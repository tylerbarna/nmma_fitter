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

"""Query methods for DQSEGDB2
"""

from __future__ import absolute_import

import os

from . import api
from .http import request_json

from ligo import segments

DEFAULT_SEGMENT_SERVER = os.environ.setdefault(
    'DEFAULT_SEGMENT_SERVER', 'https://segments.ligo.org')


def query_names(ifo, host=DEFAULT_SEGMENT_SERVER):
    """Query for all defined flags for the given ``ifo``

    Parameters
    ----------
    ifo : `str`
        the interferometer prefix for which to query

    host : `str`, optional
        the URL of the database, defaults to `DEFAULT_SEGMENT_SERVER`

    Returns
    -------
    flags : `set`
        the set of all define flag names in the format ``{ifo}:{name}``

    Examples
    --------
    >>> from dqsegdb2.query import query_names
    >>> query_names('G1')
    """
    url = api.name_query_url(host, ifo)
    names = request_json(url)['results']
    return {'{0}:{1}'.format(ifo, name) for name in names}


def query_versions(flag, host=DEFAULT_SEGMENT_SERVER):
    """Query for defined versions for the given flag

    Parameters
    ----------
    flag : `str`
        the name for which to query

    host : `str`, optional
        the URL of the database, defaults to `DEFAULT_SEGMENT_SERVER`

    Returns
    -------
    versions : `list` of `int`
        the list of defined versions for the given flag

    Examples
    --------
    >>> from dqsegdb2.query import query_versions
    >>> query_versions('G1:GEO-SCIENCE')
    [1, 2, 3]
    """
    ifo, name = flag.split(':', 1)
    url = api.version_query_url(host, ifo, name)
    return sorted(request_json(url)['version'])


def query_segments(flag, start, end, host=DEFAULT_SEGMENT_SERVER,
                   coalesce=True):
    """Query for segments for the given flag in a ``[start, stop)`` interval

    Parameters
    ----------
    flag : `str`
        the name for which to query, see _Notes_ for information on how
        versionless-flags are queried.

    start : `int`
        the GPS start time.

    end : `int`
        the GPS end time.

    host : `str`, optional
        the URL of the database, defaults to `DEFAULT_SEGMENT_SERVER`.

    coalesce : `bool`, optional
        if `True` coalesce the segmentlists returned by the server,
        otherwise return the 'raw' result, default: `True`.

    Returns
    -------
    segmentdict : `dict`
        a `dict` with the following keys

        - ``'ifo'`` - the interferometer prefix (`str`)
        - ``'name'`` - the flag name (`str`)
        - ``'version'`` - the flag version (`int`)
        - ``'known'`` - the known segments (`~ligo.segments.segmentlist`)
        - ``'active'`` - the active segments (`~ligo.segments.segmentlist`)
        - ``'metadata'`` - a `dict` of flag information (`dict`)
        - ``'query_information'`` - a `dict` of query information (`dict`)

    Notes
    -----
    If ``flag`` is given without a version (e.g. ``'X1:FLAG-NAME'``) or the
    version is given as ``'*'`` (e.g. ``'X1:FLAG-NAME:*'``) the result of
    the query will be the intersection of queries over all versions found
    in the database.
    In that case the ``'metadata'`` and ``'query_information'`` in the output
    will be preserved for the highest version number only.

    Examples
    --------
    >>> from dqsegdb2.query import query_segments
    >>> query_segments('G1:GEO-SCIENCE:1', 1000000000, 1000001000)
    """
    try:
        ifo, name, version = flag.split(':', 2)
        versions = [int(version)]
    except ValueError:
        if flag.endswith(':*'):  # allow use of wildcard version
            flag = flag.rsplit(':', 1)[0]
        ifo, name = flag.split(':', 1)
        versions = query_versions(flag, host=host)

    out = dict(
        known=segments.segmentlist(),
        active=segments.segmentlist(),
        ifo=ifo, name=name, version=versions[0],
    )

    for i, version in enumerate(sorted(versions)):
        url = api.segment_query_url(host, ifo, name, version,
                                    start=start, end=end)
        result = request_json(url)
        for key in ('active', 'known'):
            out[key] += segments.segmentlist(
                map(segments.segment, result.pop(key)))
            if coalesce:
                out[key].coalesce()
        out.update(result)
        if i:  # multiple versions:
            out['version'] = None

    return out
