import datetime
try:
    from unittest import mock
except ImportError:
    import mock

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
import pytest

from ligo.gracedb.rest import GraceDb


@pytest.fixture
def safe_client():
    """A client class which has its request() method mocked away"""
    client = GraceDb()
    client.request = mock.Mock()
    return client


@pytest.fixture
def x509_key():
    """X.509 private key"""
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    return key


@pytest.fixture
def x509_cert(x509_key):
    """Self-signed X.509 certificate, valid for 1 hour"""
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Wisconsin"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Milwaukee"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"My Company"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"mysite.com"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        x509_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Our certificate will be valid for 1 hour
        datetime.datetime.utcnow() + datetime.timedelta(seconds=3600)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,  # noqa: E122
    # Sign our certificate with our private key
    ).sign(x509_key, hashes.SHA256(), default_backend())

    return cert
