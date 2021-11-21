try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import six

import pytest

# Import get_mimetype since mimetype mapping can vary
# on different machines, i.e., locally vs in gitlab CI:

from ligo.gracedb.utils import get_mimetype


@pytest.mark.parametrize(
    "group,pipeline,search,offline,labels",
    [
        ('g1', 'p1', None, True, None),
        ('g1', 'p2', 's2', False, None),
        ('g2', 'p2', None, False, 'l1'),
        ('g1', 'p1', None, False, ['l1']),
        ('g1', 'p1', None, False, ['l2', 'l1']),
    ]
)
def test_create_event(safe_client, group, pipeline, search, offline, labels):
    filename = 'file.xml'
    file_mtype = get_mimetype(filename)

    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'groups': ['g1', 'g2'],
        'pipelines': ['p1', 'p2'],
        'searches': ['s1', 's2'],
        'labels': ['l1', 'l2'],
    }

    # Set up mock open
    open_func = 'ligo.gracedb.rest.open'
    mock_data = 'fake data'
    open_mocker = mock.mock_open(read_data=mock_data)

    # Call function
    links_prop = 'ligo.gracedb.rest.GraceDb.links'
    post_func = 'ligo.gracedb.rest.GraceDb.post'
    with mock.patch(links_prop, new_callable=mock.PropertyMock), \
         mock.patch(open_func, open_mocker), \
         mock.patch(si_property, mock_si_dict), \
         mock.patch(post_func) as mock_post:  # noqa: E127
        safe_client.createEvent(group, pipeline, filename, search=search,
                                labels=labels, offline=offline)

    # Get args used to call post
    call_args, call_kwargs = mock_post.call_args
    assert len(call_args) == 1
    assert len(call_kwargs) == 2
    assert 'data' in call_kwargs
    assert 'files' in call_kwargs
    assert call_kwargs['files'] == {'eventFile': (filename, open_mocker(),
                                                  file_mtype)}

    # Check body (convert to dict)
    body = dict(call_kwargs['data'])
    assert body['group'] == group
    assert body['pipeline'] == pipeline
    assert body['offline'] == str(offline)
    if search:
        assert body['search'] == search
    else:
        assert 'search' not in body
    if labels:
        if isinstance(labels, six.string_types):
            labels = [labels]
        req_labels = []
        for t in call_kwargs['data']:
            if t[0] == 'labels':
                req_labels.append(t[1])
        assert sorted(labels) == sorted(req_labels)


def test_create_event_from_stdin(safe_client):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'groups': ['g1', 'g2'],
        'pipelines': ['p1', 'p2'],
        'searches': ['s1', 's2'],
        'labels': ['l1', 'l2'],
    }

    # Set up mock sys.stdin.read
    stdin_obj = 'ligo.gracedb.rest.sys.stdin'
    mock_stdin_data = 'fake stdin data'
    mock_data_type = 'application/octet-stream'

    # Call function
    links_prop = 'ligo.gracedb.rest.GraceDb.links'
    post_func = 'ligo.gracedb.rest.GraceDb.post'
    with mock.patch(links_prop, new_callable=mock.PropertyMock), \
         mock.patch(si_property, mock_si_dict), \
         mock.patch(stdin_obj) as mock_stdin, \
         mock.patch(post_func) as mock_post:  # noqa: E127
        mock_stdin.read.return_value = mock_stdin_data
        safe_client.createEvent('g1', 'p1', '-')

    # Get args used to call post
    call_args, call_kwargs = mock_post.call_args
    assert len(call_kwargs) == 2
    assert 'data' in call_kwargs
    assert 'files' in call_kwargs
    assert call_kwargs['files'] == {'eventFile': ('initial.data',
                                    mock_stdin_data, mock_data_type)}


