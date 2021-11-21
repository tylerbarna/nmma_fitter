# Tests for subcommands below 'add'
#  Ex: 'gracedb add event'
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
def test_add_event_subcommand(CLI):
    """Test add event subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'g_id': 'G1234',
    }
    cmd = 'add event {s_id} {g_id}'.format(**cmd_args)

    func = 'ligo.gracedb.rest.GraceDb.addEventToSuperevent'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['g_id'],)
    assert cli_kwargs == {}


def test_add_label_subcommand(CLI):
    """Test add label subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'label': 'FAKE_LABEL',
    }
    cmd = 'add label {s_id} {label}'.format(**cmd_args)

    func = 'ligo.gracedb.rest.GraceDb.writeLabel'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['label'],)
    assert cli_kwargs == {}


TAG_DISPLAY_NAMES = [None, 'test_display_name']
@pytest.mark.parametrize("display_name", TAG_DISPLAY_NAMES)  # noqa: E302
def test_add_tag_subcommand(CLI, display_name):
    """Test add tag subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'log_N': 12,
        'tag_name': 'FAKE_TAG',
    }
    cmd = 'add tag {s_id} {log_N} {tag_name}'.format(**cmd_args)
    if display_name is not None:
        cmd += ' --tag-display-name={dn}'.format(dn=display_name)

    func = 'ligo.gracedb.rest.GraceDb.addTag'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['log_N'],)
    assert cli_kwargs == {'tag_name': cmd_args['tag_name'],
                          'displayName': display_name}
