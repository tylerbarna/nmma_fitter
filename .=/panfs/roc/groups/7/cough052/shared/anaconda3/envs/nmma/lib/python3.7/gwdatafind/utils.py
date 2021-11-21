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

"""Utilities for the GW datafind service
"""

import calendar
import os
import time
from operator import attrgetter

from OpenSSL import crypto

from ligo.segments import segment


def get_default_host():
    """Returns the default host as stored in the ``${LIGO_DATAFIND_SERVER}``

    Returns
    -------
    host : `str`
        the URL of the default host

    Raises
    ------
    ValueError
        if the ``LIGO_DATAFIND_SERVER`` environment variable is not set
    """
    try:
        return os.environ['LIGO_DATAFIND_SERVER']
    except KeyError:
        raise ValueError("Failed to determine default gwdatafind host, please "
                         "pass manually or set the `LIGO_DATAFIND_SERVER` "
                         "environment variable")


def validate_proxy(path):
    """Validate an X509 proxy certificate file.

    This function tests that the proxy certificate is
    `RFC 3820 <https://www.ietf.org/rfc/rfc3820.txt>` compliant and is
    not expired.

    Parameters
    ----------
    path : `str`
        the path of the X509 file on disk.

    Returns
    -------
    valid : `True`
        if the certificate valides.

    Raises
    ------
    RuntimeError
        if the certificate cannot be validated.
    """
    # load the proxy from path
    with open(path, 'rt') as f:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())

    # try and read proxyCertInfo
    for i in range(cert.get_extension_count()):
        if cert.get_extension(i).get_short_name() == 'proxyCertInfo':
            break
    else:  # not rfc3820
        if cert.get_subject().CN.startswith('proxy'):
            raise RuntimeError('Could not find a valid proxy credential')

    # check time remaining
    expiry = cert.get_notAfter()
    if isinstance(expiry, bytes):
        expiry = expiry.decode('utf-8')
    expiryu = calendar.timegm(time.strptime(expiry, "%Y%m%d%H%M%SZ"))
    if expiryu < time.time():
        raise RuntimeError('Required proxy credential has expired')

    # return True to indicate validated proxy
    return True


def find_credential():
    """Locate X509 certificate and key files.

    This function checks the following paths in order:

    - ``${X509_USER_PROXY}``
    - ``${X509_USER_CERT}`` and ``${X509_USER_KEY}``
    - ``/tmp/x509up_u${UID}``

    Returns
    -------
    cert, key : `str`, `str`
        the paths of the certificate and key files, respectively.

    Raises
    ------
    RuntimeError
        if not certificate files can be found, or if the files found on
        disk cannot be validtted.
    """
    try:  # use X509_USER_PROXY from environment if set
        cert = key = os.environ['X509_USER_PROXY']
    except KeyError:
        try:  # otherwise use _CERT and _KEY from env
            cert = os.environ['X509_USER_CERT']
            key = os.environ['X509_USER_KEY']
        except KeyError:  # otherwise fall back to default LIGO path
            try:
                uid = os.getuid()
            except AttributeError:  # windows
                raise RuntimeError("Could not find X509 credential in either "
                                   "X509_USER_PROXY or X509_USER_{CERT,KEY} "
                                   "environment variables. "
                                   "Please set these and try again")
            cert = key = "/tmp/x509up_u%d" % uid
    if os.access(cert, os.R_OK) and validate_proxy(cert):
        return cert, key

    raise RuntimeError("Could not find a RFC 3820 compliant proxy credential. "
                       "Please run 'grid-proxy-init -rfc' and try again.")


# -- LIGO-T050017 filename parsing --------------------------------------------

def filename_metadata(filename):
    """Return metadata parsed from a filename following LIGO-T050017

    Parameters
    ----------
    filename : `str`
        the path name of a file

    Returns
    -------
    obs : `str`
        the observatory metadata

    tag : `str`
        the file tag

    segment : `ligo.segments.segment`
        the GPS ``[start, stop)`` interval for this file

    Notes
    -----
    `LIGO-T050017 <https://dcc.ligo.org/LIGO-T050017>`__ declares a
    file naming convention that includes documenting the GPS start integer
    and integer duration of a file, see that document for more details.
    """
    obs, desc, start, end = os.path.basename(filename).split('-')
    start = int(start)
    end = int(end.split('.')[0])
    return obs, desc, segment(start, start+end)


def file_segment(filename):
    """Return the data segment for a filename following LIGO-T050017.

    Parameters
    ----------
    filename : `str`
        the path of a file.

    Returns
    -------
    segment : `~ligo.segments.segment`
        the ``[start, stop)`` GPS segment covered by the given file
    """
    return filename_metadata(filename)[2]