def test_create_event_with_filecontents(safe_client):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'groups': ['g1', 'g2'],
        'pipelines': ['p1', 'p2'],
        'searches': ['s1', 's2'],
        'labels': ['l1', 'l2'],
    }

    # File data
    filename = 'file.xml'
    file_mtype = get_mimetype(filename)
    filecontents = 'event file contents'

    # Call function
    links_prop = 'ligo.gracedb.rest.GraceDb.links'
    post_func = 'ligo.gracedb.rest.GraceDb.post'
    with mock.patch(links_prop, new_callable=mock.PropertyMock), \
         mock.patch(si_property, mock_si_dict), \
         mock.patch(post_func) as mock_post:  # noqa: E127
        safe_client.createEvent('g1', 'p1', filename,
                                filecontents=filecontents)

    # Get args used to call post
    call_args, call_kwargs = mock_post.call_args
    assert len(call_args) == 1
    assert len(call_kwargs) == 2
    assert 'files' in call_kwargs
    assert call_kwargs['files'] == {'eventFile': (filename, filecontents,
                                                  file_mtype)}


def test_create_event_with_bad_group(safe_client):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'groups': ['g1']}

    # Call
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match='bad group'):
            safe_client.createEvent('g2', '', '')


def test_create_event_with_bad_pipeline(safe_client):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'groups': ['g1'], 'pipelines': ['p1']}

    # Call
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match='bad pipeline'):
            safe_client.createEvent('g1', 'p2', '')


def test_create_event_with_bad_search(safe_client):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'groups': ['g1'], 'pipelines': ['p1'], 'searches': ['s1']}

    # Call
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match='bad search'):
            safe_client.createEvent('g1', 'p1', '', search='s2')


@pytest.mark.parametrize("offline", [1, 1.3, {}, [], (True,), None])
def test_create_event_with_bad_offline(safe_client, offline):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'groups': ['g1'], 'pipelines': ['p1'], 'searches': ['s1']}

    # Call
    err_msg = "offline parameter should be a bool"
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(TypeError, match=err_msg):
            safe_client.createEvent('g1', 'p1', '', search='s1',
                                    offline=offline)


@pytest.mark.parametrize("labels", [1, 1.3, {}])
def test_create_event_with_bad_label_type(safe_client, labels):
    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'groups': ['g1'], 'pipelines': ['p1'], 'searches': ['s1']}

    # Call
    err_msg = "labels arg is {tl}, should be str or list".format(
        tl=type(labels))
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(TypeError, match=err_msg):
            safe_client.createEvent('g1', 'p1', '', search='s1',
                                    labels=labels)


def test_create_event_with_bad_label_value(safe_client):
    label = 'l3'

    # Mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'groups': ['g1'],
        'pipelines': ['p1'],
        'searches': ['s1'],
        'labels': ['l1', 'l2'],
    }

    # Call
    err_msg = "Label '{label}' does not exist in the database".format(
        label=label)
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client.createEvent('g1', 'p1', '', search='s1',
                                    labels=label)


@pytest.mark.parametrize(
    "labels",
    [["BAD"], 'BAD', ["GOOD_LABEL", "BAD"], ('BAD', 'GOOD_LABEL')]
)
def test_creation_with_bad_labels(safe_client, labels):
    with mock.patch('ligo.gracedb.rest.GraceDb.allowed_labels',
                    new_callable=mock.PropertyMock) as mock_labels:
        mock_labels.return_value = ['GOOD_LABEL']

        with pytest.raises(ValueError):
            safe_client.createSuperevent(1, 2, 3, preferred_event='T0001',
                                         category='T', labels=labels)


@pytest.mark.parametrize("labels", [1, 2.34, {'test': 'bad'}, (1, 'GOOD')])
def test_creation_with_bad_label_type(safe_client, labels):

    with pytest.raises(TypeError):
        safe_client.createSuperevent(1, 2, 3, preferred_event='T0001',
                                     category='T', labels=labels)


