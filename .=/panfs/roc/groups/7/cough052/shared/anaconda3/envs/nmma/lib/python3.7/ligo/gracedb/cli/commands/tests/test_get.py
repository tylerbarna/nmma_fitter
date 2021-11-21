# Tests for subcommands below 'get'
#  Ex: 'gracedb get superevent'
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
def test_get_emobservation_subcommand(CLI):
    """Test get emobservation subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'N': 14,
    }

    # Generate command
    cmd = 'get emobservation {s_id} {N}'.format(**cmd_args)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.emobservations'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'],)
    assert cli_kwargs == {'emobservation_num': cmd_args['N']}


def test_get_event_subcommand(CLI):
    """Test get event subcommand"""
    g_id = 'G1234'

    # Generate command
    cmd = 'get event {g_id}'.format(g_id=g_id)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.event'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (g_id,)
    assert cli_kwargs == {}


FILE_TEST_DATA = [None, 'test.txt', '/file/we/cannot/access.txt']
@pytest.mark.parametrize("dest", FILE_TEST_DATA)  # noqa: E302
def test_get_file_subcommand(CLI, dest):
    """Test get file subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'filename': 'fake_filename.txt',
    }

    # Generate command
    cmd = 'get file {s_id} {filename}'.format(**cmd_args)
    if dest is not None:
        cmd += ' {dest}'.format(dest=dest)

    func = 'ligo.gracedb.cli.client.CommandLineClient.files'
    with mock.patch(func) as mock_cli_func:
        if dest and 'cannot' in dest:
            # Last case should raise an IOError
            with pytest.raises(IOError):
                CLI(shlex.split(cmd))
            return
        else:
            CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['filename'],)
    assert cli_kwargs == {}


def test_get_label_subcommand(CLI):
    """Test get label subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'label_name': 'FAKE_LABEL',
    }

    # Generate command
    cmd = 'get label {s_id} {label_name}'.format(**cmd_args)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.labels'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'],)
    assert cli_kwargs == {'label': cmd_args['label_name']}


def test_get_log_subcommand(CLI):
    """Test get log subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'N': 12,
    }

    # Generate command
    cmd = 'get log {s_id} {N}'.format(**cmd_args)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.logs'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'],)
    assert cli_kwargs == {'log_number': cmd_args['N']}


SIGNOFF_TEST_DATA = [None, 'FAKE_INSTRUMENT']
@pytest.mark.parametrize("instrument", SIGNOFF_TEST_DATA)  # noqa: E302
def test_get_signoff_subcommand(CLI, instrument):
    """Test get signoff subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'signoff_type': 'FAKE_SIGNOFF_TYPE',
    }

    # Generate command
    cmd = 'get signoff {s_id} {signoff_type}'.format(**cmd_args)
    if instrument is not None:
        cmd += " {inst}".format(inst=instrument)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.signoffs'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'],)
    assert cli_kwargs == {'signoff_type': cmd_args['signoff_type'],
                          'instrument': instrument or ''}


def test_get_superevent_subcommand(CLI):
    """Test get superevent subcommand"""
    s_id = 'S001122a'

    # Generate command
    cmd = 'get superevent {s_id}'.format(s_id=s_id)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.superevent'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id,)
    assert cli_kwargs == {}


def test_get_voevent_subcommand(CLI):
    """Test get voevent subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'N': 12,
    }

    # Generate command
    cmd = 'get voevent {s_id} {N}'.format(**cmd_args)

    # Call command
    func = 'ligo.gracedb.rest.GraceDb.voevents'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'],)
    assert cli_kwargs == {'voevent_num': cmd_args['N']}
