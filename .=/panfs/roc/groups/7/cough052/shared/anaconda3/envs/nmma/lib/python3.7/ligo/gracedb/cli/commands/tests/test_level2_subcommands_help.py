# Tests for level 2 subcommand help
#  Ex: 'gracedb add event'
import pytest
try:
    from unittest import mock
except ImportError:
    import mock

from .test_level1_commands import COMMANDS_TEST_DATA

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Test data ###################################################################
###############################################################################
SUBCOMMANDS_TEST_DATA = [(t[0], sc) for t in COMMANDS_TEST_DATA for sc in t[1]]


###############################################################################
# Parametrized tests ##########################################################
###############################################################################
@pytest.mark.parametrize("cmd,subcommand", SUBCOMMANDS_TEST_DATA)
def test_subcommand_help(CLI, cmd, subcommand):
    """Test level 2 subcommand help functionality"""
    command_line_cmd = '{cmd} {sc} --help'.format(cmd=cmd, sc=subcommand)

    print_help_func_str = \
        'ligo.gracedb.cli.parsers.argparse.ArgumentParser.print_help'
    with mock.patch(print_help_func_str) as mock_print_help:
        with pytest.raises(SystemExit) as excinfo:
            CLI(command_line_cmd.split(' '))

    # Make sure print_help is called once
    assert mock_print_help.call_count == 1

    # Check exit code
    assert excinfo.value.code == 0


@pytest.mark.parametrize("cmd,subcommand", SUBCOMMANDS_TEST_DATA)
def test_subcommand_help_content(CLI, cmd, subcommand):
    """Check level 2 subcommand help content"""

    # Create an instance of the subcommand
    sc_instance = CLI.subcommand_dict[cmd](parent_prog=CLI.parser.prog)

    # Get help dialogue
    help_text = sc_instance.parser.format_help()

    # Check usage
    assert help_text.startswith('usage: {prog} {sc}'.format(
        prog=CLI.parser.prog, sc=cmd))

    # Check description - have to replace newlines with spaces since the
    # help text is specially formatted
    desc = getattr(sc_instance, 'long_description', sc_instance.description)
    assert desc.replace('\n', ' ') in help_text.replace('\n', ' ')
