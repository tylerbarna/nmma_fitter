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

"""API URL implementation for DQSEGDB
"""


def _query(**kwargs):
    """Return a URL query string based on some key, value pairs
    """
    return '&'.join('{0}={1}'.format(key, value) for
                    key, value in sorted(kwargs.items()))


def segment_query_url(host, ifo, name, version, start=None, end=None,
                      include='metadata,known,active'):
    """Returns the URL to use in querying for segments

    Parameters
    ----------
    host : `str`
        the URL of the target DQSEGDB2 host

    ifo : `str`
        the interferometer prefix

    name : `str`
        the name of the flag

    version : `int`
        the version of the flag

    start : `int`
        the start GPS time of the query

    end : `int`
        the end GPS time of the query

    include : `str`, optional
        the data to return, should be a comma-separated list of keys

    Returns
    -------
    url : `str`
        the full REST URL to query for information

    Examples
    --------
    >>> from dqsegdb2.api import segment_query_url
    >>> print(segment_query_url('https://segments.ligo.org', 'G1',
    ...                         'GEO-SCIENCE', 1, 1000000000, 11000000000))
    'https://segments.ligo.org/dq/G1/GEO-SCIENCE/1?s=1000000000&e=11000000000&include=metadata,known,active'
    """
    return '{host}/dq/{ifo}/{name}/{version}?{query}'.format(
        host=host, ifo=ifo, name=name, version=version,
        query=_query(s=start, e=end, include=include))


def version_query_url(host, ifo, name):
    """Returns the URL to use in querying for flag versions

    Parameters
    ----------
    host : `str`
        the URL of the target DQSEGDB2 host

    ifo : `str`
        the interferometer prefix

    name : `str`
        the name of the flag

    Returns
    -------
    url : `str`
        the full REST URL to query for information

    Examples
    --------
    >>> from dqsegdb2.api import version_query_url
    >>> print(version_query_url('https://segments.ligo.org', 'G1',
    ...                         'GEO-SCIENCE'))
    'https://segments.ligo.org/dq/G1/GEO-SCIENCE'
    """
    return '{host}/dq/{ifo}/{name}'.format(host=host, ifo=ifo, name=name)


def name_query_url(host, ifo):
    """Returns the URL to use in querying for flag names

    Parameters
    ----------
    host : `str`
        the URL of the target DQSEGDB2 host

    ifo : `str`
        the interferometer prefix

    Returns
    -------
    url : `str`
        the full REST URL to query for information

    Examples
    --------
    >>> from dqsegdb2.api import name_query_url
    >>> print(name_query_url('https://segments.ligo.org', 'G1'))
    'https://segments.ligo.org/dq/G1'
    """
    return '{host}/dq/{ifo}'.format(host=host, ifo=ifo)
