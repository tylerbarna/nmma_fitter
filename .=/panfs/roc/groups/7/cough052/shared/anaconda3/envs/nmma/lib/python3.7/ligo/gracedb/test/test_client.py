import pytest
import sys
try:
    from unittest import mock
except ImportError:  # py < 3
    import mock

from ligo.gracedb.rest import GraceDb


def test_provide_x509_cert_and_key():
    """Test client instantiation with provided certificate and key files"""
    # Set up cert and key files
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    load_cert_func = 'ligo.gracedb.cert.load_certificate'
    with mock.patch(load_cert_func):  # noqa: E127
        # Initialize client
        g = GraceDb(cred=(cert_file, key_file))

    # Output credentials:
    creds = g.show_credentials(print_output=False)

    # Check credentials
    assert len(g.cert) == 2
    assert g.auth_type == 'x509'
    assert creds.get('cert_file') == cert_file
    assert creds.get('key_file') == key_file


def test_provide_x509_proxy():
    """Test client instantiation with provided combined proxy file"""
    # Set up combined proxy file
    proxy_file = '/tmp/proxy_file'

    exists_func = 'os.path.exists'
    load_cert_func = 'ligo.gracedb.cert.load_certificate'
    with mock.patch(load_cert_func), \
         mock.patch(exists_func) as mock_exists_func:  # noqa: E127

        mock_exists_func.return_value = True
        # Initialize client
        g = GraceDb(cred=proxy_file)

    # Output credentials:
    creds = g.show_credentials(print_output=False)

    # Check credentials
    assert type(g.cert) == str
    assert g.auth_type == 'x509'
    assert creds.get('cert_file') == proxy_file
    assert creds.get('key_file') == proxy_file


USER_PASS_TEST_DATA = [
    {'username': 'user', 'password': 'pw'},
    {'username': 'user'},
    {'password': 'pwd'},
]
@pytest.mark.parametrize("user_and_or_pass", USER_PASS_TEST_DATA)  # noqa: E302
def test_provide_username_and_password(user_and_or_pass):
    """Test client instantiation with provided username and or password"""

    # Initialize client - should fail if only one of username and
    # password is provided
    if not len(user_and_or_pass) == 2:
        err_str = 'You must provide both a username and a password '\
                  'for basic authentication'
        with pytest.raises(RuntimeError, match=err_str):
            g = GraceDb(**user_and_or_pass)
    else:
        g = GraceDb(**user_and_or_pass)

        # Output credentials:
        creds = g.show_credentials(print_output=False)

        assert len(g.auth) == 2
        assert g.auth_type == 'basic'
        assert creds.get('username') == \
            user_and_or_pass.get('username')
        assert creds.get('password') == \
            user_and_or_pass.get('password')


def test_provide_all_creds():
    """Test providing all credentials to the constructor"""
    # Setup
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'
    username = 'user'
    password = 'pw'

    # Initialize client
    g = GraceDb(
        cred=(cert_file, key_file), username=username, password=password
    )

    # Check credentials - should prioritze x509 credentials
    creds = g.show_credentials(print_output=False)

    assert len(g.cert) == 2
    assert g.auth_type == 'x509'
    assert creds.get('cert_file') == cert_file
    assert creds.get('key_file') == key_file


def test_x509_credentials_lookup():
    """Test lookup of X509 credentials"""
    # Setup
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    # Initialize client
    find_x509_func = 'ligo.gracedb.client.GraceDBClient._get_x509_credentials'
    with mock.patch(find_x509_func) as mock_find_x509:  # noqa: E127
        mock_find_x509.return_value = (cert_file, key_file)
        g = GraceDb()

    # the 'auth_type' variable doesn't get set in this case, but it's
    # sort of fictitious when self.cert is being mocked.
    assert len(g.cert) == 2


def test_x509_lookup_cert_key_from_envvars():
    """Test lookup of X509 cert and key from environment variables"""
    # Setup
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    # Initialize client
    fake_creds_dict = {
        'X509_USER_CERT': cert_file,
        'X509_USER_KEY': key_file,
    }
    os_environ_func = 'os.environ'
    with mock.patch.dict(os_environ_func, fake_creds_dict):  # noqa: E127
        g = GraceDb()

    # Check credentials - should prioritze x509 credentials
    creds = g.show_credentials(print_output=False)

    assert len(g.cert) == 2
    assert g.auth_type == 'x509'
    assert creds.get('cert_file') == cert_file
    assert creds.get('key_file') == key_file


def test_x509_lookup_proxy_from_envvars():
    """Test lookup of X509 combined provxy file from environment variables"""
    # Setup
    proxy_file = '/tmp/proxy_file'

    # Initialize client
    os_environ_func = 'os.environ'
    mock_environ_dict = {'X509_USER_PROXY': proxy_file}
    with mock.patch.dict(os_environ_func, mock_environ_dict):  # noqa: E127
        g = GraceDb()

    # Check credentials - should prioritze x509 credentials
    creds = g.show_credentials(print_output=False)

    assert type(g.cert) == str
    assert g.auth_type == 'x509'
    assert creds.get('cert_file') == proxy_file
    assert creds.get('key_file') == proxy_file


