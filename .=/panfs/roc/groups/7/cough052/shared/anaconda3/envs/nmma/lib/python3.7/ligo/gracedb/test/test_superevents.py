try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import six

import pytest


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
        {'t_start': 111, 't_0': 222, 't_end': 333, 'preferred_event': 'G0001',
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


# TODO: test search
