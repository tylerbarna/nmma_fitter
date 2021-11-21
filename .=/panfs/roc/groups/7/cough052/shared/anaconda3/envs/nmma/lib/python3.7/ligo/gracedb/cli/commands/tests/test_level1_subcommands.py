# Tests for intermediate commands
#  Ex: 'gracedb confirm_as_gw' because it has no subcommands.
#  NOT 'gracedb add' because it has subcommands like 'gracedb add event'
import pytest
import six
try:
    from unittest import mock
except ImportError:
    import mock

from ligo.gracedb.cli.commands.subcommands import InfoCommand

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Test data ###################################################################
###############################################################################
SUBCOMMANDS_TEST_DATA = [
    "confirm_as_gw", "credentials", "expose", "hide", "info", "ping"
]


###############################################################################
# Parametrized tests ##########################################################
###############################################################################
@pytest.mark.parametrize("cmd", SUBCOMMANDS_TEST_DATA)
def test_subcommand_help(CLI, cmd):
    """Test level 1 subcommand help functionality"""
    command_line_cmd = '{cmd} --help'.format(cmd=cmd)
    print_help_func_str = \
        'ligo.gracedb.cli.parsers.argparse.ArgumentParser.print_help'
    with mock.patch(print_help_func_str) as mock_print_help:
        with pytest.raises(SystemExit) as excinfo:
            CLI(command_line_cmd.split(' '))

    # Make sure print_help is called once
    assert mock_print_help.call_count == 1

    # Check exit code
    assert excinfo.value.code == 0


@pytest.mark.parametrize("cmd", SUBCOMMANDS_TEST_DATA)
def test_subcommand_help_content(CLI, cmd):
    """Check level 1 subcommand help content"""

    # Create an instance of the subcommand
    sc_instance = CLI.subcommand_dict[cmd](parent_prog=CLI.parser.prog)

    # Get help dialogue
    help_text = sc_instance.parser.format_help()

    # Check usage
    assert help_text.startswith('usage: {prog} {sc}'.format(
        prog=CLI.parser.prog, sc=cmd))


###############################################################################
# Tests of individual subcommands #############################################
###############################################################################
def test_confirm_as_gw_subcommand(CLI):
    """Test confirm_as_gw subcommand"""
    s_id = 'S001122a'

    func = 'ligo.gracedb.rest.GraceDb.confirm_superevent_as_gw'
    with mock.patch(func) as mock_cli_func:
        CLI(['confirm_as_gw', s_id])

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id,)
    assert cli_kwargs == {}


CREDENTIALS_TEST_DATA = [
    ('client', 'show_credentials', {'print_output': False}),
    ('server', 'get_user_info', {}),
]
@pytest.mark.parametrize("cmd,cli_func,kw",  # noqa: E302
                         CREDENTIALS_TEST_DATA)
def test_credentials_subcommand(CLI, cmd, cli_func, kw):
    """Test credentials subcommand"""
    func = 'ligo.gracedb.rest.GraceDb.{0}'.format(cli_func)
    with mock.patch(func) as mock_cli_func:
        CLI(['credentials', cmd])

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == ()
    assert cli_kwargs == kw


def test_expose_subcommand(CLI):
    """Test expose subcommand"""
    s_id = 'S001122a'

    func = 'ligo.gracedb.rest.GraceDb.modify_permissions'
    with mock.patch(func) as mock_cli_func:
        CLI(['expose', s_id])

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id, 'expose')
    assert cli_kwargs == {}


def test_hide_subcommand(CLI):
    """Test hide subcommand"""
    s_id = 'S001122a'

    func = 'ligo.gracedb.rest.GraceDb.modify_permissions'
    with mock.patch(func) as mock_cli_func:
        CLI(['hide', s_id])

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id, 'hide')
    assert cli_kwargs == {}


def test_ping_subcommand(CLI):
    """Test ping subcommand"""
    func = 'ligo.gracedb.rest.GraceDb.ping'
    with mock.patch(func) as mock_cli_func:
        mock_cli_func.return_value = mock.MagicMock(status_code=123)
        output = CLI(['ping'])

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == ()
    assert cli_kwargs == {}

    # Check output
    assert output == 'Response from {server}: {status}'.format(
        server=CLI.client._service_url, status=mock_cli_func().status_code)


@pytest.mark.parametrize(
    "cmd,cli_func",
    list(six.iteritems(InfoCommand.options))
)
def test_info_subcommand(CLI, cmd, cli_func):
    """Test info subcommand"""

    func = 'ligo.gracedb.rest.GraceDb.{func}'.format(func=cli_func)
    with mock.patch(func, new_callable=mock.PropertyMock) as mock_cli_func:
        mock_cli_func.return_value = ['a', 'b', 'c', 'd']
        output = CLI(['info', cmd])

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == ()
    assert cli_kwargs == {}

    # Check output
    assert output == ", ".join(mock_cli_func())
