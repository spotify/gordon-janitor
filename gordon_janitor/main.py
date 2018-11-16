# -*- coding: utf-8 -*-
#
# Copyright 2017 Spotify AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Main module to run the Gordon Janitor service.

The service expects a ``gordon-janitor.toml`` and/or a
``gordon-janitor-user.toml`` file for configuration in the current
working directory, or in a provided root directory.

Any configuration defined in ``gordon-janitor-user.toml`` overwrites
those in ``gordon-janitor.toml``.

Example:

.. code-block:: bash

    $ python gordon_janitor/main.py
    $ python gordon_janitor/main.py -c /etc/default/
    $ python gordon_janitor/main.py --config-root /etc/default/
"""

import asyncio
import logging
import os

import click
import toml
import ulogger
from gordon import plugins_loader

from gordon_janitor import __version__ as version
from gordon_janitor import exceptions
from gordon_janitor import interfaces


plugins_loader.PLUGIN_NAMESPACE = 'gordon_janitor.plugins'


def _deep_merge_dict(a, b):
    """Additively merge right side dict into left side dict."""
    for k, v in b.items():
        if k in a and isinstance(a[k], dict) and isinstance(v, dict):
            _deep_merge_dict(a[k], v)
        else:
            a[k] = v


def _load_config(root=''):
    conf, error = {}, False
    conf_files = ['gordon-janitor.toml', 'gordon-janitor-user.toml']
    for conf_file in conf_files:
        try:
            with open(os.path.join(root, conf_file), 'r') as f:
                _deep_merge_dict(conf, (toml.load(f)))
        except IOError:
            error = True

    if error and conf == {}:
        raise IOError(f'Cannot load Gordon configuration file from "{root}".')
    return conf


def setup(config_root=''):
    """
    Service configuration and logging setup.

    Configuration defined in ``gordon-janitor-user.toml`` will overwrite
    ``gordon-janitor.toml``.

    Args:
        config_root (str): where configuration should load from,
            defaults to current working directory.
    Returns:
        A dict for Gordon service configuration
    """
    config = _load_config(root=config_root)

    logging_config = config.get('core', {}).get('logging', {})
    log_level = logging_config.get('level', 'INFO').upper()
    log_handlers = logging_config.get('handlers') or ['syslog']

    ulogger.setup_logging(
        progname='gordon-janitor', level=log_level, handlers=log_handlers)

    return config


def _log_or_exit_on_exceptions(base_msg, exc, debug):
    log_level_func = logging.warn
    if not debug:
        log_level_func = logging.error

    if isinstance(exc, list):
        for exception in exc:
            log_level_func(base_msg, exc_info=exception)
    else:
        log_level_func(base_msg, exc_info=exc)

    if not debug:
        raise SystemExit(1)


def _gather_providers(plugins, debug):
    # NOTE: this assumes dict ordering is deterministic, if ever ported
    #       to <3.6, this will break!
    providers = {
        'publisher': None,
        'reconciler': None,
        'authority': None,
    }
    for plugin in plugins:
        if interfaces.IPublisher.providedBy(plugin):
            providers['publisher'] = plugin
        elif interfaces.IReconciler.providedBy(plugin):
            providers['reconciler'] = plugin
        elif interfaces.IAuthority.providedBy(plugin):
            providers['authority'] = plugin

    missing = []
    msg = ('A provider for "{name}" interface is not configured for the '
           'Janitor service or is not implemented.')
    for provider, obj in providers.items():
        if obj is None:
            exc = exceptions.MissingPluginError(msg.format(name=provider))
            missing.append(exc)
    if missing:
        base_msg = 'Issue running plugins: '
        _log_or_exit_on_exceptions(base_msg, missing, debug=debug)

    return providers


async def _run(plugins, debug):
    # organize plugins to assert order; publisher should start first,
    # authority last
    providers = _gather_providers(plugins, debug=debug)

    tasks = []
    for name, provider in providers.items():
        try:
            tasks.append(provider.run())
        except AttributeError as e:
            base_msg = 'Plugin missing required "run" method: '
            _log_or_exit_on_exceptions(base_msg, name, debug=debug)

    await asyncio.gather(*tasks)


def report_run_result(metrics, status):
    if not metrics:
        return

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        metrics.incr('run-ended', context={'status': status}))


@click.command()
@click.option('-c', '--config-root',
              type=click.Path(exists=True), required=False, default='.',
              help='Directory where to find service configuration.')
def run(config_root):
    config = setup(os.path.abspath(config_root))
    debug_mode = config.get('core', {}).get('debug', False)

    # TODO: initialize a metrics object - either here or within `load_plugins`
    plugin_kwargs = {
        'rrset_channel': asyncio.Queue(),
        'changes_channel': asyncio.Queue(),
    }

    plugin_names, plugins, errors, plugin_kwargs = plugins_loader.load_plugins(
        config, plugin_kwargs)
    metrics = plugin_kwargs.get('metrics')

    for err_plugin, exc in errors:
        base_msg = f'Plugin was not loaded: {err_plugin}'
        _log_or_exit_on_exceptions(base_msg, exc, debug=debug_mode)

    if not plugin_names:
        logging.error('No plugins to run, exiting.')
        report_run_result(metrics, 'no-plugin-error')
        return SystemExit(1)

    logging.info(f'Loaded {len(plugin_names)} plugins: {plugin_names}')
    logging.info(f'Starting gordon janitor v{version}...')

    status = 'success'
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_run(plugins, debug_mode))
        logging.info('Gordon-janitor run complete.')
    except Exception as e:
        logging.error(f'A fatal error occurred during the janitor run: {e}')
        status = 'unexpected-error'
        raise e
    finally:
        report_run_result(metrics, status)
        loop.close()


if __name__ == '__main__':
    run()
