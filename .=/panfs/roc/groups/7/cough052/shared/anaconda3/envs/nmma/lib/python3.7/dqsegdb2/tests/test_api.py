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

from .. import api


def test_segment_query_url():
    assert api.segment_query_url('http://test.com', 'X1', 'FLAG', 1,
                                 start=100, end=200) == (
        'http://test.com/dq/X1/FLAG/1?'
        'e=200&include=metadata,known,active&s=100'
    )


def test_version_query_url():
    assert api.version_query_url('http://test.com', 'X1', 'FLAG') == (
        'http://test.com/dq/X1/FLAG')


def test_name_query_url():
    assert api.name_query_url('http://test.com', 'X1') == (
        'http://test.com/dq/X1')
