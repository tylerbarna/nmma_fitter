import re
import pytest
import six
try:
    from unittest import mock
except ImportError:
    import mock

# Add module-level mark
pytestmark = pytest.mark.cli


def test_cli_subcommands_content(expected_subcommands, CLI):
    """Ensure that subcommands for main CLI are what we expect"""

    # Check content
    subcommand_names = [sc.name for sc in CLI.subcommands if not sc.legacy]
    assert sorted(subcommand_names) == sorted(expected_subcommands)


def test_cli_bad_subcommand(CLI, capsys):
    """Test handling of bad subcommand input to CLI"""
    cmd = 'fake_subcommand'
    with pytest.raises(SystemExit) as excinfo:
        CLI([cmd])

    # Check exit code
    assert excinfo.value.code == 1

    # Get output
    stdout = capsys.readouterr().out
    assert "{cmd}' not found".format(cmd=cmd) in stdout


def test_cli_help(CLI):
    """Test CLI help functionality"""
    print_help_func_str = \
        'ligo.gracedb.cli.parsers.CustomHelpArgumentParser.print_help'
    with mock.patch(print_help_func_str) as mock_print_help:
        with pytest.raises(SystemExit) as excinfo:
            CLI(['--help'])

    # Make sure print_help is called once
    assert mock_print_help.call_count == 1

    # Check exit code
    assert excinfo.value.code == 0


def test_cli_help_content(CLI, expected_subcommands, capsys):
    """Check CLI help content"""
    with pytest.raises(SystemExit) as excinfo:
        CLI(['--help'])

    # Check exit code
    assert excinfo.value.code == 0

    # Get content of help message
    stdout = capsys.readouterr().out

    # Verify entry for each command
    cmd_entry_regex = r'\s+{cmd}\s+'
    available_commands = stdout[stdout.index('Available commands'):]
    for cmd in expected_subcommands:
        assert re.search(cmd_entry_regex.format(cmd=cmd), available_commands)


def test_cli_client_setup(CLI):
    """Test translation of CLI arguments into client instantiation"""
    arg_dict = {
        'service-url': 'testserver.com',
        'proxy': 'testproxy.com:123',
        'username': 'user',
        'password': 'passw0rd',
        'creds': 'cert_file,key_file',
    }
    args = ['--{k}={v}'.format(k=k, v=v) for k, v in six.iteritems(arg_dict)]

    client_class = 'ligo.gracedb.cli.client.CommandLineClient'
    with mock.patch(client_class) as mock_client:
        cli_args, cmd_args = CLI.parser.parse_known_args(args)
        CLI.set_up_client(cli_args)

    # Check call count
    assert mock_client.call_count == 1

    # Check args used to initialize client
    cli_args, cli_kwargs = mock_client.call_args
    assert cli_args == ()
    assert cli_kwargs['service_url'] == arg_dict['service-url']
    assert cli_kwargs['username'] == arg_dict['username']
    assert cli_kwargs['password'] == arg_dict['password']
    assert cli_kwargs['cred'] == arg_dict['creds'].split(',')
