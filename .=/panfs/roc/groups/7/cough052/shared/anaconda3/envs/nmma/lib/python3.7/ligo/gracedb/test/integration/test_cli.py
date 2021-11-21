import datetime
import os
import pytest
import shlex

from ligo.gracedb.cli.client import CommandLineInterface
from ligo.gracedb.exceptions import HTTPError

# Apply module-level marks
pytestmark = [pytest.mark.cli, pytest.mark.integration]


# Instantiated client for use with tests
CLI = CommandLineInterface()

# Get test service URL and data directory
TEST_SERVICE = os.environ.get(
    'TEST_SERVICE',
    'https://gracedb-test.ligo.org/api/'
)
TEST_DATA_DIR = os.environ.get(
    'TEST_DATA_DIR',
    os.path.join(os.path.dirname(__file__), 'data')
)


# Utility function for running command with CLI and specifying the test service
def run_CLI_test(cmd):
    cmd += ' --service-url={url}'.format(url=TEST_SERVICE)
    return CLI(shlex.split(cmd))


###############################################################################
# Tests #######################################################################
###############################################################################
# Order of tests matters to some extent - we test operations first which are
# used to set up later operations. (Ex: we test creating a event before we
# use event creation in the test for getting an event)
def test_create_event():
    """Test creating an event with the command-line interface"""
    # Set up command
    cmd = 'create event Test gstlal {event_file} --labels=INJ,DQV --offline' \
        .format(event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))

    # Make request and get response
    response = run_CLI_test(cmd)
    out = response.json()

    # Check output
    assert response.status_code == 201
    assert out['group'] == 'Test'
    assert out['pipeline'] == 'gstlal'
    assert out['search'] is None
    assert sorted(out['labels']) == ['DQV', 'INJ']
    assert out['offline'] is True


def test_get_event():
    """Test getting an event with the command-line interface"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} LowMass '.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    gid = response.json()['graceid']

    # Get event
    cmd = 'get event {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check data
    assert response.status_code == 200
    assert out['group'] == 'Test'
    assert out['pipeline'] == 'gstlal'
    assert out['search'] == 'LowMass'
    assert sorted(out['labels']) == []
    assert out['offline'] is False


def test_update_event():
    """Test updating an event with the CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} LowMass '.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    out = response.json()
    gid = out['graceid']

    # Update event
    filename = os.path.join(TEST_DATA_DIR, 'cbc-lm2.xml')
    cmd = 'update event {gid} {filename}'.format(gid=gid, filename=filename)
    response = run_CLI_test(cmd)

    # Check response
    assert response.status_code == 202

    # Replace event response is useless so we get the event and check it
    cmd = 'get event {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out3 = response.json()

    # Check data
    assert response.status_code == 200
    assert out3['graceid'] == out['graceid']
    assert out3['gpstime'] != out['gpstime']  # gpstime should have changed


def test_search_events():
    """Test searching for events with the CLI"""
    # Setup: create an event
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    out = response.json()
    gid = out['graceid']

    # Search events -----------------------------------------------------------
    cmd = 'search events {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)

    # Check response (tab delimited)
    lines = response.split('\n')
    content = lines[1].split('\t')
    assert len(lines) == 2  # 1 header, 1 actual content
    assert content[0] == gid
    assert content[1] == ''  # labels
    assert content[2] == out['group']
    assert content[3] == out['pipeline']
    assert content[4] == str(out['far'])
    assert content[5] == str(out['gpstime'])
    assert content[6] == out['created']