@pytest.mark.parametrize("category", ['other', 'new', 'etc'])
def test_creation_with_bad_category(safe_client, category):
    with mock.patch('ligo.gracedb.rest.GraceDb.superevent_categories',
                    new_callable=mock.PropertyMock) as mock_sc:
        mock_sc.return_value = {
            'P': 'Production',
            'T': 'Test',
            'M': 'MDC',
        }

        with pytest.raises(ValueError):
            safe_client.createSuperevent(1, 2, 3, preferred_event='T0001',
                                         category=category)


@pytest.mark.parametrize("category", [1, 2.34, {'test': 'bad'}, None])
def test_creation_with_bad_category_type(safe_client, category):
    with mock.patch('ligo.gracedb.rest.GraceDb.superevent_categories',
                    new_callable=mock.PropertyMock) as mock_sc:
        mock_sc.return_value = {
            'P': 'Production',
            'T': 'Test',
            'M': 'MDC',
        }

        with pytest.raises(TypeError):
            safe_client.createSuperevent(1, 2, 3, preferred_event='T0001',
                                         category=category)
    pass


@pytest.mark.parametrize(
    "events",
    [1, ['G0001', 3], [()], [1, 2, 3.44]]
)
def test_creation_with_bad_event_graceids(safe_client, events):
    with pytest.raises(TypeError):
        safe_client.createSuperevent(1, 2, 3, preferred_event='T0001',
                                     category='T', events=events)


@pytest.mark.parametrize(
    "t_start,t_0,t_end,preferred_event,category,events,labels",
    [
        (1, 2, 3, 'T0001', 'T', None, None),
        (1, 2, 3, 'T0001', 'T', 'T0002', None),
        (1, 2, 3, 'T0001', 'T', None, 'INJ'),
        (1, 2, 3, 'T0001', 'T', ['T0002', 'T0003'], ['INJ', 'DQV']),
    ]
)
def test_creation_args(
    safe_client, t_start, t_0, t_end, preferred_event, category, events, labels
):
    with mock.patch('ligo.gracedb.rest.GraceDb.superevent_categories',
                    new_callable=mock.PropertyMock) as mock_sc, \
         mock.patch('ligo.gracedb.rest.GraceDb.allowed_labels',  # noqa: E127
                    new_callable=mock.PropertyMock) as mock_labels, \
         mock.patch('ligo.gracedb.rest.GraceDb.links',
                    new_callable=mock.PropertyMock), \
         mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post:
        mock_sc.return_value = {
            'P': 'Production',
            'T': 'Test',
            'M': 'MDC',
        }
        mock_labels.return_value = ['DQV', 'INJ']
        safe_client.createSuperevent(
            t_start, t_0, t_end, preferred_event, category=category,
            labels=labels, events=events
        )

    # Check args
    call_args, call_kwargs = mock_post.call_args
    body = call_kwargs['data']
    assert body['t_start'] == t_start
    assert body['t_0'] == t_0
    assert body['t_end'] == t_end
    assert body['preferred_event'] == preferred_event
    assert body['category'] == category
    if events:
        if isinstance(events, six.string_types):
            events = [events]
        assert body['events'] == events
    if labels:
        if isinstance(labels, six.string_types):
            labels = [labels]
        assert body['labels'] == labels


def test_update_no_args(safe_client):
    err_msg = ('Provide at least one of t_start, t_0, t_end, preferred_event, '
               'em_type, time_coinc_far, or space_coinc_far')
    with pytest.raises(ValueError, match=err_msg):
        safe_client.updateSuperevent('S181224a')


@pytest.mark.parametrize(
    "update_kwargs",
    [
        {'t_start': 1},
        {'t_0': 2},
        {'t_end': 3},
        {'preferred_event': 'G0001'},
        {'em_type': 'EM_TEST'},
        {'time_coinc_far': 4},
        {'space_coinc_far': 5},
        {'t_start': 1, 't_0': 2, 't_end': 3, 'preferred_event': 'G0001',
         'em_type': 'EM_TEST', 'time_coinc_far': 4, 'space_coinc_far': 5},
    ]
)
def test_update_args(safe_client, update_kwargs):
    with mock.patch('ligo.gracedb.rest.GraceDb.patch') as mock_patch, \
         mock.patch('ligo.gracedb.rest.GraceDb.templates'):  # noqa: E127
        safe_client.updateSuperevent('S181224a', **update_kwargs)

    # Check results
    call_args, call_kwargs = mock_patch.call_args
    body = call_kwargs['data']
    assert sorted(list(update_kwargs)) == sorted(list(body))
    for k in update_kwargs:
        assert update_kwargs[k] == body[k]


