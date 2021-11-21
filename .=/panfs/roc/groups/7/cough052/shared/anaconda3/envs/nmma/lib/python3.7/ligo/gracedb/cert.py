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

# This file contains x509 certificate loading and checking tools.
# Mostly duplicated effort from Tanner's work in support of certificate
# reloading, but it could be useful for giving the client the option
# of checking their certificates, or displaying certificate validity and
# expiration dates when they use the 'gracedb credentials client' command.

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import datetime

far_future = datetime.timedelta(days=365)


# Takes in the path of a certificate and retrrns an x509.cryptography
# certificate object. This removes the prior check that the auth_type
# be 'x509' since this should only be called when reload_certificate
# is true, which checks for x509, or in cases in general when users want
# to check a cert without connecting a client.

def load_certificate(cert):
    """ Loads in a path to a x509 certificate and returns a
        x509.cryptography object """

    # Check certificate type. First check if cert is a tuple, then
    # take the first entry, which is assumed to be the cert.
    # If it's a string, then take that. Otherwise fail.

    if isinstance(cert, tuple):
        cert_file = cert[0]
    elif isinstance(cert, str):
        cert_file = cert
    else:
        raise RuntimeError('Unknown certificate format. Certificate must '
                           'be a tuple of format ("/path/to/cert",'
                           '"/path/to/key") or a string or the path to the '
                           'combined certificate/key')

    with open(cert_file, 'rb') as cert_obj:
        cert_obj = cert_obj.read()

    # Try loading with PEM, then try loading with DER, then give up.

    try:
        return x509.load_pem_x509_certificate(
            cert_obj, default_backend()
        )
    except ValueError:
        try:
            return x509.load_der_x509_certificate(
                cert_obj, default_backend()
            )
        except ValueError:
            raise RuntimeError('Error importing certificate')


# Checks certificate expiration and returns a boolean. Optionally checks
# that the time left until expiration within the 'reload_buffer' parameter.

def check_certificate_expiration(cert, reload_buffer=0):
    """ Checks to see if a cert is expiring within an optional
        reload_buffer parameter. Default, reload_buffer=0, meaning
        is the certificate currently expired.

        cert is either a string path to an x509 cert, or a x509
        cryptography certificate object """

    if not hasattr(cert, 'subject'):
        cert = load_certificate(cert)

    expired = (cert.not_valid_after - datetime.datetime.utcnow()) <= \
        datetime.timedelta(seconds=reload_buffer)

    return expired
