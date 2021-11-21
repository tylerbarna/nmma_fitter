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

"""Tests for :mod:`dqsegdb.api`
"""

import json

try:
    from unittest import mock
except ImportError:
    import mock

import pytest

from .. import query


@mock.patch('dqsegdb2.query.request_json')
def test_query_names(request_json):
    names = ['name1', 'name2', 'name2']
    request_json.return_value = {'results': names}
    assert query.query_names('X1') == set(map('X1:{0}'.format, names))


@mock.patch('dqsegdb2.query.request_json')
def test_query_versions(request_json):
    versions = [1, 2, 3, 4]
    request_json.return_value = {'version': versions}
    assert query.query_versions('X1:test') == sorted(versions)


@pytest.mark.parametrize('flag', ('X1:TEST:1', 'X1:TEST:*'))
@mock.patch('dqsegdb2.query.query_versions')
@mock.patch('dqsegdb2.http.request')
def test_query_versions_versioned(request, versions, flag):
    versions.return_value = [1, 2]
    result = {
        'ifo': 'X1',
        'name': 'TEST',
        'version': 1,
        'known': [(0, 5)],
        'active': [(1, 2), (3, 4)],
    }
    # this mock is a bit more complicated because query_segments() pops
    # keys out of the dict, so we need to mock further upstream
    request.return_value = response = mock.MagicMock()
    response.read.return_value = json.dumps(result)

    out = query.query_segments(flag, 0, 5)
    assert out.pop('version') is (None if flag.endswith('*') else 1)
    for key in set(result) & set(out):
        assert out[key] == result[key]
