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

import logging
import os

import click
import toml
import ulogger

from gordon_janitor import __version__ as version
from gordon_janitor import plugins_loader


def _load_config(root=''):
    conf, error = {}, False
    conf_files = ['gordon-janitor.toml', 'gordon-janitor-user.toml']
    for conf_file in conf_files:
        try:
            with open(os.path.join(root, conf_file), 'r') as f:
                conf.update(toml.load(f))
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


def _log_or_exit_on_exceptions(errors, debug):
    log_level_func = logging.warn
    if not debug:
        log_level_func = logging.error

    base_msg = 'Plugin "{name}" was not loaded:'
    for name, exc in errors:
        msg = base_msg.format(name=name)
        log_level_func(msg, exc_info=exc)

    if not debug:
        raise SystemExit(1)


@click.command()
@click.option('-c', '--config-root',
              type=click.Path(exists=True), required=False, default='.',
              help='Directory where to find service configuration.')
def run(config_root):
    config = setup(os.path.abspath(config_root))
    debug_mode = config.get('core', {}).get('debug', False)

    plugin_names, plugins, errors = plugins_loader.load_plugins(config)
    if errors:
        _log_or_exit_on_exceptions(errors, debug_mode)

    if plugin_names:
        logging.info(f'Loaded {len(plugin_names)} plugins: {plugin_names}')

    logging.info(f'Starting gordon janitor v{version}...')


if __name__ == '__main__':
    run()
