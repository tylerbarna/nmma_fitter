# -*- coding: utf-8 -*-
# Copyright (C) Brian Moe, Branson Stephens (2015)
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
from base64 import b64encode
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import datetime
from io import open
import json
import os
import socket
import ssl
import sys

import six
from six.moves import http_client
from six.moves.urllib.parse import urlparse
import mimetypes


from .exceptions import HTTPError
from .extern.safe_netrc import netrc as safe_netrc
from .version import __version__

DEFAULT_SERVICE_URL = "https://gracedb.ligo.org/api/"

# ----------------------------------------------------------------
# HTTP/S Proxy classes
# Taken from: http://code.activestate.com/recipes/456195/


class ProxyHTTPConnection(http_client.HTTPConnection):

    _ports = {'http': 80, 'https': 443}

    def request(self, method, url, body=None, headers={}):
        # request is called before connect, so can interpret url and get
        # real host/port to be used to make CONNECT request to proxy
        o = urlparse(url)
        proto = o.scheme
        port = o.port
        host = o.hostname
        if proto is None:
            raise ValueError("unknown URL type: %s" % url)
        if port is None:
            try:
                port = self._ports[proto]
            except KeyError:
                raise ValueError("unknown protocol for: %s" % url)
        self._real_host = host
        self._real_port = port
        http_client.HTTPConnection.request(self, method, url, body, headers)

    def connect(self):
        http_client.HTTPConnection.connect(self)
        # send proxy CONNECT request
        self.send("CONNECT {0}:{1} HTTP/1.0\r\n\r\n".format(
                  self._real_host, self._real_port))
        # expect a HTTP/1.0 200 Connection established
        response = self.response_class(self.sock, strict=self.strict,
                                       method=self._method)
        (version, code, message) = response._read_status()
        # probably here we can handle auth requests...
        if code != 200:
            # proxy returned and error, abort connection, and raise exception
            self.close()
            raise socket.error("Proxy connection failed: {0} {1}".format(
                               code, message.strip()))
        # eat up header block from proxy....
        while True:
            # should not use directly fp probably
            line = response.fp.readline()
            if line == '\r\n':
                break


class ProxyHTTPSConnection(ProxyHTTPConnection):
    default_port = 443

    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, context=None):
        ProxyHTTPConnection.__init__(self, host, port)
        self.key_file = key_file
        self.cert_file = cert_file
        self.context = context

    def connect(self):
        ProxyHTTPConnection.connect(self)
        # make the sock ssl-aware
        self.sock = self.context.wrap_socket(self.sock)


