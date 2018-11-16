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

import copy
import logging

import pytest
from click.testing import CliRunner

from gordon_janitor import interfaces
from gordon_janitor import main
from tests.unit import conftest


#####
# Tests for service setup
#####
@pytest.mark.parametrize('suffix', ['', '-user'])
def test_load_config(tmpdir, suffix, config_file, loaded_config):
    """Load prod and user config."""
    filename = 'gordon-janitor{}.toml'.format(suffix)
    conf_file = tmpdir.mkdir('config').join(filename)
    conf_file.write(config_file)
    config = main._load_config(root=conf_file.dirpath())
    assert loaded_config == config


def test_load_config_deep_merges(tmpdir, config_file, loaded_config):
    """Additively merge user file to main config."""
    config_dir = tmpdir.mkdir('mergeconfig')
    main_conf_file = config_dir.join('gordon-janitor.toml')
    main_conf_file.write(config_file)

    user_conf_file = config_dir.join('gordon-janitor-user.toml')
    user_conf_file.write('[core.logging]\nlevel = "error"\n')
    config = main._load_config(root=config_dir.strpath)

    expected_config = copy.deepcopy(loaded_config)
    expected_config['core']['logging']['level'] = 'error'
    assert expected_config == config


@pytest.mark.parametrize('a,b,expected', [
    ({'a': 1}, {'b': 2}, {'a': 1, 'b': 2}),
    ({'a': 1}, {'a': 2}, {'a': 2}),
    ({'a': {'a1': 1}}, {'a': {'a2': 2}}, {'a': {'a1': 1, 'a2': 2}}),
    ({'a': {'a1': 1}}, {'a': {'a1': 2}}, {'a': {'a1': 2}}),
    ({}, {'a': {'a1': 1}}, {'a': {'a1': 1}}),
    ({'a': None}, {'a': {'a1': 1}}, {'a': {'a1': 1}}),
    ({'a': {'a1': 1}}, {'a': None}, {'a': None}),
    ({'a': {'a1': 1}}, {'a': {}}, {'a': {'a1': 1}})
])
def test_deep_merge_dict(a, b, expected):
    main._deep_merge_dict(a, b)
    assert expected == a


def test_load_config_raises(tmpdir):
    """No config loaded raises IOError."""
    dir_with_no_conf = tmpdir.mkdir('config')
    with pytest.raises(IOError) as e:
        main._load_config(root=dir_with_no_conf.dirpath())

    assert e.match('Cannot load Gordon configuration file from')


def test_setup(tmpdir, mocker, monkeypatch, config_file, loaded_config):
    """Setup service config and logging."""
    conf_file = tmpdir.mkdir('config').join('gordon-janitor.toml')
    conf_file.write(config_file)

    ulogger_mock = mocker.MagicMock(main.ulogger, autospec=True)
    ulogger_mock.setup_logging = mocker.Mock()
    monkeypatch.setattr(main, 'ulogger', ulogger_mock)

    config = main.setup(config_root=conf_file.dirpath())

    assert loaded_config == config

    ulogger_mock.setup_logging.assert_called_once_with(
        progname='gordon-janitor', level='DEBUG', handlers=['stream'])


#####
# Tests & fixtures for running service
#####
@pytest.fixture
def setup_mock(mocker, monkeypatch):
    setup_mock = mocker.MagicMock(main.setup, autospec=True)
    monkeypatch.setattr(main, 'setup', setup_mock)
    return setup_mock


@pytest.fixture
def load_plugins_mock(mocker, monkeypatch):
    load_plugins_mock = mocker.MagicMock(
        main.plugins_loader.load_plugins, autospec=True)
    patch = 'gordon_janitor.main.plugins_loader.load_plugins'
    monkeypatch.setattr(patch, load_plugins_mock)
    return load_plugins_mock


@pytest.fixture
def metrics_mock(mocker):
    metrics = mocker.Mock()

    async def incr(*args, **kwargs):
        metrics._incr(*args, **kwargs)
    metrics.incr = incr
    return metrics


@pytest.mark.parametrize('error_type', ['list', 'obj'])
def test_log_or_exit_on_exceptions_no_debug(
        error_type, plugin_exc_mock, caplog, capsys):
    """Raise SystemExit if debug flag is off."""
    error = plugin_exc_mock
    if error_type == 'list':
        error = [error]
    with pytest.raises(SystemExit) as e:
        main._log_or_exit_on_exceptions('base msg', error, debug=False)
    e.match('1')

    assert 1 == len(caplog.records)
    for record in caplog.records:
        assert 'ERROR' == record.levelname

    # Assert the bug from https://github.com/spotify/gordon-janitor/pull/14
    # has not reappeared.
    out, err = capsys.readouterr()
    assert '--- Logging error ---' not in err


def test_log_or_exit_on_exceptions_debug(
        plugin_exc_mock, mocker, monkeypatch, caplog, capsys):
    """Do not exit out if debug flag is on."""
    msg, error = 'Plugin not loaded "bad.plugin"', plugin_exc_mock
    main._log_or_exit_on_exceptions(msg, error, debug=True)

    assert 1 == len(caplog.records)
    for record in caplog.records:
        assert 'WARNING' == record.levelname


