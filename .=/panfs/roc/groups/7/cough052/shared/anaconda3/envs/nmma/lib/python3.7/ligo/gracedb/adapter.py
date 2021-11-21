# -*- coding: utf-8 -*-
# Copyright (C) Alexander Pace, Tanner Prestegard,
#               Branson Stephens, Brian Moe (2020)
#
# This file is part of gracedb
#
# gracedb is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gracedb.  If not, see <http://www.gnu.org/licenses/>

# Sources:
#  1) https://stackoverflow.com/questions/45539422/can-we-reload-a-page-url-
#     in-python-using-urllib-or-urllib2-or-requests-or-mechan

#  2) https://2.python-requests.org/en/master/user/advanced/#example-
#     specific-ssl-version

#  3) https://urllib3.readthedocs.io/en/1.2.1/pools.html


from functools import partial
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.connection import HTTPSConnection
from requests.packages.urllib3.connectionpool \
    import HTTPSConnectionPool, HTTPConnectionPool
from .cert import check_certificate_expiration


class GraceDbCertAdapter(HTTPAdapter):
    def __init__(self, cert=None, reload_buffer=0, **kwargs):
        super(GraceDbCertAdapter, self).__init__(**kwargs)
        https_pool_cls = partial(
            GraceDbCertHTTPSConnectionPool,
            cert=cert,
            reload_buffer=reload_buffer)

        self.poolmanager.pool_classes_by_scheme = {
            'http': HTTPConnectionPool,
            'https': https_pool_cls
        }


class GraceDbCertHTTPSConnection(HTTPSConnection):
    def __init__(self, host, cert=None, reload_buffer=0, **kwargs):
        # At this point, te HTTPSConnection is initialized
        # but unconnected. Set this property to 'True'
        self.unestablished_connection = True
        super(GraceDbCertHTTPSConnection, self).__init__(host, **kwargs)

    @property
    def unestablished_connection(self):
        return self._unestablished_connection

    @unestablished_connection.setter
    def unestablished_connection(self, value):
        self._unestablished_connection = value

    def connect(self):
        # Connected. After this step, the unestablished
        # property is false.
        self.unestablished_connection = False
        super(GraceDbCertHTTPSConnection, self).connect()


class GraceDbCertHTTPSConnectionPool(HTTPSConnectionPool):
    # ConnectionPool object gets used in the HTTPAdapter.
    # "ConnectionCls" is a HTTP(S)COnnection object to use
    # As the underlying connection.

    # Source: https://urllib3.readthedocs.io/en/latest/
    #         reference/#module-urllib3.connectionpool

    ConnectionCls = GraceDbCertHTTPSConnection

    def __init__(self, host, port=None, cert=None,
                 reload_buffer=0, **kwargs):

        super(GraceDbCertHTTPSConnectionPool, self).__init__(
            host, port=port, **kwargs)

        self._cert = cert
        self._reload_buffer = reload_buffer

    def _expired_cert(self):
        return check_certificate_expiration(
            self._cert,
            self._reload_buffer)

    def _get_conn(self, timeout=None):
        while True:
            # Start the connection object. At this step, the connection
            # unestablished variable is true
            conn = super(GraceDbCertHTTPSConnectionPool, self)._get_conn(
                timeout)

            # 'returning' the connection object then triggers the
            # connection to be established. Establish a new connection
            # if it's unestablished, or if the cert expiration is within the
            # reload buffer. Establishing the new connection will (hopefully
            # load the new cert.
            if conn.unestablished_connection or not self._expired_cert():
                return conn

            # otherwise, kill the connection which will reset unestablished_..
            # to true and then exit the loop.
            conn.close()
