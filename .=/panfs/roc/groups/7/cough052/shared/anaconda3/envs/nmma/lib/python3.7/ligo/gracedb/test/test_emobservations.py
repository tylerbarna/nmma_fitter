try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


@pytest.mark.parametrize("emo_number", [None, 12])
def test_superevent_emobservations(safe_client, emo_number):
    superevent_id = 'TS190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if emo_number:
        template_key = 'superevent-emobservation-detail-template'
    else:
        template_key = 'superevent-emobservation-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.emobservations(superevent_id,
                                   emobservation_num=emo_number)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    num_kwargs = 1
    if emo_number:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['superevent_id'] == superevent_id
    if emo_number:
        assert template_call_kwargs['N'] == emo_number


@pytest.mark.parametrize("emo_number", [None, 12])
def test_event_logs(safe_client, emo_number):
    graceid = 'T123456'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if emo_number:
        template_key = 'emobservation-detail-template'
    else:
        template_key = 'emobservation-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.emobservations(graceid, emobservation_num=emo_number)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    num_kwargs = 1
    if emo_number:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['graceid'] == graceid
    if emo_number:
        assert template_call_kwargs['N'] == emo_number


@pytest.mark.parametrize(
    "is_event,obj_id",
    [
        (True, "T123456"),
        (False, "TS121212abc"),
    ]
)
def test_write_emobservations(safe_client, is_event, obj_id):

    # Generate data
    emgroup = 'FAKE_EMGROUP'
    ra_list = [1] * 4
    ra_width_list = [2] * 4
    dec_list = [3] * 4
    dec_width_list = [4] * 4
    start_time_list = [5] * 4
    duration_list = [6] * 4
    comment = 'test'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'emobservation-list-template'
    else:
        template_key = 'superevent-emobservation-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up emgroup mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'em-groups': [emgroup]}

    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(si_prop, mock_si_dict), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.writeEMObservation(
            obj_id, emgroup, ra_list, ra_width_list, dec_list, dec_width_list,
            start_time_list, duration_list, comment=comment
        )

    # Test call to self.post
    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 1
    assert 'json' in post_call_kwargs
    request_body = post_call_kwargs['json']
    assert request_body['group'] == emgroup
    assert request_body['ra_list'] == ra_list
    assert request_body['ra_width_list'] == ra_width_list
    assert request_body['dec_list'] == dec_list
    assert request_body['dec_width_list'] == dec_width_list
    assert request_body['start_time_list'] == start_time_list
    assert request_body['duration_list'] == duration_list
    assert request_body['comment'] == comment

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    if is_event:
        call_key = 'graceid'
    else:
        call_key = 'superevent_id'
    assert template_call_kwargs[call_key] == obj_id


@pytest.mark.parametrize(
    "ras,ra_widths,decs,dec_widths,start_times,durations",
    [
        ([1] * 4, [1] * 4, [1] * 4, [1] * 4, [1] * 4, [1] * 5),
        ([1] * 4, [1] * 4, [1] * 4, [1] * 4, [1] * 5, [1] * 4),
        ([1] * 4, [1] * 4, [1] * 4, [1] * 5, [1] * 4, [1] * 4),
        ([1] * 4, [1] * 4, [1] * 5, [1] * 4, [1] * 4, [1] * 4),
        ([1] * 4, [1] * 5, [1] * 4, [1] * 4, [1] * 4, [1] * 4),
        ([1] * 5, [1] * 4, [1] * 4, [1] * 4, [1] * 4, [1] * 4),
        ([1] * 1, [1] * 2, [1] * 3, [1] * 4, [1] * 5, [1] * 6),
    ]
)
def test_write_emobservation_different_list_lengths(
    safe_client, ras, ra_widths, decs, dec_widths, start_times, durations
):

    # Set up emgroup mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'em-groups': ['emgroup1']}

    err_msg = ("raList, decList, startTimeList, raWidthList, decWidthList, "
               "and durationList should be the same length")
    with mock.patch(si_prop, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client.writeEMObservation(
                'TS121212a', 'emgroup1', ras, ra_widths, decs, dec_widths,
                start_times, durations, comment="test"
            )


def test_write_emobservation_bad_emgroup(safe_client):

    # Set up emgroup mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'em-groups': ['emgroup1']}

    err_msg = "group must be one of {groups}".format(
        groups=", ".join(mock_si_dict['em-groups']))
    with mock.patch(si_prop, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client.writeEMObservation(
                'TS121212a', 'emgroup20', 1, 1, 1, 1, 1, 1, comment="test"
            )
