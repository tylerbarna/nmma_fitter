# DQSEGDB2
# Copyright (C) 2018  Duncan Macleod
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for :mod:`dqsegdb.http`
"""

import json
from io import BytesIO
try:
    from unittest import mock
except ImportError:
    import mock

from .. import http


@mock.patch('dqsegdb2.http.urlopen')
def test_request_http(urlopen):
    http.request('test', a=1, b=2)
    urlopen.assert_called_once_with('test', a=1, b=2)


@mock.patch('ssl.create_default_context')
@mock.patch('gwdatafind.utils.find_credential')
@mock.patch('dqsegdb2.http.urlopen')
def test_request_https(urlopen, find, create):
    print(create, find, urlopen)
    create.return_value = context = mock.MagicMock()
    http.request('https://test', a=1)
    find.assert_called_once_with()
    urlopen.assert_called_once_with('https://test', context=context, a=1)


@mock.patch('dqsegdb2.http.urlopen')
def test_request_json(urlopen):
    data = {'key': 'value'}
    urlopen.return_value = BytesIO(json.dumps(data).encode('utf-8'))
    out = http.request_json('http://test')
    assert out == data
