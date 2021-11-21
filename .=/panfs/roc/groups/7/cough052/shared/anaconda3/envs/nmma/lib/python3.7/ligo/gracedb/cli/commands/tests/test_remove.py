# Tests for subcommands below 'remove'
#  Ex: 'gracedb remove event'
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
def test_remove_event_subcommand(CLI):
    """Test remove event subcommand"""
    s_id = 'S001122a'
    g_id = 'G123456'
    cmd = 'remove event {s_id} {g_id}'.format(s_id=s_id, g_id=g_id)

    func = 'ligo.gracedb.rest.GraceDb.removeEventFromSuperevent'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id, g_id,)
    assert cli_kwargs == {}


def test_remove_label_subcommand(CLI):
    """Test remove label subcommand"""
    s_id = 'S001122a'
    label_name = 'TEST_LABEL'
    cmd = 'remove label {s_id} {label}'.format(s_id=s_id, label=label_name)

    func = 'ligo.gracedb.rest.GraceDb.removeLabel'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id, label_name,)
    assert cli_kwargs == {}


def test_remove_tag_subcommand(CLI):
    """Test remove tag subcommand"""
    s_id = 'S001122a'
    log_N = 12
    tag_name = 'new_tag'
    cmd = 'remove tag {s_id} {N} {tag}'.format(
        s_id=s_id, N=log_N,
        tag=tag_name
    )

    func = 'ligo.gracedb.rest.GraceDb.removeTag'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id, log_N, tag_name,)
    assert cli_kwargs == {}
