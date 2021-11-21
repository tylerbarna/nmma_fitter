import json
import pytest
# import six
try:
    from unittest import mock
except ImportError:
    import mock

from ligo.gracedb.exceptions import HTTPError
from requests import Response

# Apply module-level mark
pytestmark = pytest.mark.cli


@pytest.mark.parametrize("output_type", ['json', 'status'])
def test_main_with_ok_response(main_tester, capsys, output_type):
    """Test CLI wrapper when response object is returned with good status"""

    CLI = 'ligo.gracedb.cli.client.CommandLineInterface'
    with mock.patch(CLI) as mock_CLI:

        # Set up response from CLI.__call__
        status = 200
        reason = 'because'
        response_mock = mock.MagicMock(
            spec=Response,
            status_code=status, reason=reason)
        mock_CLI().return_value = response_mock
        # Set up response.json()
        json_mock = mock.MagicMock()
        json_mock.return_value = {'test': 'ok'}
        # Use setattr since the MagicMock is autospecced
        setattr(response_mock, 'json', json_mock)

        # Set up CLI.args.output_type
        mock_CLI().args.output_type = output_type

        # Call function
        main_tester()

    # Get output
    stdout = capsys.readouterr().out

    # Test output
    if output_type == 'json':
        assert json.loads(stdout) == json_mock.return_value
    elif output_type == 'status':
        assert stdout.rstrip() == 'Server returned {status}: {reason}'.format(
            status=status, reason=reason)


MSG_DATA = ['short message', 'long' * 500]
@pytest.mark.parametrize("response_msg", MSG_DATA,  # noqa: E302
                         ids=['short', 'long'])
def test_main_with_bad_response(main_tester, capsys, response_msg):
    """Test CLI wrapper when response object is returned with status >= 400"""

    CLI = 'ligo.gracedb.cli.client.CommandLineInterface'
    with mock.patch(CLI) as mock_CLI:

        # Set up response from CLI.__call__
        status = 400
        reason = 'Bad Request'
        response_mock = mock.MagicMock(
            spec=Response,
            status_code=status, reason=reason,
            text=response_msg)
        mock_CLI().return_value = response_mock

        # Set up CLI.args.output_type
        mock_CLI().args.output_type = 'json'

        # Call function
        with pytest.raises(SystemExit) as excinfo:
            main_tester()

    # Make sure exit code is correct
    assert excinfo.value.code == 1

    # Get output
    stdout = capsys.readouterr().out

    # Test output
    if len(response_msg) < 1000:
        assert stdout.rstrip() == '{code} {reason}: {msg}'.format(
            code=status, reason=reason, msg=response_msg)
    else:
        assert stdout.rstrip() == '{code} {reason}'.format(
            code=status, reason=reason)


# Define an error response object:
err_response = Response()
err_response.status_code = 400
err_response.reason = 'Bad Request'
err_response._content = b'test'
EXCEPTION_DATA = [Exception('test'),
                  HTTPError(response=err_response)]


@pytest.mark.parametrize("exc", EXCEPTION_DATA)  # noqa: E302
def test_main_with_exception_in_CLI_call(main_tester, capsys, exc):
    """Test CLI wrapper when CLI call raises exception"""

    CLI = 'ligo.gracedb.cli.client.CommandLineInterface'
    with mock.patch(CLI) as mock_CLI:
        # Set up response from CLI.__call__
        mock_CLI().side_effect = exc

        # Call function
        with pytest.raises(SystemExit) as excinfo:
            main_tester()

    # Make sure exit code is correct
    assert excinfo.value.code == 1

    # Get output
    stdout = capsys.readouterr().out

    # Test output
    if isinstance(exc, HTTPError):
        assert stdout.rstrip() == 'Error: {code} {reason}. {text}.'.format(
            code=exc.status_code, reason=exc.reason, text=exc.text)
    elif isinstance(exc, Exception):
        assert stdout.rstrip() == 'Error: {msg}'.format(msg=str(exc))


def test_main_with_exception_in_response_json(main_tester, capsys):
    """Test CLI wrapper when response.json() raises exception"""

    CLI = 'ligo.gracedb.cli.client.CommandLineInterface'
    with mock.patch(CLI) as mock_CLI:
        # Set up response from CLI.__call__
        status = 200
        reason = 'OK'
        response_mock = mock.MagicMock(
            spec=Response,
            status_code=status, reason=reason)
        mock_CLI().return_value = response_mock
        # Set up response.read()
        exc_msg = 'uh oh'
        json_mock = mock.MagicMock()
        json_mock.side_effect = Exception(exc_msg)
        # Use setattr since the MagicMock is autospecced
        setattr(response_mock, 'json', json_mock)

        # Set up CLI.args.output_type
        mock_CLI().args.output_type = 'json'

        # Call function
        with pytest.raises(SystemExit) as excinfo:
            main_tester()

    # Make sure exit code is correct
    assert excinfo.value.code == 1

    # Get output
    stdout = capsys.readouterr().out

    # Test output
    assert stdout.rstrip() == exc_msg


def test_main_with_str_response(main_tester, capsys):
    """Test CLI wrapper with string response"""

    CLI = 'ligo.gracedb.cli.client.CommandLineInterface'
    with mock.patch(CLI) as mock_CLI:
        # Set up response from CLI.__call__
        str_response = 'this is a string response'
        mock_CLI().return_value = str_response

        # Call function
        main_tester()

    # Get output
    stdout = capsys.readouterr().out

    # Test output
    assert stdout.rstrip() == str_response


def test_main_with_unexpected_response_type(main_tester, capsys):
    """Test CLI wrapper with unexpected response type"""

    CLI = 'ligo.gracedb.cli.client.CommandLineInterface'
    with mock.patch(CLI) as mock_CLI:
        # Set up response from CLI.__call__
        response = float(1.2345)
        mock_CLI().return_value = response

        # Call function
        with pytest.raises(SystemExit) as excinfo:
            main_tester()

    # Make sure exit code is correct
    assert excinfo.value.code == 1

    # Get output
    stdout = capsys.readouterr().out

    # Test output
    expected = "Unexpected response type {tp}\nResponse: {resp}".format(
        tp=type(response), resp=str(response))
    assert stdout.rstrip() == expected
