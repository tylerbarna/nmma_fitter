# Tests for subcommands below 'create'
#  Ex: 'gracedb create emobservation'
import datetime
import pytest
import shlex
import six
try:
    from unittest import mock
except ImportError:
    import mock

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Tests of individual subcommands #############################################
###############################################################################
EMO_TEST_DATA = [
    ([0.1, 0.2, 0.9, 0.7], [0.1, 0.2, 0.04, 1.2], [1, 2, 3, 4], None),
    (0.2, 0.1, 2.2, "test comment"),
]
@pytest.mark.parametrize("ra_width,dec_width,duration,comment",  # noqa: E302
                         EMO_TEST_DATA)
def test_create_emobservation_subcommand(CLI, ra_width, dec_width, duration,
                                         comment):
    """Test create observation subcommand"""
    now = datetime.datetime.now()
    s_id = 'S001122a'
    group = 'FAKE_EMGROUP'
    ra_list = [1, 2, 3, 4]
    dec_list = [5, 6, 7, 8]
    start_time_list = list(
        map(lambda i: (now + datetime.timedelta(seconds=i)).isoformat(),
            [0, 1, 2, 3])
    )

    # Compile command
    def join_s(s):
        return ",".join([str(i) for i in s]) if isinstance(s, list) else s

    cmd = ('create emobservation {s_id} {group} {ra_list} {ra_width_list} '
           '{dec_list} {dec_width_list} {start_time_list} {duration_list}') \
        .format(s_id=s_id, group=group, ra_list=join_s(ra_list),
                ra_width_list=join_s(ra_width), dec_list=join_s(dec_list),
                dec_width_list=join_s(dec_width),
                duration_list=join_s(duration),
                start_time_list=join_s(start_time_list))
    if comment is not None:
        cmd += " --comment='{comment}'".format(comment=comment)

    func = 'ligo.gracedb.rest.GraceDb.writeEMObservation'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (s_id, group, ra_list, ra_width, dec_list, dec_width,
                        start_time_list, duration,)
    assert cli_kwargs == {'comment': comment}


EVENT_TEST_DATA = [
    (None, None, None),
    (None, 'FAKE_LABEL', True),
    ('FAKE_SEARCH', ['FAKE_LABEL1', 'FAKE_LABEL2'], False),
]
@pytest.mark.parametrize("search,labels,offline",  # noqa: #302
                         EVENT_TEST_DATA)
def test_create_event_subcommand(CLI, search, labels, offline):
    """Test create event subcommand"""
    cmd_args = {
        'group': 'FAKE_GROUP',
        'pipeline': 'FAKE_PIPELINE',
        'event_file': '/path/to/fake/file.xml',
    }

    # Generate command
    cmd = 'create event {group} {pipeline} {event_file}'.format(**cmd_args)
    if search is not None:
        cmd += ' {search}'.format(search=search)
    if labels is not None:
        if isinstance(labels, list):
            cmd += " --labels={labels}".format(labels=",".join(labels))
        else:
            cmd += " --labels={labels}".format(labels=labels)
    if offline:
        cmd += " --offline"

    func = 'ligo.gracedb.rest.GraceDb.createEvent'
    func2 = 'ligo.gracedb.rest.GraceDb.searches'
    with mock.patch(func2, new_callable=mock.PropertyMock) as mock_searches, \
         mock.patch(func) as mock_cli_func:  # noqa: E127

        # Set up return value and call CLI
        mock_searches.return_value = []
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['group'], cmd_args['pipeline'],
                        cmd_args['event_file'],)
    assert cli_kwargs == {'search': search, 'labels': labels,
                          'offline': offline or False}


