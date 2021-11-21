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

"""HTTP interactions with DQSEGDB
"""

import json
try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:  # python < 3
    from urllib2 import urlopen
    from urlparse import urlparse


def request(url, **urlopen_kw):
    """Request data from a URL

    If the URL uses HTTPS and the `context` keyword
    is not given, X509 credentials will be automatically loaded
    using :func:`gwdatafind.utils.find_credential`.

    Parameters
    ----------
    url : `str`
        the remote URL to request (HTTP or HTTPS)

    **urlopen_kw
        other keywords are passed to :func:`urllib.request.urlopen`

    Returns
    -------
    reponse : `http.client.HTTPResponse`
        the reponse from the URL
    """
    if urlparse(url).scheme == 'https' and 'context' not in urlopen_kw:
        from ssl import create_default_context
        from gwdatafind.utils import find_credential
        urlopen_kw['context'] = context = create_default_context()
        context.load_cert_chain(*find_credential())
    return urlopen(url, **urlopen_kw)


def request_json(url, **kwargs):
    """Request data from a URL and return a parsed JSON packet

    Parameters
    ----------
    url : `str`
        the remote URL to request (HTTP or HTTPS)

    Returns
    -------
    data : `object`
        the URL reponse parsed with :func:`json.loads`

    See also
    --------
    dqsegdb2.http.request
        for information on how the request is performed
    """
    out = request(url, **kwargs).read()
    if isinstance(out, bytes):
        out = out.decode('utf8')
    return json.loads(out)