@pytest.fixture
def mock_provided_by(mocker, monkeypatch):
    mock_iauthority = mocker.Mock(interfaces.IAuthority, autospec=True)
    mock_iauthority.providedBy.side_effect = iter([True])
    patch = 'gordon_janitor.main.interfaces.IAuthority'
    monkeypatch.setattr(patch, mock_iauthority)

    mock_ireconciler = mocker.Mock(interfaces.IReconciler, autospec=True)
    mock_ireconciler.providedBy.side_effect = iter([True, False])
    patch = 'gordon_janitor.main.interfaces.IReconciler'
    monkeypatch.setattr(patch, mock_ireconciler)

    mock_ipublisher = mocker.Mock(interfaces.IPublisher, autospec=True)
    mock_ipublisher.providedBy.side_effect = iter([True, False, False])
    patch = 'gordon_janitor.main.interfaces.IPublisher'
    monkeypatch.setattr(patch, mock_ipublisher)

    return mock_iauthority, mock_ireconciler, mock_ipublisher


def test_gather_providers_no_providers(plugins, mock_provided_by, caplog):
    mock_iauthority, mock_ireconciler, mock_ipublisher = mock_provided_by
    mock_iauthority.providedBy.side_effect = [False, False, False]
    mock_ireconciler.providedBy.side_effect = [False, False, False]
    mock_ipublisher.providedBy.side_effect = [False, False, False]

    main._gather_providers(plugins, debug=True)

    assert 3 == len(caplog.records)


@pytest.mark.asyncio
async def test_run_no_providers(plugins, mock_provided_by, caplog):
    mock_iauthority, mock_ireconciler, mock_ipublisher = mock_provided_by
    mock_iauthority.providedBy.side_effect = [False, False, False]
    mock_ireconciler.providedBy.side_effect = [False, False, False]
    mock_ipublisher.providedBy.side_effect = [False, False, False]

    await main._run(plugins, debug=True)

    assert 6 == len(caplog.records)


@pytest.mark.asyncio
@pytest.mark.parametrize('debug', (True, False))
async def test_async_run_debug(debug, mock_provided_by, caplog):
    plugins = [
        conftest.FakePlugin({}),
        conftest.FakePlugin({}),
        conftest.FakePlugin({})
    ]
    await main._run(plugins, debug=debug)

    mock_iauthority, mock_ireconciler, mock_ipublisher = mock_provided_by
    assert 3 == mock_ipublisher.providedBy.call_count
    assert 2 == mock_ireconciler.providedBy.call_count
    assert 1 == mock_iauthority.providedBy.call_count


run_args = 'has_active_plugins,has_metric,exp_log_count'
run_params = [
    (True, True, 3),
    (True, False, 3),
    (False, True, 1),
]


@pytest.mark.parametrize(run_args, run_params)
def test_run(has_active_plugins, has_metric, exp_log_count, setup_mock,
             load_plugins_mock, mock_provided_by, monkeypatch, caplog,
             metrics_mock, mocker, event_loop):
    """Successfully start the Gordon service."""
    mock_get_event_loop = mocker.Mock(return_value=event_loop)
    monkeypatch.setattr(main.asyncio, 'get_event_loop', mock_get_event_loop)
    caplog.set_level(logging.INFO)
    names, _plugins, errors = [], [], []
    kwargs = {'metrics': metrics_mock} if has_metric else {}
    expected_result = 'no-plugin-error'
    if has_active_plugins:
        expected_result = 'success'
        names = ['authority.plugin', 'reconciler.plugin', 'publisher.plugin']
        _plugins = [
            conftest.FakePlugin({}),
            conftest.FakePlugin({}),
            conftest.FakePlugin({})
        ]
    load_plugins_mock.return_value = names, _plugins, errors, kwargs

    runner = CliRunner()
    result = runner.invoke(main.run)

    assert 0 == result.exit_code
    setup_mock.assert_called_once()
    assert exp_log_count == len(caplog.records)
    if has_metric:
        metrics_mock._incr.assert_called_once_with(
            'run-ended', context={'status': expected_result})


def test_run_raise_plugin_exceptions(loaded_config, plugins, caplog, setup_mock,
                                     load_plugins_mock, plugin_exc_mock,
                                     mock_provided_by):
    """Raise plugin exceptions when not in debug mode."""
    loaded_config['core']['debug'] = False
    setup_mock.return_value = loaded_config

    names = ['authority.plugin', 'reconciler.plugin']
    errors = [('publisher.plugin', plugin_exc_mock)]
    kwargs = {}
    load_plugins_mock.return_value = names, plugins, errors, kwargs

    runner = CliRunner()
    result = runner.invoke(main.run)

    assert 1 == result.exit_code
    setup_mock.assert_called_once()
    assert 1 == len(caplog.records)


def test_run_raise_run_exception(monkeypatch, caplog, setup_mock, metrics_mock,
                                 load_plugins_mock, mock_provided_by):

    async def raises(*args, **kwargs):
        raise Exception('test!')

    monkeypatch.setattr(main, '_run', raises)
    caplog.set_level(logging.ERROR)

    names = ['authority.plugin', 'reconciler.plugin', 'publisher.plugin']
    _plugins = [
        conftest.FakePlugin({}),
        conftest.FakePlugin({}),
        conftest.FakePlugin({})
    ]

    kwargs = {'metrics': metrics_mock}
    load_plugins_mock.return_value = names, _plugins, [], kwargs

    runner = CliRunner()
    result = runner.invoke(main.run)

    assert -1 == result.exit_code
    assert 1 == len(caplog.records)
    assert 'test!' in str(caplog.records)
    metrics_mock._incr.assert_called_once_with(
        'run-ended', context={'status': 'unexpected-error'})