def test_create_event_legacy_usage(CLI):
    """Test create event legacy usage (search and event file are swapped)"""
    cmd_args = {
        'group': 'FAKE_GROUP',
        'pipeline': 'FAKE_PIPELINE',
        'event_file': '/path/to/fake/file.xml',
        'search': 'FAKE_SEARCH',
    }

    # Generate command
    cmd = 'create event {group} {pipeline} {search} {event_file}'.format(
        **cmd_args)

    # Have to patch client.searches and os.path.isfile
    func = 'ligo.gracedb.rest.GraceDb.createEvent'
    func2 = 'ligo.gracedb.rest.GraceDb.searches'
    func3 = 'ligo.gracedb.cli.commands.create.os.path.isfile'
    with mock.patch(func2, new_callable=mock.PropertyMock) as mock_searches, \
         mock.patch(func3) as mock_isfile, \
         mock.patch(func) as mock_cli_func:  # noqa: E127

        # Set up return values
        mock_searches.return_value = cmd_args['search']
        mock_isfile.return_value = True

        # Call CLI
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['group'], cmd_args['pipeline'],
                        cmd_args['event_file'],)
    assert cli_kwargs == {'search': cmd_args['search'], 'labels': None,
                          'offline': False}


LOG_TEST_DATA = [
    (None, None, None),
    (None, 'FAKE_TAG', 'FAKE_DISP_NAME'),
    ('/path/to/fake/file.txt', ['FAKE_TAG1', 'FAKE_TAG2'],
        ['FAKE_DISP_NAME1', 'FAKE_DISP_NAME2']),
]
@pytest.mark.parametrize("filename,tag_name,tag_disp_name",  # noqa: E302
                         LOG_TEST_DATA)
def test_create_log_subcommand(CLI, filename, tag_name, tag_disp_name):
    """Test create log subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'comment': 'test comment',
    }

    # Generate command
    cmd = "create log {s_id} '{comment}'".format(**cmd_args)
    if filename is not None:
        cmd += " {filename}".format(filename=filename)
    if tag_name is not None:
        tag_name_str = tag_name
        if isinstance(tag_name_str, list):
            tag_name_str = ",".join(tag_name_str)
        cmd += " --tag-name={tag_name}".format(tag_name=tag_name_str)
    if tag_disp_name is not None:
        tag_disp_str = tag_disp_name
        if isinstance(tag_disp_str, list):
            tag_disp_str = ",".join(tag_disp_str)
        cmd += " --tag-display-name={tag_disp_name}".format(
            tag_disp_name=tag_disp_str)

    func = 'ligo.gracedb.rest.GraceDb.writeLog'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['comment'],)
    assert cli_kwargs == {'filename': filename, 'tag_name': tag_name,
                          'displayName': tag_disp_name}


SIGNOFF_TEST_DATA = [None, 'FAKE_INSTRUMENT']
@pytest.mark.parametrize("instrument", SIGNOFF_TEST_DATA)  # noqa: E302
def test_create_signoff_subcommand(CLI, instrument):
    """Test create signoff subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'signoff_type': 'FAKE_SIGNOFF_TYPE',
        'signoff_status': 'FAKE_SIGNOFF_STATUS',
        'comment': 'test comment',
    }

    # Generate command
    cmd = "create signoff {s_id} {signoff_type} {signoff_status} '{comment}'" \
        .format(**cmd_args)
    if instrument is not None:
        cmd += " {inst}".format(inst=instrument)

    func = 'ligo.gracedb.rest.GraceDb.create_signoff'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['signoff_type'],
                        cmd_args['signoff_status'], cmd_args['comment'],)
    assert cli_kwargs == {'instrument': instrument or ''}


SUPEREVENT_TEST_DATA = [
    (None, None, ['G1234', 'G1235']),
    (None, 'FAKE_LABEL', 'G1236'),
    ('FAKE_CATEGORY', ['FAKE_LABEL1', 'FAKE_LABEL2'], None),
]
@pytest.mark.parametrize("category,labels,events",  # noqa: E302
                         SUPEREVENT_TEST_DATA)
