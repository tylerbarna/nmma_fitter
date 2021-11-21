# Tests for subcommands below 'delete'
#  Ex: 'gracedb delete signoff'
import pytest
import shlex
try:
    from unittest import mock
except ImportError:
    import mock

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Tests of individual subcommands #############################################
###############################################################################
SIGNOFF_TEST_DATA = [None, 'FAKE_INSTRUMENT']
@pytest.mark.parametrize("instrument", SIGNOFF_TEST_DATA)  # noqa: E302
def test_delete_signoff_subcommand(CLI, instrument):
    """Test delete signoff subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'signoff_type': 'FAKE_SIGNOFF_TYPE',
    }

    # Generate command
    cmd = "delete signoff {s_id} {signoff_type}".format(**cmd_args)
    if instrument is not None:
        cmd += " {inst}".format(inst=instrument)

    func = 'ligo.gracedb.rest.GraceDb.delete_signoff'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['signoff_type'],)
    assert cli_kwargs == {'instrument': instrument or ''}
