# -*- coding: utf-8 -*-
# Copyright (C) 2018  Duncan Macleod
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""Tests for :mod:`gwdatafind.http`
"""

import json
import os
from io import BytesIO
from operator import attrgetter

from six import string_types
from six.moves.urllib.error import HTTPError

try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from ligo.segments import (segment, segmentlist)

from .. import utils
from ..http import (
    HTTPConnection,
    HTTPSConnection,
)

LIGO_DATAFIND_SERVER = os.getenv('LIGO_DATAFIND_SERVER')

def setup_module():
    os.environ['LIGO_DATAFIND_SERVER'] = 'test.gwdatafind.com:123'


def teardown_module():
    os.environ.pop('LIGO_DATAFIND_SERVER')
    if LIGO_DATAFIND_SERVER:
        os.environ['LIGO_DATAFIND_SERVER'] = LIGO_DATAFIND_SERVER


def fake_response(output, status=200):
    resp = mock.Mock()
    resp.status = int(status)
    if not isinstance(output, string_types):
        output = json.dumps(output)
    resp.read.return_value = output.encode('utf-8')
    return resp


class TestHTTPConnection(object):
    CONNECTION = HTTPConnection

    @classmethod
    def setup_class(cls):
        cls._create_connection_patch = mock.patch('socket.create_connection')
        cls._create_connection_patch.start()

    @classmethod
    def teardown_class(cls):
        cls._create_connection_patch.stop()

    @classmethod
    @pytest.fixture
    def connection(cls):
        return cls.CONNECTION()

    def test_init(self, connection):
        assert connection.host == 'test.gwdatafind.com'
        assert connection.port == 123

    def test_get_json(self, response, connection):
        response.return_value = fake_response({'test': 1})
        jdata = connection.get_json('something')
        assert jdata['test'] == 1


    def test_ping(self, response, connection):
        response.return_value = fake_response('')
        assert connection.ping() is 0
        response.return_value = fake_response('', 500)
        with pytest.raises(HTTPError):
            connection.ping()

    @pytest.mark.parametrize('match, out', [
        (None, ['A', 'B', 'C', 'D', 'ABCD']),
        ('B', ['B', 'ABCD']),
    ])
    def test_find_observatories(self, response, connection, match, out):
        response.return_value = fake_response(['A', 'B', 'C', 'D', 'ABCD'])
        assert sorted(connection.find_observatories(match=match)) == (
            sorted(out))

    @pytest.mark.parametrize('site, match, out', [
        (None, None, ['A', 'B', 'C', 'D', 'ABCD']),
        ('X', 'B', ['B', 'ABCD']),
    ])
    def test_find_types(self, response, connection, site, match, out):
        response.return_value = fake_response(['A', 'B', 'C', 'D', 'ABCD'])
        assert sorted(connection.find_types(match=match)) == (
            sorted(out))

    def test_find_times(self, response, connection):
        segs = [(0, 1), (1, 2), (3, 4)]
        response.return_value = fake_response(segs)
        times = connection.find_times('X', 'test')
        assert isinstance(times, segmentlist)
        assert isinstance(times[0], segment)
        assert times == segs

        # check keywords
        times = connection.find_times('X', 'test', 0, 10)
        assert times == segs
        with pytest.raises(ValueError):
            times = connection.find_times('X', 'test', gpsstart=0)
        with pytest.raises(ValueError):
            times = connection.find_times('X', 'test', gpsend=10)

    def test_find_url(self, response, connection):
        out = ['file:///tmp/X-test-0-10.gwf']
        response.return_value = fake_response(out)
        url = connection.find_url('X-test-0-10.gwf')
        assert url == out

        response.return_value = fake_response([])
        with pytest.raises(RuntimeError):
            connection.find_url('X-test-0-10.gwf')
        with pytest.warns(UserWarning):
            url = connection.find_url('X-test-0-10.gwf', on_missing='warn')
            assert url == []
        with pytest.warns(None) as wrngs:
            url = connection.find_url('X-test-0-10.gwf', on_missing='ignore')
            assert url == []
        assert not wrngs.list

    def test_find_frame(self, response, connection):
        out = ['file:///tmp/X-test-0-10.gwf']
        response.return_value = fake_response(out)
        with pytest.warns(DeprecationWarning):
            url = connection.find_frame('X-test-0-10.gwf')
        assert url == out

    def test_find_latest(self, response, connection):
        out = ['file:///tmp/X-test-0-10.gwf']
        response.return_value = fake_response(out)
        url = connection.find_latest('X', 'test')
        assert url == out

        response.return_value = fake_response([])
        with pytest.raises(RuntimeError):
            connection.find_latest('X', 'test')
        with pytest.warns(UserWarning):
            url = connection.find_latest('X', 'test', on_missing='warn')
            assert url == []
        with pytest.warns(None) as wrngs:
            url = connection.find_latest('X', 'test', on_missing='ignore')
            assert url == []
        assert not wrngs.list

    def test_find_urls(self, response, connection):
        files =  [
            'file:///tmp/X-test-0-10.gwf',
            'file:///tmp/X-test-10-10.gwf',
            'file:///tmp/X-test-20-10.gwf',
        ]
        response.return_value = fake_response(files)
        urls = connection.find_urls('X', 'test', 0, 30, match='anything')
        assert urls == files

        # check gaps
        with pytest.raises(RuntimeError):
            connection.find_urls('X', 'test', 0, 40, on_gaps='error')
        with pytest.warns(UserWarning):
            urls = connection.find_urls('X', 'test', 0, 40, on_gaps='warn')
            assert urls == files
        with pytest.warns(None) as wrngs:
            urls = connection.find_urls('X', 'test', 0, 40, on_gaps='ignore')
            assert urls == files
        assert not wrngs.list

    def test_find_frame_urls(self, response, connection):
        files =  [
            'file:///tmp/X-test-0-10.gwf',
            'file:///tmp/X-test-10-10.gwf',
            'file:///tmp/X-test-20-10.gwf',
        ]
        response.return_value = fake_response(files)
        with pytest.warns(DeprecationWarning):
            urls = connection.find_frame_urls('X', 'test', 0, 30)
        assert urls == files


class TestHTTPSConnection(TestHTTPConnection):
    CONNECTION = HTTPSConnection