def test_basic_credentials_lookup():
    """Test client instantiation - look up basic auth creds from .netrc file"""
    # Set up credentials and mock_netrc return
    fake_creds = {
        'machine': 'fake.com',
        'login': 'fake_user',
        'password': 'fake_password',
    }
    netrc = 'ligo.gracedb.client.netrc'
    find_x509_func = 'ligo.gracedb.client.GraceDBClient._get_x509_credentials'
    with mock.patch(find_x509_func) as mock_find_x509, \
         mock.patch(netrc) as mock_netrc:  # noqa: E127

        # Force lookup to not find any X509 credentials
        mock_find_x509.return_value = None
        # Mock return value from netrc lookup
        mock_netrc().authenticators.return_value = (
            fake_creds['login'], None, fake_creds['password'])

        # Initialize client
        g = GraceDb('https://{0}/api/'.format(fake_creds['machine']))

        # Check credentials
        creds = g.show_credentials(print_output=False)

        assert len(g.auth) == 2
        assert g.auth_type == 'basic'
        assert creds.get('username') == fake_creds.get('login')
        assert creds.get('password') == fake_creds.get('password')


@pytest.mark.parametrize("fail_if_noauth", [True, False])
def test_no_credentials(fail_if_noauth):
    """Test client instantiation with no credentials at all"""
    find_x509_func = 'ligo.gracedb.client.GraceDBClient._get_x509_credentials'
    netrc = 'ligo.gracedb.client.netrc'
    with mock.patch(find_x509_func) as mock_find_x509, \
         mock.patch(netrc) as mock_netrc:  # noqa: E127

        # Force lookup to not find any X509 credentials
        mock_find_x509.return_value = None
        # Mock return value from netrc lookup
        mock_netrc().authenticators.return_value = None

        # Initialize client
        if fail_if_noauth:
            err_str = 'No authentication credentials could be found'
            with pytest.raises(RuntimeError, match=err_str):
                g = GraceDb(fail_if_noauth=fail_if_noauth)
        else:
            if sys.version_info[0] > 2:
                warn_str = 'Authentication credentials not found, proceeding'
                with pytest.warns(UserWarning, match=warn_str):
                    g = GraceDb(fail_if_noauth=fail_if_noauth)
            else:
                g = GraceDb(fail_if_noauth=fail_if_noauth)

            # Check credentials
            assert g.auth_type is None


def test_force_noauth():
    """Test forcing no authentication, even with X509 certs available"""
    # Setup
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    # Initialize client
    environ_dict = 'os.environ'
    mock_environ_dict = {
        'X509_USER_CERT': cert_file,
        'X509_USER_KEY': key_file,
    }
    with mock.patch.dict(environ_dict, mock_environ_dict):  # noqa: E127

        # Initialize client
        g = GraceDb(force_noauth=True)

    # Check credentials
    assert g.auth_type is None


@pytest.mark.parametrize("creds_found", [True, False])
def test_fail_if_noauth(creds_found):
    """Test failing if no authentication credentials are provided"""
    cert_file = '/tmp/cert_file'
    key_file = '/tmp/key_file'

    # Initialize client
    find_x509_func = 'ligo.gracedb.client.GraceDBClient._get_x509_credentials'
    netrc = 'ligo.gracedb.client.netrc'
    with mock.patch(find_x509_func) as mock_find_x509, \
         mock.patch(netrc) as mock_netrc:  # noqa: E127

        if not creds_found:
            # Force lookup to not find any X509 credentials
            mock_find_x509.return_value = None
            # Mock return value from netrc lookup
            mock_netrc().authenticators.return_value = None

            # Initialize client
            err_str = 'No authentication credentials could be found'
            with pytest.raises(RuntimeError, match=err_str):
                g = GraceDb(fail_if_noauth=True)
        else:
            # Initialize client:
            mock_find_x509.return_value = (cert_file, key_file)
            g = GraceDb(cred=(cert_file, key_file), fail_if_noauth=True)

            # Check credentials
            assert len(g.cert) == 2


def test_force_noauth_and_fail_if_noauth():
    # Initialize client
    err_str = ('You have provided conflicting parameters to the client '
               'constructor: fail_if_noauth=True and force_noauth=True.')
    with pytest.raises(ValueError, match=err_str):
        GraceDb(force_noauth=True, fail_if_noauth=True)


@pytest.mark.parametrize(
    "resource,key",
    [
        ('api_versions', 'api-versions'),
        ('server_version', 'server-version'),
        ('links', 'links'),
        ('templates', 'templates'),
        ('groups', 'groups'),
        ('pipelines', 'pipelines'),
        ('searches', 'searches'),
        ('allowed_labels', 'labels'),
        ('superevent_categories', 'superevent-categories'),
        ('em_groups', 'em-groups'),
        ('voevent_types', 'voevent-types'),
        ('signoff_types', 'signoff-types'),
        ('signoff_statuses', 'signoff-statuses'),
        ('instruments', 'instruments'),
    ]
)
def test_properties_from_api_root(safe_client, resource, key):
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    with mock.patch(si_prop, new_callable=mock.PropertyMock()) as mock_si:
        getattr(safe_client, resource)

    call_args, call_kwargs = mock_si.get.call_args
    assert mock_si.get.call_count == 1
    assert len(call_args) == 1
    assert call_kwargs == {}
    assert call_args[0] == key


@pytest.mark.parametrize("api_version", [1, 1.2, [], (), {}])
def test_bad_api_version(api_version):
    err_msg = 'api_version should be a string'
    with pytest.raises(TypeError, match=err_msg):
        GraceDb(api_version=api_version)


@pytest.mark.parametrize(
    "service_url,api_version",
    [
        ('test', None),
        ('test/', None),
        ('test', 'v1'),
        ('test/', 'v2'),
        ('test/', 'default'),
    ],
)
def test_set_service_url(safe_client, service_url, api_version):
    safe_client._set_service_url(service_url, api_version)

    # Construct expected service urls
    expected_service_url = service_url.rstrip('/') + '/'
    expected_versioned_service_url = expected_service_url

    if api_version and api_version != 'default':
        expected_versioned_service_url += api_version + '/'

    assert safe_client._service_url == expected_service_url
    assert safe_client._versioned_service_url == expected_versioned_service_url
