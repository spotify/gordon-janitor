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
Module for reusable pytest fixtures.
"""

import os

import pkg_resources
import pytest


class FakePlugin:
    def __init__(self, config, **kwargs):
        self.config = config

    async def run(self):
        pass

    async def cleanup(self):
        pass


@pytest.fixture
def plugin_exc_mock():
    class FakePluginException(Exception):
        """Exception raised from a plugin when loading"""
        pass
    return FakePluginException('dangit')


@pytest.fixture(scope='session')
def config_file():
    here = os.path.dirname(os.path.realpath(__file__))
    filepath = os.path.join(here, 'fixtures/test-gordon-janitor.toml')
    with open(filepath, 'r') as f:
        return f.read()


@pytest.fixture
def loaded_config():
    return {
        'core': {
            'plugins': [
                'xyz.authority',
                'xyz.reconciler',
                'xyz.publisher'],
            'debug': True,
            'logging': {
                'level': 'debug',
                'handlers': ['stream'],
                'format': '%(created)f %(levelno)d %(message)s',
                'date_format': '%Y-%m-%dT%H:%M:%S',
            }
        },
        'xyz': {
            'a_key': 'a_value',
            'b_key': 'b_value',
            'authority': {
                'a_key': 'another_value',
            },
            'reconciler': {
                'd_key': 'd_value',
            },
            'publisher': {
                'c_key': 'c_value',
            }
        }
    }


@pytest.fixture
def plugins(mocker):
    plugins = {}
    names = ['xyz.authority', 'xyz.reconciler', 'xyz.publisher']
    for name in names:
        plugin_mock = mocker.MagicMock(pkg_resources.EntryPoint, autospec=True)
        plugin_mock.name = name
        plugin_mock.load.return_value = FakePlugin
        plugins[name] = plugin_mock
    return plugins