def test_create_superevent_subcommand(CLI, category, labels, events):
    """Test create superevent subcommand"""
    cmd_args = {
        't_start': 1,
        't_0': 2,
        't_end': 3,
        'pref_ev': 'G0001',
    }

    # Generate command
    cmd = "create superevent {t_start} {t_0} {t_end} {pref_ev}".format(
        **cmd_args)
    if category is not None:
        cmd += " --category={cat}".format(cat=category)
    if labels is not None:
        if isinstance(labels, list):
            cmd += " --labels={labels}".format(labels=",".join(labels))
        else:
            cmd += " --labels={labels}".format(labels=labels)
    if events is not None:
        if isinstance(events, list):
            cmd += " --events={events}".format(events=",".join(events))
        else:
            cmd += " --events={events}".format(events=events)

    func = 'ligo.gracedb.rest.GraceDb.createSuperevent'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['t_start'], cmd_args['t_0'],
                        cmd_args['t_end'], cmd_args['pref_ev'],)
    assert cli_kwargs == {'category': category or 'production',
                          'labels': labels, 'events': events}


# Define a dict where keys are parameters and values are lists of
# values for those parameters
VOEVENT_TEST_DICT = {
    'skymap_type': [None, 'FAKE_SKYMAP_TYPE'],
    'skymap_filename': [None, 'FAKE_SKYMAP_FILENAME'],
    'external': [None, True],
    'open_alert': [None, True],
    'hardware_inj': [None, True],
    'coinc_comment': [None, True],
    'prob_has_ns': [None, 0.1],
    'prob_has_remnant': [None, 0.2],
    'bns': [None, 0.3],
    'nsbh': [None, 0.4],
    'bbh': [None, 0.5],
    'terrestrial': [None, 0.6],
    'mass_gap': [None, 0.7],
}
# Convert into a list of tuples
VOEVENT_TEST_DATA = zip(*list(six.itervalues(VOEVENT_TEST_DICT)))
@pytest.mark.parametrize(",".join(list(VOEVENT_TEST_DICT)),  # noqa: E302
                         VOEVENT_TEST_DATA)
def test_create_voevent_subcommand(
    CLI, skymap_type, skymap_filename, external, open_alert, hardware_inj,
    coinc_comment, prob_has_ns, prob_has_remnant, bns, nsbh, bbh, terrestrial,
    mass_gap
):
    """Test create voevent subcommand"""
    cmd_args = {
        's_id': 'S001122a',
        'voevent_type': 'FAKE_VOEVENT_TYPE',
    }

    # Generate command
    cmd = "create voevent {s_id} {voevent_type}".format(**cmd_args)
    if skymap_type is not None:
        cmd += " --skymap-type={st}".format(st=skymap_type)
    if skymap_filename is not None:
        cmd += " --skymap-filename={sf}".format(sf=skymap_filename)
    if external:
        cmd += " --external"
    if open_alert:
        cmd += " --open-alert"
    if hardware_inj:
        cmd += " --hardware-inj"
    if coinc_comment:
        cmd += " --coinc-comment"
    if prob_has_ns is not None:
        cmd += " --prob-has-ns={phn}".format(phn=prob_has_ns)
    if prob_has_remnant is not None:
        cmd += " --prob-has-remnant={phr}".format(phr=prob_has_remnant)
    if bns is not None:
        cmd += " --bns={bns}".format(bns=bns)
    if nsbh is not None:
        cmd += " --nsbh={nsbh}".format(nsbh=nsbh)
    if bbh is not None:
        cmd += " --bbh={bbh}".format(bbh=bbh)
    if terrestrial is not None:
        cmd += " --terrestrial={terr}".format(terr=terrestrial)
    if mass_gap is not None:
        cmd += " --mass-gap={mg}".format(mg=mass_gap)

    func = 'ligo.gracedb.rest.GraceDb.createVOEvent'
    with mock.patch(func) as mock_cli_func:
        CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (cmd_args['s_id'], cmd_args['voevent_type'],)
    assert cli_kwargs == {
        'skymap_type': skymap_type,
        'skymap_filename': skymap_filename,
        'internal': not (external or False),
        'open_alert': open_alert or False,
        'hardware_inj': hardware_inj or False,
        'CoincComment': coinc_comment or False,
        'ProbHasNS': prob_has_ns,
        'ProbHasRemnant': prob_has_remnant,
        'BNS': bns,
        'NSBH': nsbh,
        'BBH': bbh,
        'Terrestrial': terrestrial,
        'MassGap': mass_gap,
    }
