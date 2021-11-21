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
# along with gracedb.  If not, see <http://www.gnu.org/licenses/>.
import os
import sys
import json as json_lib

from warnings import warn
from requests import Session
from .extern.safe_netrc import netrc
from os import getuid
from .version import __version__
from .adapter import GraceDbCertAdapter
from .utils import hook_response, raise_status_exception

# To remove later: python2 compatibility fix:
if sys.version_info[0] > 2:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse

DEFAULT_SERVICE_URL = "https://gracedb.ligo.org/api/"


class GraceDBClient(Session):
    """
    url (:obj:`str`, optional): URL of server API
    cred (:obj:`tuple` or :obj:`str, optional): a tuple or list of
        (``/path/to/cert/file``, ``/path/to/key/file) or a single path to
        a combined proxy file (if using an X.509 certificate for
        authentication)
    username (:obj:`str`, optional): username for basic auth
    password (:obj:`str`, optional): password for basic auth
    force_noauth (:obj:`bool`, optional): set to True if you want to skip
        credential lookup and use this client as an unauthenticated user
    fail_if_noauth (:obj:`bool`, optional): set to True if you want the
        constructor to fail if no authentication credentials are provided
        or found
    reload_certificate (:obj:`bool`, optional): if ``True``, your
        certificate will be checked before each request whether it is
        within ``reload_buffer`` seconds of expiration, and if so, it will
        be reloaded. Useful for processes which may live longer than the
        certificate lifetime and have an automated method for certificate
        renewal. The path to the new/renewed certificate **must** be the
        same as for the old certificate.
    reload_buffer (:obj:`int`, optional): buffer (in seconds) for reloading
        a certificate in advance of its expiration. Only used if
        ``reload_certificate`` is ``True``.

    Authentication details:
    You can:
        1. Provide a path to an X.509 certificate and key or a single
           combined proxy file
        2. Provide a username and password
    Or:
        The code will look for a certificate in a default location
            (``/tmp/x509up_u%d``, where ``%d`` is your user ID)
        The code will look for a username and password for the specified
            server in ``$HOME/.netrc``
    """

    def __init__(self, url=DEFAULT_SERVICE_URL, cred=None, username=None,
                 password=None, force_noauth=False, fail_if_noauth=False,
                 reload_certificate=False, reload_buffer=300,
                 *args, **kwargs):
        super(GraceDBClient, self).__init__(*args, **kwargs)

        # Initialize variables:
        self.cert = None
        self.auth = None
        self.host = urlparse(url).hostname
        self.auth_type = None

        # Set up credentials. First, only attempt if the user did not
        # force noauth:
        if not force_noauth:
            # Attempt to assign x509 credentials.
            if cred or not (username or password):
                self.cert = self._get_x509_credentials(cred)

            # if we weren't able to determine a x509 certificate,
            # then look for basic auth.
            if not self.cert:
                self.auth = self._process_basic_credentials(username,
                                                            password)

                # If no basic auth credentials were provided, and
                # fail_if_noauthis set, then fail.
                if not self.auth:
                    if fail_if_noauth:
                        raise RuntimeError("No authentication credentials "
                                           "could be found, and fail_if_"
                                           "noauth is set.")
                    else:
                        warn("Authentication credentials not found, "
                             "proceeding with unauthorized session")

        elif fail_if_noauth:
            raise ValueError('You have provided conflicting parameters '
                             'to the client constructor: '
                             'fail_if_noauth=True and force_noauth=True.')

        # Update session headers:
        self.headers.update(self._update_headers())

        # Adjust the response via a session hook:
        self.hooks = {'response': [hook_response, raise_status_exception]}

        if reload_certificate and self.auth_type == 'x509':
            self.mount('https://', GraceDbCertAdapter(
                       cert=self.cert,
                       reload_buffer=reload_buffer))

    def _process_basic_credentials(self, username, password):
        """ Gathers basic auth credentials. First it looks for
            the input username/password, then checks the netrc file
        """

        # Checks username/password:
        if username and password:
            self.auth_type = 'basic'
            return username, password
        # If one or the other is provided, but not both, raise an error.
        elif bool(username) != bool(password):
            raise RuntimeError('You must provide both a username and a '
                               'password for basic authentication.')
        # Finally, try the netrc fle:
        else:
            try:
                netrc_auth = netrc().authenticators(self.host)
            except IOError:
                pass
            else:
                if netrc_auth is not None:
                    self.auth_type = 'basic'
                    return netrc_auth[0], netrc_auth[2]

        # If that didn't work, then give up.
        return

    def _get_x509_credentials(self, cred):
        """ Get a user's x509 credentials. Look in the following locations.
               1) 'cred' input variable, either cert/key pair or combined file
               2) $X509_USER_CERT/KEY/PROXY environment variables.
                  - X509_USER_PROXY: combined cert/cert pair
                  - X509_USER_CERT: x509 certificate file.
                  - X509_USER_KEY: corresponding x509 private key.
               3) Auto-generated grid proxy in /tmp/x509up_$UID
        """

        # First use the contents of the 'cred' variable.
        # Assume that you'll find the x509 credentials *somewhere*
        # in here. Switch it back at the end if you don't.
        self.auth_type = 'x509'
        if cred:
            # if it's a list or a tuple, then return the pair
            # as a tuple to the session
            if isinstance(cred, (list, tuple)):
                return tuple(cred)
            elif isinstance(cred, str) and os.path.exists(cred):
                return cred
            else:
                warn("x509 cert/key/pair provided by 'cert' variable "
                     "is invalid, or not found.")
                return None

        # Now: check envionment variables:
        grid_proxy_file = os.environ.get('X509_USER_PROXY')
        grid_cert_file = os.environ.get('X509_USER_CERT')
        grid_key_file = os.environ.get('X509_USER_KEY')

        # Set logic for returning credentials:
        # If the user supplies both a cert and key, return those:

        if grid_cert_file and grid_key_file:
            return grid_cert_file, grid_key_file
        # If the user supplies a proxy file, then return it:
        elif grid_proxy_file:
            return grid_proxy_file

        # If the user supplies one or the other, then return a warning
        elif grid_cert_file or grid_key_file:
            warn("Warning: must supply a $X509_USER_PROXY or a "
                 "X509_USER_CERT/KEY pair. Proceeding with unauthenticated "
                 "session")
            return None

        # Next try the usual grid-proxy location:
        uid = getuid()
        if uid is not None:
            grid_proxy_file = os.path.join('/tmp', 'x509up_u{}'.format(uid))
            if os.path.exists(grid_proxy_file):
                return grid_proxy_file

        # Finally the default globus key/cert files:
        homedir = os.environ.get('HOME')
        if homedir:
            globus_cert_file = os.path.join(homedir, '.globus', 'usercert.pem')
            globus_key_file = os.path.join(homedir, '.globus', 'userkey.pem')

            if (os.path.exists(globus_cert_file)
                and os.path.exists(globus_key_file)):
                return globus_cert_file, globus_key_file

        # Give up otherwise:
        warn("No x509 credentials found")
        self.auth_type = None

        return None

    def _update_headers(self):
        """ Update the sessions' headers:
        """
        new_headers = {}
        # Assign the user agent. This shows up in gracedb's log files.
        new_headers.update({'User-Agent':
                            'gracedb-client/{}'.format(__version__)})
        new_headers.update({'Accept-Encoding':
                            'gzip, deflate'})
        return new_headers

    # hijack 'Session.request':
    # https://2.python-requests.org/en/master/api/#requests.Session.request
    def request(
            self, method, url, params=None, data=None, headers=None,
            cookies=None, files=None, auth=None, timeout=None,
            allow_redirects=True, proxies=None, hooks=None, stream=None,
            verify=None, cert=None, json=None):
        return super(GraceDBClient, self).request(
            method, url, params=params, data=data, headers=headers,
            cookies=cookies, files=files, auth=auth,
            timeout=timeout, allow_redirects=True, proxies=proxies,
            hooks=hooks, stream=stream, verify=verify, cert=cert, json=json)

    # Extra definitions to return closed contexts' connections
    # back to the pool:
    # https://stackoverflow.com/questions/48160728/resourcewarning
    # -unclosed-socket-in-python-3-unit-test
    def close(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # For getting files, return a "raw" file-type object.
    # Automatically decode content.
    def get_file(self, url, **kwargs):
        resp = self.get(url, stream=True, **kwargs)
        resp.raw.decode_content = True
        resp.raw.status_code = resp.status_code
        resp.raw.json = resp.json
        return resp.raw

    # Return client credentials
    def show_credentials(self, print_output=True):
        """ Prints authentication type and credentials info."""
        output = {'auth_type': self.auth_type}

        cred = {}

        if self.auth_type == 'x509':
            if isinstance(self.cert, tuple):
                cred = {'cert_file': self.cert[0],
                        'key_file': self.cert[1]}
            elif isinstance(self.cert, str):
                cred = {'cert_file': self.cert,
                        'key_file': self.cert}
            else:
                raise ValueError("Problem reading authentication certificate")

        if self.auth_type == 'basic':
            cred = {'username': self.auth[0],
                    'password': self.auth[1]}

        output.update(cred)

        if print_output:
            print(output)
        else:
            return output

    def get_user_info(self):
        """Get information from the server about your user account."""
        user_info_link = self.links.get('user-info', None)
        if user_info_link is None:
            raise RuntimeError('Server does not provide a user info endpoint')
        return self.get(user_info_link)

    @classmethod
    def load_json_from_response(cls, response):
        """ Always return a json content response, even when the server
            provides a 204: no content"""
        # Check if response exists:
        if not response:
            raise ValueError("No response object provided")

        # Check if there is response content. If not, create it.
        if response.content == 'No Content':
            response_content = '{}'

        # Some responses send back strings of strings. This iterates
        # until proper dict is returned, or if it doesn't make progress.
        num_tries = 1
        response_content = response.content.decode('utf-8')

        while type(response_content) == str and num_tries < 3:
            response_content = json_lib.loads(response_content)
            num_tries += 1

        if type(response_content) == dict:
            return response_content
        else:
            return ValueError("ERROR: got unexpected content from "
                              "the server: {}".format(response_content))
