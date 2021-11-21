# Tests for subcommands below 'list'
#  Ex: 'gracedb list labels'
import pytest
import shlex
try:
    from unittest import mock
except ImportError:
    import mock

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Parametrized tests ##########################################################
###############################################################################
# We can parametrize most of the tests because these commands are simple
TEST_DATA = [
    ('emobservations', None),
    ('files', None),
    ('labels', None),
    ('logs', None),
    ('signoffs', None),
    ('voevents', None),
]
@pytest.mark.parametrize("name,cli_func", TEST_DATA)  # noqa: E302
def test_list_subcommands(CLI, name, cli_func):
    """Test most of the list subcommands"""
    s_id = 'S001122a'

    # Generate command
    cmd = 'list {name} {s_id}'.format(name=name, s_id=s_id)

    # Set up client function
    if cli_func is None:
        cli_func = name
    func = 'ligo.gracedb.rest.GraceDb.{func}'.format(func=cli_func)
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id,)
    assert cli_kwargs == {}


###############################################################################
# Tests of individual subcommands #############################################
###############################################################################
def test_list_tags_subcommand(CLI):
    """Test list tags subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'N': 14,
    }

    # Generate command
    cmd = 'list tags {s_id} {N}'.format(**cmd_args)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.tags'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['N'],)
    assert cli_kwargs == {}