def test_labels():
    """Test all things label related with the CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} LowMass '.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    gid = response.json()['graceid']

    # Add a label -------------------------------------------------------------
    label = 'PE_READY'
    cmd = 'add label {gid} {label}'.format(gid=gid, label=label)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 201

    # Get event and check
    cmd = 'get event {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 200
    assert out['labels'] == [label]

    # Get label ---------------------------------------------------------------
    cmd = 'get label {gid} {label}'.format(gid=gid, label=label)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert out['name'] == label

    # List labels -------------------------------------------------------------
    cmd = 'list labels {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert len(out['labels']) == 1
    assert out['labels'][0]['name'] == label

    # Remove label ------------------------------------------------------------
    cmd = 'remove label {gid} {label}'.format(gid=gid, label=label)
    response = run_CLI_test(cmd)

    # Check response
    assert response.status_code == 204

    # Get event and check
    cmd = 'get event {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 200
    assert out['labels'] == []


def test_logs_files():
    """Test all things log and file related with CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} LowMass '.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    gid = response.json()['graceid']

    # Create a log message with a file ----------------------------------------
    comment = "test comment"
    fname = 'test_file.txt'
    filename = os.path.join(TEST_DATA_DIR, fname)
    tags = ['tag1', 'tag2']
    cmd = 'create log {gid} "{comment}" {filename} --tag-name={tags}'.format(
        gid=gid, comment=comment, filename=filename, tags=",".join(tags))
    response = run_CLI_test(cmd)
    out = response.json()

    # Test output
    assert response.status_code == 201
    assert out['comment'] == out['comment']
    assert out['filename'] == os.path.basename(filename)
    assert sorted(out['tag_names']) == sorted(tags)

    # Get log -----------------------------------------------------------------
    cmd = 'get log {gid} {N}'.format(gid=gid, N=out['N'])
    response = run_CLI_test(cmd)
    out = response.json()

    # Test output
    assert response.status_code == 200
    assert out['comment'] == out['comment']
    assert out['filename'] == fname
    assert sorted(out['tag_names']) == sorted(tags)

    # List logs ---------------------------------------------------------------
    cmd = 'list logs {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Test output
    assert response.status_code == 200
    comments = [l['comment'] for l in out['log']]
    assert comment in comments

    # Get file ----------------------------------------------------------------
    cmd = 'get file {gid} {filename}'.format(gid=gid, filename=fname)
    response = run_CLI_test(cmd)
    with open(filename, 'rb') as fh:
        assert response == fh.read()

    # List files -------------------------------------------------------------
    cmd = 'list files {gid}'.format(gid=gid, filename=fname)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 200
    assert len(out) >= 2
    assert fname in out
    assert fname + ',0' in out