# ----------------------------------------------------------------
# Legacy GSI REST Client
class LegacyGsiRest(object):
    def __init__(self, url=DEFAULT_SERVICE_URL, proxy_host=None,
                 proxy_port=3128, cred=None, username=None, password=None,
                 force_noauth=False, fail_if_noauth=False,
                 reload_certificate=False, reload_buffer=300):
        """
        url (:obj:`str`, optional): URL of server API
        proxy_host (:obj:`str`, optional): proxy host
        proxy_port (:obj:`str`, optional): proxy port
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
        # Process service URL
        o = urlparse(url)
        host = o.hostname
        port = o.port or 443

        # Store some of this information
        self._server_host = host
        self._server_port = port
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._reload_certificate = reload_certificate
        self._reload_buffer = reload_buffer

        # Store information about credentials and authentication type
        self.credentials = {}
        self.auth_type = None

        # Fail if conflicting arguments: (fail if no auth, but force no auth)
        if fail_if_noauth and force_noauth:
            err_msg = ('You have provided conflicting parameters to the '
                       'client constructor: fail_if_noauth=True and '
                       'force_noauth=True.')
            raise ValueError(err_msg)

        # Try to get user-provided credentials, if we aren't forcing
        # no authentication
        if not force_noauth:
            credentials_provided = self._process_credentials(
                cred, username, password)

        # If the user didn't provide credentials in the constructor,
        # we try to look up the credentials
        if not force_noauth and not credentials_provided:
            # Look for X509 certificate and key
            cred = self._find_x509_credentials()
            if cred:
                self.credentials['cert_file'], self.credentials['key_file'] = \
                    cred
                self.auth_type = 'x509'
            else:
                # Look for basic auth credentials in .netrc file
                try:
                    basic_auth_tuple = safe_netrc().authenticators(host)
                except IOError:
                    # IOError = no .netrc file found, pass
                    pass
                else:
                    # If credentials were found for host, set them up!
                    if basic_auth_tuple is not None:
                        self.credentials['username'] = basic_auth_tuple[0]
                        self.credentials['password'] = basic_auth_tuple[2]
                        self.auth_type = 'basic'

        if (fail_if_noauth and not self.credentials):
            raise RuntimeError('No authentication credentials found.')

        # If we are using basic auth, construct auth header
        if (self.auth_type == 'basic'):
            user_and_pass = b64encode('{username}:{password}'.format(
                username=self.credentials['username'],
                password=self.credentials['password']).encode()) \
                .decode('ascii')
            self.authn_header = {
                'Authorization': 'Basic {0}'.format(user_and_pass),
            }

        # If we are using X.509 auth, load the certificate with the
        # cryptography.x509 module
        if (self.auth_type == 'x509'):
            self._load_certificate()

        # Construct version header
        self.version_header = {'User-Agent': 'gracedb-client/{version}'.format(
            version=__version__)}

        # Set up SSL context and connector
        self.set_up_connector(host, port, proxy_host, proxy_port)

    def _load_certificate(self):
        if not self.auth_type == 'x509':
            raise RuntimeError("Can't load certificate for "
                               "non-X.509 authentication.")

        # Open cert file and load it as bytes
        with open(self.credentials['cert_file'], 'rb') as cf:
            cert_data = cf.read()

        # Certificates should be PEM, but just in case, we'll try
        # DER if loading a PEM certificate fails
        try:
            self.certificate = x509.load_pem_x509_certificate(
                cert_data, default_backend()
            )
        except ValueError:
            try:
                self.certificate = x509.load_der_x509_certificate(
                    cert_data, default_backend()
                )
            except ValueError:
                raise RuntimeError('Error importing certificate')

    def _check_certificate_expiration(self, reload_buffer=None):
        if reload_buffer is None:
            reload_buffer = self._reload_buffer
        if (self.auth_type != 'x509'):
            raise RuntimeError("Can't check certificate expiration for "
                               "non-X.509 authentication.")
        if not hasattr(self, 'certificate'):
            self._load_certificate()

        # Compare certificate expiration to current time (UTC)
        # (certs use UTC until 2050, see https://tools.ietf.org/html/rfc5280)
        time_to_expire = \
            (self.certificate.not_valid_after - datetime.datetime.utcnow())
        expired = \
            time_to_expire <= datetime.timedelta(seconds=reload_buffer)
        return expired

    def print_certificate_subject(self):
        if not hasattr(self, 'certificate'):
            raise RuntimeError('No certificate found.')
        print(self.certificate.subject.rfc4514_string())

    def print_certificate_expiration_date(self):
        if not hasattr(self, 'certificate'):
            raise RuntimeError('No certificate found.')
        out_str = '{dt} UTC'.format(dt=self.certificate.not_valid_after)
        print(out_str)

    def set_up_connector(self, host, port, proxy_host, proxy_port):
        # Prepare SSL context
        # Fix for python < 2.7.13
        # https://docs.python.org/2/library/ssl.html#ssl.PROTOCOL_TLS
        # This *needs* to be updated. Eventually 2.7.5 support is going
        # to have to stop.
        if sys.version_info >= (2, 7, 13):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        else:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)

        if (self.auth_type == 'x509'):
            try:
                ssl_context.load_cert_chain(self.credentials['cert_file'],
                                            self.credentials['key_file'])
            except ssl.SSLError:
                msg = ("\nERROR: Unable to load cert/key pair.\n\nPlease "
                       "run ligo-proxy-init or grid-proxy-init again or "
                       "make sure your robot certificate is readable.\n\n")
                self.output_and_die(msg)
        # Load and verify certificates
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True
        # Find the various CA cert bundles stored on the system
        ssl_context.load_default_certs()

        if proxy_host:
            self.connector = lambda: ProxyHTTPSConnection(
                proxy_host, proxy_port, context=ssl_context)
        else:
            self.connector = lambda: http_client.HTTPSConnection(
                host, port, context=ssl_context)

    def _process_credentials(self, cred, username, password):
        """Process credentials provided in the constructor"""
        credentials_provided = False
        if cred:
            if isinstance(cred, (list, tuple)):
                self.credentials['cert_file'], self.credentials['key_file'] = \
                    cred
            else:
                self.credentials['cert_file'] = cred
                self.credentials['key_file'] = cred
            credentials_provided = True
            self.auth_type = 'x509'
        elif username and password:
            self.credentials['username'] = username
            self.credentials['password'] = password
            credentials_provided = True
            self.auth_type = 'basic'
        elif (username is None) ^ (password is None):
            raise RuntimeError('Must provide both username AND password for '
                               'basic auth.')

        return credentials_provided

    def _find_x509_credentials(self):
        """
        Tries to find a user's X509 certificate and key.  Checks environment
        variables first, then expected location for default proxy.
        """
        proxyFile = os.environ.get('X509_USER_PROXY')
        certFile = os.environ.get('X509_USER_CERT')
        keyFile = os.environ.get('X509_USER_KEY')

        if certFile and keyFile:
            return certFile, keyFile

        if proxyFile:
            return proxyFile, proxyFile

        # Try default proxy
        proxyFile = os.path.join('/tmp', "x509up_u%d" % os.getuid())
        if os.path.exists(proxyFile):
            return proxyFile, proxyFile

        # Try default cert/key
        homeDir = os.environ.get('HOME', None)
        if homeDir:
            certFile = os.path.join(homeDir, '.globus', 'usercert.pem')
            keyFile = os.path.join(homeDir, '.globus', 'userkey.pem')

            if os.path.exists(certFile) and os.path.exists(keyFile):
                return certFile, keyFile

    def show_credentials(self, print_output=True):
        """Prints authentication type and credentials information."""
        output = {'auth_type': self.auth_type}
        output.update(self.credentials)

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

    def getConnection(self):
        return self.connector()

    # When there is a problem with the SSL connection or cert authentication,
    # either conn.request() or conn.getresponse() will throw an exception.
    # The following two wrappers are intended to catch these exceptions and
    # return an intelligible error message to the user.
    # A wrapper for getting the response:
    def get_response(self, conn):
        try:
            return conn.getresponse()
        except ssl.SSLError as e:

            if (self.auth_type == 'x509'):
                # Check for a valid user proxy cert.
                expired = self._check_certificate_expiration(reload_buffer=0)

                if expired:
                    msg = ("\nERROR\n\nYour certificate or proxy has "
                           "expired. Please run ligo-proxy-init or "
                           "grid-proxy-init (as appropriate) to generate "
                           "a fresh one.\n\n")
                else:
                    msg = ("\nERROR\n\nYour certificate appears valid, "
                           "but there was a problem establishing a secure "
                           "connection: {e}").format(e=str(e))
            else:
                msg = ("\nERROR\n\nProblem establishing secure connection: "
                       "{e}\n\n").format(e=str(e))
            self.output_and_die(msg)

    # A wrapper for making the request.
    def make_request(self, conn, *args, **kwargs):
        try:
            conn.request(*args, **kwargs)
        except ssl.SSLError as e:
            msg = "\nERROR \n\n"
            msg += "Problem establishing secure connection: %s \n\n" % str(e)
            self.output_and_die(msg)

    def make_request_and_get_response(self, conn, method, url, body=None,
                                      headers={}):

        # For X.509 based auth: if the user has specified to reload the
        # certificate (upon expiration), check the certificate to see if it
        # has expired
        if (self.auth_type == 'x509' and self._reload_certificate):
            cert_expired = self._check_certificate_expiration()
            if cert_expired:
                self._load_certificate()
                self.set_up_connector(
                    self._server_host, self._server_port, self._proxy_host,
                    self._proxy_port
                )
                conn = self.getConnection()

        # Make request
        self.make_request(conn, method, url, body=body, headers=headers)

        # Get response
        response = self.get_response(conn)

        return response

    def request(self, method, url, body=None, headers=None, priming_url=None):
        # Bug in Python (versions < 2.7.1 (?))
        # http://bugs.python.org/issue11898
        # if the URL is unicode and the body of a request is binary,
        # the POST/PUT action fails because it tries to concatenate
        # the two which fails due to encoding problems.
        # Workaround is to cast all URLs to str.
        # This is probably bad in general,
        # but for our purposes, today, this will do.
        url = url and str(url)
        priming_url = priming_url and str(priming_url)
        headers = headers or {}
        conn = self.getConnection()

        # Add version string to user-agent header
        headers.update(self.version_header)

        # Add auth header for basic auth
        if (self.auth_type == 'basic'):
            headers.update(self.authn_header)

        # Set up priming URL for certain requests using X509 auth
        if (self.auth_type == 'x509' and priming_url):
            priming_header = {'connection': 'keep-alive'}
            priming_header.update(self.version_header)
            response = self.make_request_and_get_response(
                conn, "GET", priming_url, headers=priming_header
            )
            if response.status != 200:
                response = self.adjustResponse(response)
            else:
                # Throw away the response and make sure to read the body.
                response = response.read()

        response = self.make_request_and_get_response(
            conn, method, url, body=body, headers=headers
        )

        # Special handling of 401 unauthorized response for basic auth
        # to catch expired passwords
        if (self.auth_type == 'basic' and response.status == 401):
            try:
                msg = "\nERROR: {e}\n\n".format(json.loads(
                    response.read())['detail'])
            except Exception:
                msg = "\nERROR:\n\n"
            msg += ("\nERROR:\n\nPlease check the username/password in your "
                    ".netrc file. If your password is more than a year old, "
                    "you will need to use the web interface to generate a new "
                    "one.\n\n")
            self.output_and_die(msg)
        return self.adjustResponse(response)

    def adjustResponse(self, response):
        # XXX WRONG.
        if response.status >= 400:
            response_content = response.read()
            if isinstance(response_content, bytes):
                response_content = response_content.decode()
            if response.getheader('x-throttle-wait-seconds', None):
                try:
                    rdict = json.loads(response_content)
                    rdict['retry-after'] = response.getheader(
                        'x-throttle-wait-seconds')
                    response_content = json.dumps(rdict)
                except Exception:
                    pass
            raise HTTPError(response.status, response.reason, response_content)
        response.json = lambda: self.load_json_or_die(response)
        return response

    def get(self, url, headers=None):
        return self.request("GET", url, headers=headers)

    def head(self, url, headers=None):
        return self.request("HEAD", url, headers=headers)

    def delete(self, url, headers=None):
        return self.request("DELETE", url, headers=headers)

    def options(self, url, headers=None):
        return self.request("OPTIONS", url, headers=headers)

    def post(self, *args, **kwargs):
        return self.post_or_put_or_patch("POST", *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.post_or_put_or_patch("PUT", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.post_or_put_or_patch("PATCH", *args, **kwargs)

    def post_or_put_or_patch(self, method, url, body=None, headers=None,
                             files=None):
        headers = headers or {}
        if not files:
            # Simple urlencoded body
            if isinstance(body, dict):
                # XXX What about the headers in the params?
                if 'content-type' not in headers:
                    headers['content-type'] = "application/json"
                body = json.dumps(body)
        else:
            body = body or {}
            if isinstance(body, dict):
                body = list(body.items())
            content_type, body = encode_multipart_formdata(body, files)
            # XXX What about the headers in the params?
            headers = {
                'content-type': content_type,
                'content-length': str(len(body)),
                # 'connection': 'keep-alive',
            }
        return self.request(method, url, body, headers)

    # A utility for writing out an error message to the user and then stopping
    # execution. This seems to behave sensibly in both the interpreter and in
    # a script.
    @classmethod
    def output_and_die(cls, msg):
        raise RuntimeError(msg)

    # Given an HTTPResponse object, try to read its content and interpret as
    # JSON--or die trying.
    @classmethod
    def load_json_or_die(cls, response):

        # First check that the response object actually exists.
        if not response:
            raise ValueError("No response object")

        # Next, try to read the content of the response.
        response_content = response.read()
        response_content = response_content.decode('utf-8')
        if not response_content:
            response_content = '{}'

        # Finally, try to create a dict by decoding the response as JSON.
        rdict = None
        try:
            rdict = json.loads(response_content)
        except ValueError:
            msg = "ERROR: got unexpected content from the server:\n"
            msg += response_content
            raise ValueError(msg)

        return rdict


# ----------------------------------------------------------------
# HTTP upload encoding
# Taken from http://code.activestate.com/recipes/146306/
def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
        uploaded as files.
    Returns (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = b'\r\n'
    L = []
    for (key, value) in fields:
        if value is None:
            continue
        L.append(('--' + BOUNDARY).encode())
        L.append('Content-Disposition: form-data; name="{0}"'.format(
            key).encode())
        L.append(''.encode())
        # encode in case it is unicode
        if isinstance(value, six.binary_type):
            L.append(value)
        elif isinstance(value, six.text_type):
            L.append(value.encode())
        else:
            L.append(str(value).encode())
    for (key, filename, value) in files:
        if value is None:
            continue
        L.append(('--' + BOUNDARY).encode())
        # str(filename) in case it is unicode
        L.append(('Content-Disposition: form-data; name="{0}"; '
                 'filename="{1}"').format(key, filename).encode())
        L.append('Content-Type: {0}'.format(get_content_type(filename))
                 .encode())
        L.append(''.encode())
        if isinstance(value, six.text_type):
            L.append(value.encode())
        else:
            L.append(value)
    L.append(('--' + BOUNDARY + '--').encode())
    L.append(''.encode())
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary={0}'.format(BOUNDARY) \
        .encode()
    return content_type, body


def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