def test_add_event(safe_client):
    superevent_id = 'S190302abc'
    event_graceid = 'G123456'
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-event-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.addEventToSuperevent(superevent_id, event_graceid)

    call_args, call_kwargs = mock_post.call_args
    assert call_kwargs['data'] == {'event': event_graceid}

    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs['superevent_id'] == superevent_id


def test_remove_event(safe_client):
    superevent_id = 'S190302abc'
    event_graceid = 'G123456'
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-event-detail-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.delete') as mock_delete, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.removeEventFromSuperevent(superevent_id, event_graceid)

    delete_call_args, delete_call_kwargs = mock_delete.call_args
    assert len(delete_call_args) == 1
    assert delete_call_kwargs == {}

    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 2
    assert template_call_kwargs['superevent_id'] == superevent_id
    assert template_call_kwargs['graceid'] == event_graceid


def test_confirm_as_gw(safe_client):
    superevent_id = 'S190302abc'
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-confirm-as-gw-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.confirm_superevent_as_gw(superevent_id)

    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert post_call_kwargs == {}

    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs['superevent_id'] == superevent_id


# Test get
def test_get(safe_client):
    superevent_id = 'S190302abc'
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-detail-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.superevent(superevent_id)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs['superevent_id'] == superevent_id


@pytest.mark.parametrize("filecontents", [None, "fake data"])
def test_replace_event(safe_client, filecontents):
    graceid = 'T123456'
    filename = 'file.xml'
    file_mtype = get_mimetype(filename)

    # Set up mock template
    mock_template = mock.MagicMock()
    mock_template_dict = {'event-detail-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up mock open
    open_func = 'ligo.gracedb.rest.open'
    mock_data = 'fake open data'
    open_mocker = mock.mock_open(read_data=mock_data)

    # Call function
    with mock.patch('ligo.gracedb.rest.GraceDb.put') as mock_put, \
         mock.patch(open_func, open_mocker), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.replaceEvent(graceid, filename, filecontents=filecontents)

    # Check template call
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs == {'graceid': graceid}

    # Check put call
    call_args, call_kwargs = mock_put.call_args
    assert len(call_args) == 1
    assert len(call_kwargs) == 1
    assert 'files' in call_kwargs
    if filecontents:
        expected_data = filecontents
    else:
        expected_data = open_mocker()
    assert call_kwargs['files'] == {'eventFile': (filename, expected_data,
                                                  file_mtype)}


def test_get_event(safe_client):
    graceid = 'T123456'

    # Set up mock template
    mock_template = mock.MagicMock()
    mock_template_dict = {'event-detail-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Call function
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.event(graceid)

    # Check template call
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs == {'graceid': graceid}

    # Check get call
    call_args, call_kwargs = mock_get.call_args
    assert len(call_args) == 1
    assert call_kwargs == {}


@pytest.mark.parametrize("query", [None, 'fake query'])
def test_num_events(safe_client, query):
    # Call function
    link_prop = 'ligo.gracedb.rest.GraceDb.links'
    get_func = 'ligo.gracedb.rest.GraceDb.get'
    with mock.patch(link_prop, new_callable=mock.PropertyMock), \
         mock.patch(get_func) as mock_get:  # noqa: E127
        safe_client.numEvents(query=query)

    # Check get calls
    assert len(mock_get.call_args[0]) == 1
    assert mock_get.call_args[1] == {}


# TODO: test search