def test_tags():
    """Test all things tag-related with the CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} LowMass '.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    gid = response.json()['graceid']

    # Setup: create a log message
    comment = "test comment"
    filename = os.path.join(TEST_DATA_DIR, 'test_file.txt')
    tags = ['tag1', 'tag2']
    cmd = 'create log {gid} "{comment}" {filename} --tag-name={tags}'.format(
        gid=gid, comment=comment, filename=filename, tags=",".join(tags))
    out = run_CLI_test(cmd).json()
    log_N = out['N']
    assert response.status_code == 201
    assert out['comment'] == out['comment']
    assert out['filename'] == os.path.basename(filename)
    assert sorted(out['tag_names']) == sorted(tags)

    # Add tag to log ----------------------------------------------------------
    tag = 'tag3'
    cmd = 'add tag {gid} {N} {tag}'.format(gid=gid, N=log_N, tag=tag)
    response = run_CLI_test(cmd)
    assert response.status_code == 201

    # Tag response for events is not helpful. So we have to get the full log
    cmd = 'get log {gid} {N}'.format(gid=gid, N=log_N)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check output
    assert response.status_code == 200
    assert sorted(out['tag_names']) == sorted(tags + [tag])

    # List tags ---------------------------------------------------------------
    cmd = 'list tags {gid} {N}'.format(gid=gid, N=log_N)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert len(out['tags']) == 3
    tags_list = [t['name'] for t in out['tags']]
    assert sorted(tags_list) == sorted(tags + [tag])

    # Remove tag from log -----------------------------------------------------
    cmd = 'remove tag {gid} {N} {tag}'.format(gid=gid, N=log_N, tag=tag)
    response = run_CLI_test(cmd)
    assert response.status_code == 204

    # Tag response for events is not helpful. So we have to get the full log
    cmd = 'get log {gid} {N}'.format(gid=gid, N=log_N)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check output
    assert response.status_code == 200
    assert sorted(out['tag_names']) == sorted(tags)
    assert tag not in out['tag_names']


def test_create_superevent():
    """Test creating a superevent with the command-line interface"""
    # Setup: create two events
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response1 = run_CLI_test(cmd)
    gid1 = response1.json()['graceid']
    response2 = run_CLI_test(cmd)
    gid2 = response2.json()['graceid']

    # Create superevent
    cmd = ('create superevent 1 2 3 {p_ev} --labels=INJ,EM_READY '
           '--category=Test --events={ev}').format(p_ev=gid1, ev=gid2)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response content
    assert response.status_code == 201
    assert out['category'] == 'Test'
    assert sorted(out['gw_events']) == sorted([gid1, gid2])
    assert sorted(out['labels']) == ['EM_READY', 'INJ']
    assert out['preferred_event'] == gid1
    assert out['t_start'] == 1
    assert out['t_0'] == 2
    assert out['t_end'] == 3
    assert out['em_events'] == []


def test_get_superevent():
    """Test getting a superevent with the command-line interface"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    gid = response.json()['graceid']

    # Setup: create superevent
    cmd = 'create superevent 1 2 3 {p_ev} --category=Test '.format(p_ev=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    sid = out['superevent_id']

    # Get superevent
    cmd = 'get superevent {sid}'.format(sid=sid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert out['preferred_event'] == gid
    assert out['gw_events'] == [gid]
    assert out['em_events'] == []
    assert out['category'] == 'Test'
    assert out['t_start'] == 1
    assert out['t_0'] == 2
    assert out['t_end'] == 3


def test_add_event_to_superevent():
    """Test adding an event to a superevent with the command-line interface"""
    # Setup: create two events
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response1 = run_CLI_test(cmd)
    gid1 = response1.json()['graceid']
    response2 = run_CLI_test(cmd)
    gid2 = response2.json()['graceid']

    # Setup: create superevent with event 1
    cmd = 'create superevent 1 2 3 {p_ev} --category=Test '.format(p_ev=gid1)
    response = run_CLI_test(cmd)
    out = response.json()
    sid = out['superevent_id']

    # Check contents
    assert response.status_code == 201
    assert out['category'] == 'Test'
    assert out['preferred_event'] == gid1
    assert out['gw_events'] == [gid1]

    # Add event 2 to superevent
    cmd = 'add event {sid} {gid}'.format(sid=sid, gid=gid2)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert out['graceid'] == gid2

    # Get superevent and check more details
    cmd = 'get superevent {sid}'.format(sid=sid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert sorted(out['gw_events']) == sorted([gid1, gid2])
    assert out['preferred_event'] == gid1


def test_remove_event_from_superevent():
    """Test adding an event to a superevent with the command-line interface"""
    # Setup: create two events
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response1 = run_CLI_test(cmd)
    gid1 = response1.json()['graceid']
    response2 = run_CLI_test(cmd)
    gid2 = response2.json()['graceid']

    # Setup: create superevent with both events
    cmd = ('create superevent 1 2 3 {p_ev} --category=Test --events={ev}') \
        .format(p_ev=gid1, ev=gid2)
    response = run_CLI_test(cmd)
    out = response.json()
    sid = out['superevent_id']

    # Check contents
    assert response.status_code == 201
    assert out['category'] == 'Test'
    assert out['preferred_event'] == gid1
    assert sorted(out['gw_events']) == sorted([gid1, gid2])

    # Remove event 2 from superevent
    cmd = 'remove event {sid} {gid}'.format(sid=sid, gid=gid2)
    response = run_CLI_test(cmd)

    # Check response
    assert response.status_code == 204

    # Get superevent and make sure event 2 is not in it
    cmd = 'get superevent {sid}'.format(sid=sid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert out['gw_events'] == [gid1]
    assert out['preferred_event'] == gid1


def test_update_superevent():
    """Test update superevent with CLI"""
    # Setup: create two events
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response1 = run_CLI_test(cmd)
    assert response1.status_code == 201
    gid1 = response1.json()['graceid']
    response2 = run_CLI_test(cmd)
    assert response2.status_code == 201
    gid2 = response2.json()['graceid']

    # Setup: create superevent
    cmd = ('create superevent 1 2 3 {p_ev} --labels=INJ,EM_READY '
           '--category=Test').format(p_ev=gid1)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 201
    sid = out['superevent_id']

    # Update superevent -------------------------------------------------------
    cmd = ('update superevent {sid} --t-start=4 --t-0=5 --t-end=6 '
           '--preferred-event={gid}').format(sid=sid, gid=gid2)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert out['t_start'] == 4
    assert out['t_0'] == 5
    assert out['t_end'] == 6
    assert out['preferred_event'] == gid2
    assert sorted(out['gw_events']) == sorted([gid1, gid2])


def test_update_grbevent():
    """Test update GRB event with CLI"""
    # Setup: create a GRB event
    cmd = 'create event Test Fermi {event_file} GRB'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'fermi-test.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    initial_data = response.json()
    gid = initial_data['graceid']

    # Update the grbevent's parameters
    redshift = 3.4
    designation = 'very good'
    ra = 12.34
    cmd = ('update grbevent {gid} --redshift={rs} --designation="{des}" '
           '--ra={ra}').format(gid=gid, rs=redshift, des=designation,
                               ra=ra)
    try:
        response = run_CLI_test(cmd)
        new_data = response.json()

        # Even though they're test GRB events, unprivileged users
        # can't update GRB events. So try to catch a 200 status
        # in the case of an admin or grb user, and 403 otherwise.
        # This came up with setting up the gitlab integration instance.

        assert response.status_code == 200
        # Compare results
        initial_grb_params = initial_data['extra_attributes']['GRB']
        new_grb_params = new_data['extra_attributes']['GRB']
        assert new_grb_params['ra'] == ra
        assert new_grb_params['redshift'] == redshift
        assert new_grb_params['designation'] == designation
        assert new_grb_params['ra'] != initial_grb_params['ra']
        assert new_grb_params['redshift'] != initial_grb_params['redshift']

    except HTTPError as e:
        assert e.status_code == 403


def test_confirm_as_gw():
    """Test confirming a superevent as a GW with the command-line interface"""
    # Setup: create an event
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    gid = response.json()['graceid']

    # Setup: create superevent
    cmd = 'create superevent 1 2 3 {p_ev} --category=Test'.format(p_ev=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    sid = out['superevent_id']
    assert response.status_code == 201
    assert out['gw_id'] is None

    # Confirm as GW
    cmd = 'confirm_as_gw {sid}'.format(sid=sid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check output
    assert response.status_code == 200
    assert out['superevent_id'] == sid
    assert out['gw_id'] is not None
    assert out['gw_id'].startswith('TGW')


def test_search_superevents():
    """Test searching for superevents with the CLI"""
    # Setup: create an event
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    gid = response.json()['graceid']

    # Setup: create superevent
    cmd = ('create superevent 1 2 3 {p_ev} --labels=INJ,EM_READY '
           '--category=Test').format(p_ev=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 201
    sid = out['superevent_id']

    # Search superevents ------------------------------------------------------
    cmd = 'search superevents {sid}'.format(sid=sid)
    response = run_CLI_test(cmd)

    # Check response (tab delimited)
    lines = response.split('\n')
    content = lines[1].split('\t')
    assert len(lines) == 2  # 1 header, 1 actual content
    assert content[0] == sid
    assert content[1] == gid
    assert content[2] == gid
    assert sorted(content[3].split(',')) == sorted(out['labels'])
    assert content[4] == str(out['far'])
    assert content[5] == out['links']['files']


def test_permissions():
    """Test exposing and hiding a superevent with the CLI"""
    # Setup: create an event
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    gid = response.json()['graceid']

    # Setup: create superevent
    cmd = 'create superevent 1 2 3 {p_ev} --category=Test'.format(p_ev=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 201
    sid = out['superevent_id']

    # Expose superevent
    cmd = 'expose {sid}'.format(sid=sid)
    try:
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response-- this will be 200 for admins and
        # em_advocates, or 403 for everyone else, like th
        # gitlab runner.
        assert response.status_code == 200
        assert isinstance(out, list)
        assert len(out) == 3
    except HTTPError as e:
        assert e.status_code == 403

    # Hide superevent
    cmd = 'hide {sid}'.format(sid=sid)
    try:
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response-- same rules apply for exposing:
        # Note that unauthorized users will get the 403 response
        # at the permissions check even if the superevent is not
        # exposed. So if the previous test 200'ed, then in theory
        # this one will too if everything worked.
        assert response.status_code == 200
        assert isinstance(out, list)
        assert len(out) == 0
    except HTTPError as e:
        assert e.status_code == 403


def test_voevents():
    """Test all things related to VOEvents with the CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} --offline' \
        .format(event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    out = response.json()
    gid = out['graceid']

    # Setup: upload fake skymap
    filename = os.path.join(TEST_DATA_DIR, 'test_file.txt')
    cmd = 'create log {gid} "fake skymap" {filename}'.format(
        gid=gid, filename=filename)
    response = run_CLI_test(cmd)
    assert response.status_code == 201

    # Creation ----------------------------------------------------------------
    cmd = ('create voevent {gid} UP --skymap-filename={skymap} --hardware-inj '
           ' --skymap-type=update --prob-has-ns={pns} --bbh={bbh}').format(
        gid=gid, pns=0.1, bbh=0.3, skymap=os.path.basename(filename))
    response = run_CLI_test(cmd)
    out = response.json()
    voevent_N = out['N']

    # Check response
    assert response.status_code == 201
    assert out['N'] == voevent_N
    assert out['voevent_type'] == 'UP'

    # Get ---------------------------------------------------------------------
    cmd = 'get voevent {gid} {N}'.format(gid=gid, N=voevent_N)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert out['N'] == voevent_N
    assert out['voevent_type'] == 'UP'

    # List --------------------------------------------------------------------
    cmd = 'list voevents {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert len(out['voevents']) == 1
    assert out['voevents'][0]['N'] == voevent_N
    assert out['voevents'][0]['voevent_type'] == 'UP'


def test_emobservations():
    """Test all things related to EM observations with the CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file} --offline' \
        .format(event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    out = response.json()
    gid = out['graceid']

    # Creation ----------------------------------------------------------------
    now = datetime.datetime.now()
    group = 'AGILE'
    ra_list = [1, 2, 3, 4]
    ra_width = 0.1
    dec_width = 0.2
    duration = 10
    dec_list = [5, 6, 7, 8]
    start_time_list = list(
        map(lambda i: (now + datetime.timedelta(seconds=i)).isoformat(),
            [0, 1, 2, 3])
    )

    # Compile command
    def join_s(s):
        return ",".join([str(i) for i in s]) if isinstance(s, list) else s

    cmd = ('create emobservation {gid} {group} {ra_list} {ra_width_list} '
           '{dec_list} {dec_width_list} {start_time_list} {duration_list}') \
        .format(gid=gid, group=group, ra_list=join_s(ra_list),
                ra_width_list=join_s(ra_width), dec_list=join_s(dec_list),
                dec_width_list=join_s(dec_width),
                duration_list=join_s(duration),
                start_time_list=join_s(start_time_list))
    cmd += " --comment='fake comment'"
    response = run_CLI_test(cmd)
    print("yay1", response)
    out = response.json()
    print("yay2", out)
    print("yay3", type(out))
    emo_N = out['N']

    # Check response
    assert response.status_code == 201
    assert out['comment'] == 'fake comment'
    assert len(out['footprints']) == len(ra_list)
    assert out['group'] == group

    # Get ---------------------------------------------------------------------
    cmd = 'get emobservation {gid} {N}'.format(gid=gid, N=emo_N)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert out['N'] == emo_N
    assert out['comment'] == 'fake comment'
    assert len(out['footprints']) == len(ra_list)
    assert out['group'] == group

    # List --------------------------------------------------------------------
    cmd = 'list emobservations {gid}'.format(gid=gid)
    response = run_CLI_test(cmd)
    out = response.json()

    # Check response
    assert response.status_code == 200
    assert out['observations'][0]['N'] == emo_N
    assert out['observations'][0]['comment'] == 'fake comment'
    assert len(out['observations'][0]['footprints']) == len(ra_list)
    assert out['observations'][0]['group'] == group


def test_signoffs():
    """Test all things related to signoffs with the CLI"""
    # Setup: create event
    cmd = 'create event Test gstlal {event_file}'.format(
        event_file=os.path.join(TEST_DATA_DIR, 'cbc-lm.xml'))
    response = run_CLI_test(cmd)
    assert response.status_code == 201
    gid = response.json()['graceid']

    # Setup: create superevent
    cmd = ('create superevent 1 2 3 {p_ev} --labels=INJ,EM_READY '
           '--category=Test').format(p_ev=gid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 201
    sid = out['superevent_id']

    # Setup: apply ADVREQ label
    cmd = 'add label {sid} ADVREQ'.format(sid=sid)
    response = run_CLI_test(cmd)
    out = response.json()
    assert response.status_code == 201

    # Create signoff ----------------------------------------------------------
    cmd = 'create signoff {sid} ADV OK "looks good"'.format(sid=sid)
    try:
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response
        assert response.status_code == 201
        assert out['status'] == 'OK'
        assert out['comment'] == 'looks good'
        assert out['instrument'] == ''
        assert out['signoff_type'] == 'ADV'

        # Define this session as an authorized session. The rest of the tests
        # are sensible only if this one passes. This is admittedly something
        # that needs to be run offline by an admin unless i can think of a more
        # clever way of doing it.
        authorized_user = True

    except HTTPError as e:
        assert e.status_code == 403
        authorized_user = False

    if authorized_user:
        # Get signoff ------------------------------------------------------
        cmd = 'get signoff {sid} ADV'.format(sid=sid)
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response
        assert response.status_code == 200
        assert out['status'] == 'OK'
        assert out['comment'] == 'looks good'
        assert out['instrument'] == ''
        assert out['signoff_type'] == 'ADV'

        # List signoff -----------------------------------------------------
        cmd = 'list signoffs {sid}'.format(sid=sid)
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response
        assert response.status_code == 200
        assert len(out['signoffs']) == 1
        assert out['signoffs'][0]['status'] == 'OK'
        assert out['signoffs'][0]['comment'] == 'looks good'
        assert out['signoffs'][0]['instrument'] == ''
        assert out['signoffs'][0]['signoff_type'] == 'ADV'

        # Update signoff ---------------------------------------------------
        cmd = 'update signoff {sid} ADV --status=NO --comment="new"'.format(
            sid=sid)
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response
        assert response.status_code == 200
        assert out['status'] == 'NO'
        assert out['comment'] == 'new'
        assert out['instrument'] == ''
        assert out['signoff_type'] == 'ADV'

        # Delete signoff ---------------------------------------------------
        cmd = 'delete signoff {sid} ADV'.format(sid=sid)
        response = run_CLI_test(cmd)

        # Check response
        assert response.status_code == 204

        # List signoff again -----------------------------------------------
        cmd = 'list signoffs {sid}'.format(sid=sid)
        response = run_CLI_test(cmd)
        out = response.json()

        # Check response
        assert response.status_code == 200
        assert len(out['signoffs']) == 0


def test_ping():
    """Test ping with the CLI"""
    response = run_CLI_test('ping')
    assert response.startswith('Response from {0}'.format(TEST_SERVICE))
    assert response.endswith('200 OK')


def test_credentials():
    """Test getting credentials from server"""
    response = run_CLI_test('credentials server')
    assert response.status_code == 200


# Subcommands for testing 'info' command
CMDS = ['emgroups', 'groups', 'labels', 'pipelines', 'searches',
        'server_version', 'signoff_statuses', 'signoff_types',
        'superevent_categories', 'voevent_types']
@pytest.mark.parametrize("cmd", CMDS)  # noqa: E302
def test_info(cmd):
    """Test 'info' command with CLI"""
    response = run_CLI_test('info ' + cmd)

    # Can't really check content of response but we can make sure we got
    # something
    assert response != 'Data not found on server.'
