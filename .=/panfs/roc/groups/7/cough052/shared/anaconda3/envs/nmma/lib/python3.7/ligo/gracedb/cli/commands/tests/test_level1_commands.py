# Tests for intermediate commands
#  Ex: 'gracedb add' because it has subcommands like 'gracedb add event'
#  NOT 'gracedb confirm_as_gw' because it has no subcommands.
import re
import pytest
try:
    from unittest import mock
except ImportError:
    import mock

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Test data ###################################################################
###############################################################################
COMMANDS_TEST_DATA = [
    ("add", ["event", "label", "tag"]),
    ("create", ["emobservation", "event", "log", "signoff", "superevent",
                "voevent"]),
    ("delete", ["signoff"]),
    ("get", ["emobservation", "event", "file", "label", "log", "signoff",
             "superevent", "voevent"]),
    ("list", ["emobservations", "files", "labels", "logs", "signoffs",
              "tags", "voevents"]),
    ("remove", ["event", "label", "tag"]),
    ("search", ["events", "superevents"]),
    ("update", ["event", "signoff", "superevent", "grbevent"]),
]


###############################################################################
# Tests #######################################################################
###############################################################################
@pytest.mark.parametrize("cmd, expected", COMMANDS_TEST_DATA)
def test_subcommands(CLI, cmd, expected):
    """
    Ensure that the subcommands for the specified level 1 command are
    as expected
    """
    cmd_instance = CLI.subcommand_dict[cmd]()

    assert sorted(list(cmd_instance.subcommand_dict)) == sorted(expected)


@pytest.mark.parametrize("cmd", [sc[0] for sc in COMMANDS_TEST_DATA])
def test_bad_subcommand(CLI, capsys, cmd):
    """Test handling of bad subcommand input to level 1 commands"""
    fake_sc = 'fake_subcommand'
    with pytest.raises(SystemExit) as excinfo:
        CLI([cmd, fake_sc])

    # Check exit code
    assert excinfo.value.code == 1

    # Get output
    stdout = capsys.readouterr().out
    assert "{cmd} {sc}' not found".format(cmd=cmd, sc=fake_sc) in stdout


@pytest.mark.parametrize("cmd", [sc[0] for sc in COMMANDS_TEST_DATA])
def test_command_help(CLI, cmd):
    """Test level 1 command help functionality"""
    print_help_func_str = \
        'ligo.gracedb.cli.parsers.CustomHelpArgumentParser.print_help'
    with mock.patch(print_help_func_str) as mock_print_help:
        with pytest.raises(SystemExit) as excinfo:
            CLI([cmd, '--help'])

    # Make sure print_help is called once
    assert mock_print_help.call_count == 1

    # Check exit code
    assert excinfo.value.code == 0


@pytest.mark.parametrize("cmd,expected", COMMANDS_TEST_DATA)
def test_command_help_content(CLI, capsys, cmd, expected):
    """Check level 1 command help content"""
    with pytest.raises(SystemExit) as excinfo:
        CLI([cmd, '--help'])

    # Check exit code
    assert excinfo.value.code == 0

    # Get content of help message
    stdout = capsys.readouterr().out

    # Verify entry for each command
    cmd_entry_regex = r'\s+{cmd}\s+'
    available_commands = stdout[stdout.index('Available commands'):]
    for cmd in expected:
        assert re.search(cmd_entry_regex.format(cmd=cmd), available_commands)
