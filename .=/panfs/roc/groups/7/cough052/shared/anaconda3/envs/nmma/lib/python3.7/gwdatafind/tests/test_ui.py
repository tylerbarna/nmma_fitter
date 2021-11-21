# -*- coding: utf-8 -*-
# Copyright Duncan Macleod 2018
#
# This file is part of GWDataFind.
#
# GWDataFind is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GWDataFind is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GWDataFind.  If not, see <http://www.gnu.org/licenses/>.

import os

import pytest

try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

from .. import ui

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'

ENVMOCK = None


def setup_module():
    global ENVMOCK
    ENVMOCK = mock.patch.dict(os.environ, {
        'LIGO_DATAFIND_SERVER': 'test.datafind.com',
    })
    ENVMOCK.start()


def teardown_module():
    ENVMOCK.stop()


@mock.patch('gwdatafind.ui.HTTPConnection')
@pytest.mark.parametrize('serv', (
    None,
    'test.datafind.com',
))
def test_connect_http(conn, serv):
    ui.connect(host=serv)
    conn.assert_called_with(host='test.datafind.com', port=None)


@mock.patch('ssl.create_default_context')
@mock.patch('gwdatafind.ui.find_credential')
@mock.patch('gwdatafind.ui.HTTPSConnection')
def test_connect_https(conn, cred, sslctx):
    loadcert = mock.MagicMock()
    sslctx.return_value = loadcert
    sslctx
    cred.return_value = ('cert', 'key')

    ui.connect('test.datafind.com:443')

    loadcert.load_cert_chain.assert_called_with('cert', 'key')
    conn.assert_called_with(host='test.datafind.com', port=443,
                            context=loadcert)


@mock.patch('gwdatafind.ui.HTTPConnection', return_value=mock.MagicMock())
@pytest.mark.parametrize('method', (
    'ping',
    'find_observatories',
    'find_types',
    'find_times',
    'find_url',
    'find_urls',
    'find_latest',
))
def test_factory_method(conn, method):
    getattr(ui, method)()
    assert getattr(conn.return_value, method).call_count == 1


