import itertools
import pytest
try:
    from unittest import mock
except ImportError:  # py < 3
    import mock

from ligo.gracedb.rest import GraceDb
from ligo.gracedb.cert import check_certificate_expiration


def test_x509_cert_load():
    """Test loading of X.509 certificate during client instantiation"""
    # Set up cert and key files
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    load_cert_func = 'ligo.gracedb.cert.load_certificate'
    with mock.patch(load_cert_func) as mock_load_cert:
        # Initialize client
        g = GraceDb(cred=(cert_file, key_file))

    # Check credentials
    assert len(g.cert) == 2
    assert g.auth_type == 'x509'
    assert g.cert[0] == cert_file
    assert g.cert[1] == key_file
    assert mock_load_cert.called_once()


@pytest.mark.parametrize("reload_buffer", [86400, 10])
def test_x509_cert_expiration(reload_buffer, x509_cert):
    """Test X.509 certificate expiration check"""

    # Check if certificate is expired (should have 3600 second lifetime)
    # compared to reload_buffer
    expired = check_certificate_expiration(x509_cert,
                                           reload_buffer=reload_buffer)
    if reload_buffer > 3600:
        assert expired is True
    else:
        assert expired is False

# AEP: test depreciated.
# def test_x509_cert_autoload_in_expiration_check():

# AEP: test depreciated. 'load_certificate" decoupled from client class
# and does not depend on auth_type.
# def test_load_certificate_with_auth_type_not_x509():

# AEP: test depeciated. 'check_certificate_expiration' decoupled from
# client class and does not check auth_type.
# def test_check_certificate_with_auth_type_not_x509():


# All possible combinations of True/False for the three variables
RELOAD_TEST_DATA = list(itertools.product((True, False), repeat=3))
@pytest.mark.skip(reason="tested online, figure out mocking in pytest'")
@pytest.mark.parametrize("force_noauth,reload_cert,cert_expired",  # noqa: E302
                         RELOAD_TEST_DATA)
def test_reloading_feature(force_noauth, reload_cert, cert_expired):
    # Set up cert and key files
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    set_up_conn_func = \
        'ligo.gracedb.adapter.GraceDbCertHTTPSConnection.connect'
    get_conn_func = \
        'ligo.gracedb.adapter.GraceDbCertHTTPSConnectionPool._get_conn'
    load_cert_func = 'ligo.gracedb.cert.load_certificate'
    cert_expire_func = \
        'ligo.gracedb.cert.check_certificate_expiration'
    with mock.patch(get_conn_func), \
         mock.patch(set_up_conn_func) as mock_set_up_conn, \
         mock.patch(load_cert_func) as mock_load_cert, \
         mock.patch(cert_expire_func) as mock_cert_expire:  # noqa: E127

        # Set return value for mock_cert_expire
        mock_cert_expire.return_value = cert_expired

        # Initialize client
        g = GraceDb(
            cred=(cert_file, key_file),
            reload_certificate=reload_cert,
            force_noauth=force_noauth
        )

        # Try to make a request
        g.get("https://fakeurl.com")

        # Compile number of times which we expect certain functions to be
        # called
        check_cert_call_count = 0
        set_up_conn_call_count = 0
        load_cert_call_count = int(not force_noauth)

        if g.auth_type == 'x509' and reload_cert:
            check_cert_call_count += 1
            if cert_expired:
                load_cert_call_count += 1
                set_up_conn_call_count += 1

        # Compare to actual results
        assert mock_load_cert.call_count == load_cert_call_count
        assert mock_cert_expire.call_count == check_cert_call_count
        assert mock_set_up_conn.call_count == set_up_conn_call_count
