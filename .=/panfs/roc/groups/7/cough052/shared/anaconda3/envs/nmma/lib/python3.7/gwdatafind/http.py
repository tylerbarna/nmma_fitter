# -*- coding: utf-8 -*-
# Copyright (C) 2012-2015  Scott Koranda, 2015+ Duncan Macleod
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

"""Connection utilities for the GW datafind service.
"""

from __future__ import (absolute_import, division)

import os
import re
import socket
import warnings
from json import loads

from six.moves import http_client
from six.moves.urllib.error import HTTPError
from six.moves.urllib.parse import urlparse

from ligo import segments

from .utils import (get_default_host, file_segment)

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'
__all__ = ['DEFAULT_SERVICE_PREFIX', 'HTTPConnection', 'HTTPSConnection']

DEFAULT_SERVICE_PREFIX = "/LDR/services/data/v1"


class HTTPConnection(http_client.HTTPConnection):
    """Connect to a GWDataFind host using HTTP.

    Parameters
    ----------
    host : `str`
        the name of the server with which to connect.

    port : `int`, optional
        the port on which to connect.

    **kwargs
        other keywords are passed directly to `http.client.HTTPConnection`
    """
    def __init__(self, host=None, port=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None,
                 **kwargs):
        """Create a new connection.
        """
        if host is None:
            host = get_default_host()
        http_client.HTTPConnection.__init__(self, host, port, timeout,
                                            source_address, **kwargs)

    def _request_response(self, method, url, **kwargs):
        """Internal method to perform request and verify reponse.

        Parameters
        ----------
        method : `str`
            name of the method to use (e.g. ``'GET'``).

        url : `str`
            remote URL to query.

        **kwargs
            other keyword arguments are passed to
            :meth:`http.client.HTTPConnection.request`.

        Returns
        -------
        response : `str`
            reponse from server query

        Raises
        ------
        RuntimeError
            if query is unsuccessful
        """
        self.request(method, url, **kwargs)
        response = self.getresponse()
        if response.status != 200:
            raise HTTPError(url, response.status, response.reason,
                            response.getheaders(), response.fp)
        return response

    def get_json(self, url, **kwargs):
        """Perform a 'GET' request and return the decode the result as JSON

        Parameters
        ----------
        url : `str`
            remote URL to query

        **kwargs
            other keyword arguments are passed to
            :meth:`HTTPConnection._request_response`

        Returns
        -------
        data : `object`
            JSON decoded using :func:`json.loads`
        """
        response = self._request_response('GET', url, **kwargs).read()
        if isinstance(response, bytes):
            response = response.decode('utf-8')
        return loads(response)

    def get_urls(self, url, scheme=None, on_missing='ignore', **kwargs):
        """Perform a 'GET' request and return a list of URLs.

        Parameters
        ----------
        url : `str`
            remote URL to query

        scheme : `str`, `None`, optional
            the URL scheme to match, default: `None`

        on_missing : `str`, optional
            how to handle an empty (but successful) response, one of

            - ``'ignore'``: do nothing, return empty `list`
            - ``'warn'``: print warning, return empty `list`
            - ``'raise'``: raise `RuntimeError`

        **kwargs
            other keyword arguments are passed to
            :meth:`HTTPConnection.get_json`

        Returns
        -------
        urls : `list` of `str`
            a list of file paths as returned from the server.
        """
        urls = self.get_json(url, **kwargs)

        # sieve for correct file scheme
        if scheme:
            urls = list(filter(lambda e: urlparse(e).scheme == scheme, urls))

        # handle empty result
        if not urls:
            err = "no files found"
            if on_missing == 'warn':
                warnings.warn(err)
            elif on_missing != 'ignore':
                raise RuntimeError(err)

        return urls

    # -- supported interactions -----------------

    def ping(self):
        """Ping the LDR host to test for life.

        Raises
        ------
        RuntimeError
            if the ping fails
        """
        url = '{prefix}/gwf/H/R/1,2'.format(prefix=DEFAULT_SERVICE_PREFIX)
        self._request_response("HEAD", url)
        return 0

    def find_observatories(self, match=None):
        """Query the LDR host for observatories.

        Parameters
        ----------
        match : `str`, `re.Pattern`
            restrict returned observatories to those matching a
            regular expression.

        Returns
        -------
        obs : `list` of `str`
            the list of known osbervatory prefices (and combinations)

        Examples
        --------
        >>> from gwdatafind import connect
        >>> conn = connect()
        >>> conn.find_observatories()
        ['AGHLT', 'G', 'GHLTV', 'GHLV', 'GHT', 'H', 'HL', 'HLT',
         'L', 'T', 'V', 'Z']
        >>> conn.find_observatories("H")
        ['H', 'HL', 'HLT']
        """
        url = "%s/gwf.json" % DEFAULT_SERVICE_PREFIX
        sitelist = set(self.get_json(url))
        if match:
            regmatch = re.compile(match)
            return [site for site in sitelist if regmatch.search(site)]
        return list(sitelist)

    def find_types(self, site=None, match=None):
        """Query the LDR host for frame types.

        Parameters
        ----------
        site : `str`
            single-character name of site to match

        match : `str`, `re.Pattern`
            regular expression to match against known types

        Returns
        -------
        types  : `list` of `str`
            list of frame types

        Examples
        --------
        >>> from gwdatafind import connect
        >>> conn = connect()
        >>> conn.find_types("L", "RDS")
        ['L1_RDS_C01_LX',
         'L1_RDS_C02_LX',
         'L1_RDS_C03_L2',
         'L1_RDS_R_L1',
         'L1_RDS_R_L3',
         'L1_RDS_R_L4',
         'PEM_RDS_A6',
         'RDS_R_L1',
         'RDS_R_L2',
         'RDS_R_L3',
         'TESTPEM_RDS_A6']
        """
        if site:
            url = "%s/gwf/%s.json" % (DEFAULT_SERVICE_PREFIX, site[0])
        else:
            url = "%s/gwf/all.json" % DEFAULT_SERVICE_PREFIX
        typelist = set(self.get_json(url))
        if match:
            regmatch = re.compile(match)
            return [type_ for type_ in typelist if regmatch.search(type_)]
        return list(typelist)

    def find_times(self, site, frametype, gpsstart=None, gpsend=None):
        """Query the LDR for times for which files are avaliable.

        Parameters
        ----------
        site : `str`
            single-character name of site to match

        frametype : `str`
            name of frametype to match

        start : `int`
            GPS start time of query

        end : `int`
            GPS end time of query

        Returns
        -------
        segments : `ligo.segments.segmentlist`
            the list of `[start, stop)` intervals for which files are
            available.
        """
        if gpsstart is not None and gpsend is not None:
            url = ("{prefix}/gwf/{site}/{type}/segments/"
                   "{start},{end}.json".format(
                       prefix=DEFAULT_SERVICE_PREFIX, site=site,
                       type=frametype, start=gpsstart, end=gpsend))
        elif gpsstart is not None or gpsend is not None:
            raise ValueError("please give both `gpsstart` and `gpsend`")
        else:
            url = "{prefix}/gwf/{site}/{type}/segments.json".format(
                prefix=DEFAULT_SERVICE_PREFIX, site=site, type=frametype)

        segmentlist = self.get_json(url)
        return segments.segmentlist(map(segments.segment, segmentlist))

    def find_url(self, framefile, urltype='file', on_missing="error"):
        """Query the LDR host for a single filename.

        Parameters
        ----------
        frametype : `str`
            name of frametype to match

        urltype : `str`, optional
            file scheme to search for, one of ``'file'``, ``'gsiftp'``, or
            `None`, default: 'file'

        on_missing : `str`
            what to do when the requested file isn't found, one of:

            - ``'warn'``: print a warning (default),
            - ``'error'``: raise a `RuntimeError`, or
            - ``'ignore'``: do nothing

        Returns
        -------
        urls : `list` of `str`
            a list of structured file paths for all instances of ``filename``.
        """
        framefile = os.path.basename(framefile)

        # parse file name for site, frame type (expects T050017)
        site, frametype, _, _ = framefile.split("-")

        # query
        url = "{prefix}/gwf/{site}/{type}/{filename}.json".format(
            prefix=DEFAULT_SERVICE_PREFIX, site=site, type=frametype,
            filename=framefile)
        return self.get_urls(url, scheme=urltype, on_missing=on_missing)

    def find_frame(self, *args, **kwargs):
        """DEPRECATED, use :meth:`~HTTPConnection.find_url` instead.
        """
        warnings.warn('find_frame() was renamed find_url()',
                      DeprecationWarning)
        return self.find_url(*args, **kwargs)

    def find_latest(self, site, frametype, urltype='file', on_missing="error"):
        """Query for the most recent file of a given type.

        Parameters
        ----------
        site : `str`
            single-character name of site to match

        frametype : `str`
            name of frametype to match

        urltype : `str`, optional
            file scheme to search for, one of 'file', 'gsiftp', or
            `None`, default: 'file'

        on_missing : `str`, optional
            what to do when the requested frame isn't found, one of:

            - ``'warn'`` print a warning (default), or
            - ``'error'``: raise a `RuntimeError`, or
            - ``'ignore'``: do nothing

        Returns
        -------
        latest : `list` with one `str`
            the URLs of the latest file found (all file types)

        Raises
        ------
        RuntimeError
            if no frames are found
        """
        url = '{prefix}/gwf/{site}/{type}/latest{urltype}.json'.format(
            prefix=DEFAULT_SERVICE_PREFIX, site=site, type=frametype,
            urltype='/{0}'.format(urltype) if urltype else '',
        )
        return self.get_urls(url, scheme=urltype, on_missing=on_missing)

    def find_urls(self, site, frametype, gpsstart, gpsend,
                  match=None, urltype='file', on_gaps="warn"):
        """Find all files of the given type in the [start, end) GPS interval.

        site : `str`
            single-character name of site to match

        frametype : `str`
            name of frametype to match

        gpsstart : `int`
            integer GPS start time of query

        gpsend : `int`
            integer GPS end time of query

        match : `str`, `re.Pattern`, optional
            regular expression to match against

        urltype : `str`, optional
            file scheme to search for, one of 'file', 'gsiftp', or
            `None`, default: 'file'

        on_gaps : `str`, optional
            what to do when the requested frame isn't found, one of:

            - ``'warn'`` print a warning (default), or
            - ``'error'``: raise a `RuntimeError`, or
            - ``'ignore'``: do nothing

        Returns
        -------
        cache : `list` of `str`
            the list of discovered file URLs
        """
        url = '{prefix}/gwf/{site}/{type}/{start},{end}{urltype}.json'.format(
            prefix=DEFAULT_SERVICE_PREFIX, site=site, type=frametype,
            start=gpsstart, end=gpsend,
            urltype='/{0}'.format(urltype) if urltype else '',
        )

        # append a regex if input
        if match:
            url += "?match={0}".format(match)

        # make query
        urls = self.get_urls(url)

        # ignore missing data
        if on_gaps == "ignore":
            return urls

        # handle missing data
        span = segments.segment(gpsstart, gpsend)
        seglist = segments.segmentlist(map(file_segment, urls)).coalesce()
        missing = (segments.segmentlist([span]) - seglist).coalesce()
        if not missing:  # no gaps
            return urls

        # warn or error on missing
        msg = "Missing segments: \n%s" % "\n".join(map(str, missing))
        if on_gaps == "warn":
            warnings.warn(msg)
            return urls
        raise RuntimeError(msg)

    def find_frame_urls(self, *args, **kwargs):
        """DEPRECATED, use :meth:`~HTTPConnection.find_urls` instead.
        """
        warnings.warn('find_frame_urls() was renamed find_urls()',
                      DeprecationWarning)
        return self.find_urls(*args, **kwargs)


class HTTPSConnection(http_client.HTTPSConnection, HTTPConnection):
    """Connect to a GWDataFind host using HTTPS.

    This requires a valid X509 credential registered with the remote host.

    Parameters
    ----------
    host : `str`
        the name of the server with which to connect.

    port : `int`, optional
        the port on which to connect.

    **kwargs
        other keywords are passed directly to `http.client.HTTPSConnection`
    """
    def __init__(self, host=None, port=None, **kwargs):
        """Create a new connection.
        """
        if host is None:
            host = get_default_host()
        http_client.HTTPSConnection.__init__(self, host, port=port, **kwargs)
