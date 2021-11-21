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

import ssl

from .utils import (find_credential, get_default_host)
from .http import (HTTPConnection, HTTPSConnection)

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'


def connect(host=None, port=None):
    """Open a new connection to a Datafind server

    This method will auto-select between HTTP and HTTPS based on port,
    and (for HTTPS) will automatically load the necessary X509 credentials
    using :func:`gwdatafind.utils.find_credential`.

    Parameters
    ----------
    host : `str`, optional
        the name of the datafind server to connect to; if not given will be
        taken from the ``LIGO_DATAFIND_SERVER`` environment variable.

    port : `int`, optional
        the port on the server to use, if not given it will be stripped from
        the ``host`` name.

    Returns
    -------
    connection : `gwdatafind.HTTPConnection` or `gwdatafind.HTTPSConnection`
        a newly opened connection
    """
    if host is None:
        host = get_default_host()
    if port is None:
        try:
            host, port = host.rsplit(':', 1)
        except ValueError:
            pass
        else:
            port = int(port)
    if port not in (None, 80):
        cert, key = find_credential()
        context = ssl.create_default_context()
        context.load_cert_chain(cert, key)
        return HTTPSConnection(host=host, port=port, context=context)
    return HTTPConnection(host=host, port=port)


def _with_connection(func):
    def wrapper(*args, **kwargs):
        if not kwargs.get('connection'):
            kw = {key: kwargs.pop(key, None) for key in ('host', 'port')}
            kwargs['connection'] = connect(**kw)
        return func(*args, **kwargs)
    return wrapper


def _ui_factory(target):
    @_with_connection
    def finder(*args, **kwargs):
        connection = kwargs.pop('connection')
        return getattr(connection, target)(*args, **kwargs)

    finder.__doc__ = getattr(HTTPConnection, target).__doc__

    return finder


ping = _ui_factory('ping')
find_observatories = _ui_factory('find_observatories')
find_types = _ui_factory('find_types')
find_times = _ui_factory('find_times')
find_url = _ui_factory('find_url')
find_urls = _ui_factory('find_urls')
find_latest = _ui_factory('find_latest')
