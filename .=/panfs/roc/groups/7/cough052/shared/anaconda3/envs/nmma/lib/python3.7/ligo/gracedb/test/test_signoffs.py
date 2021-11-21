try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


@pytest.mark.parametrize(
    "method",
    ['signoffs', 'create_signoff', 'update_signoff', 'delete_signoff']
)
def test_event_signoff_actions(safe_client, method):
    graceid = 'T123456'
    err_msg = 'Not yet implemented for events'
    with pytest.raises(NotImplementedError, match=err_msg):
        getattr(safe_client, method)(
            graceid, 'fake_arg1', 'fake_arg2', 'fake_arg3'
        )


@pytest.mark.parametrize(
    "signoff_type,instrument",
    [(None, ""), ("OP", "H1"), ("ADV", "")]
)
def test_get_superevent_signoffs(safe_client, signoff_type, instrument):
    superevent_id = 'TS120345zd'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if signoff_type:
        template_key = 'superevent-signoff-detail-template'
    else:
        template_key = 'superevent-signoff-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb._signoff_helper') as mock_sh, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.signoffs(superevent_id, signoff_type=signoff_type,
                             instrument=instrument)

    call_args, call_kwargs = mock_sh.call_args
    assert len(call_args) == 4
    assert call_args == (superevent_id, 'get', mock_template,
                         {'superevent_id': superevent_id},)
    assert len(call_kwargs) == 2
    assert call_kwargs['signoff_type'] == signoff_type
    assert call_kwargs['instrument'] == instrument


@pytest.mark.parametrize(
    "signoff_type,instrument",
    [(None, ""), ("OP", "H1"), ("ADV", "")]
)
def test_create_superevent_signoff(safe_client, signoff_type, instrument):
    superevent_id = 'TS120345zd'
    status = 'OK'
    comment = 'test comment'

    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-signoff-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb._signoff_helper') as mock_sh, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.create_signoff(superevent_id, signoff_type, status,
                                   comment, instrument=instrument)

    call_args, call_kwargs = mock_sh.call_args
    assert len(call_args) == 4
    assert call_args == (superevent_id, 'create', mock_template,
                         {'superevent_id': superevent_id},)
    assert len(call_kwargs) == 4
    assert call_kwargs['signoff_type'] == signoff_type
    assert call_kwargs['instrument'] == instrument
    assert call_kwargs['status'] == status
    assert call_kwargs['comment'] == comment


@pytest.mark.parametrize(
    "signoff_type,instrument",
    [(None, ""), ("OP", "H1"), ("ADV", "")]
)
def test_update_superevent_signoff(safe_client, signoff_type, instrument):
    superevent_id = 'TS120345zd'
    status = 'OK'
    comment = 'test comment'

    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-signoff-detail-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb._signoff_helper') as mock_sh, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.update_signoff(superevent_id, signoff_type, status,
                                   comment, instrument=instrument)

    call_args, call_kwargs = mock_sh.call_args
    assert len(call_args) == 4
    assert call_args == (superevent_id, 'update', mock_template,
                         {'superevent_id': superevent_id},)
    assert len(call_kwargs) == 4
    assert call_kwargs['signoff_type'] == signoff_type
    assert call_kwargs['instrument'] == instrument
    assert call_kwargs['status'] == status
    assert call_kwargs['comment'] == comment


@pytest.mark.parametrize("status,comment", [(None, None), (None, "")])
def test_update_signoff_bad_args(safe_client, status, comment):
    err_msg = "Provide at least one of 'status' or 'comment'"
    with pytest.raises(ValueError, match=err_msg):
        safe_client.update_signoff('TS120412bc', 'ADV', status=status,
                                   comment=comment)


@pytest.mark.parametrize(
    "signoff_type,instrument",
    [(None, ""), ("OP", "H1"), ("ADV", "")]
)
def test_delete_superevent_signoff(safe_client, signoff_type, instrument):
    superevent_id = 'TS120345zd'

    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-signoff-detail-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb._signoff_helper') as mock_sh, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.delete_signoff(superevent_id, signoff_type,
                                   instrument=instrument)

    call_args, call_kwargs = mock_sh.call_args
    assert len(call_args) == 4
    assert call_args == (superevent_id, 'delete', mock_template,
                         {'superevent_id': superevent_id},)
    assert len(call_kwargs) == 2
    assert call_kwargs['signoff_type'] == signoff_type
    assert call_kwargs['instrument'] == instrument


@pytest.mark.parametrize(
    "action,signoff_type,instrument,status,comment",
    [
        ('create', 'ADV', '', 'NO', 'test comment'),
        ('update', 'OP', 'H1', None, None),
        ('update', 'OP', 'H1', 'OK', None),
        ('update', 'OP', 'H1', None, 'new comment'),
        ('update', 'ADV', '', 'OK', 'looks good'),
        ('get', None, None, None, None),
        ('get', 'OP', 'L1', None, None),
        ('get', 'ADV', '', None, None),
        ('delete', 'OP', 'V1', None, None),
        ('delete', 'ADV', '', None, None),
    ]
)
def test_signoff_helper(safe_client, action, signoff_type, instrument, status,
                        comment):
    superevent_id = 'TS340229zzz'

    # Mocks
    template = mock.MagicMock()
    uri_kwargs = {}

    # Set up mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'signoff-types': {'ADV': 'advocate', 'OP': 'operator'},
        'instruments': {'H1': 'Hanford', 'L1': 'Livingston', 'V1': 'Virgo'},
        'signoff-statuses': {'OK': 'OKAY', 'NO': 'NOT OKAY'},
    }

    # Mock request method
    expected_request_method_dict = {
        'create': 'POST',
        'update': 'PATCH',
        'get': 'GET',
        'delete': 'DELETE',
    }
    request_func = 'ligo.gracedb.rest.GraceDb.{action}'.format(
        action=expected_request_method_dict[action].lower())

    # Call
    with mock.patch(request_func) as mock_rf, \
         mock.patch(si_property, mock_si_dict):  # noqa: E127
        safe_client._signoff_helper(
            superevent_id, action, template, uri_kwargs,
            signoff_type=signoff_type, instrument=instrument, status=status,
            comment=comment
        )

    # Check template kwargs
    template_args, template_kwargs = template.format.call_args
    assert len(template_args) == 0
    if action == 'create':
        assert len(template_kwargs) == 0
    else:
        if signoff_type:
            assert len(template_kwargs) == 1
            assert template_kwargs['typeinst'] == signoff_type + instrument
        else:
            assert len(template_kwargs) == 0

    # Check request method call
    rf_args, rf_kwargs = mock_rf.call_args
    assert len(rf_args) == 1
    if action == 'create':
        assert len(rf_kwargs) == 1
        assert 'data' in rf_kwargs
        assert rf_kwargs['data']['signoff_type'] == signoff_type
        assert rf_kwargs['data']['instrument'] == instrument
        assert rf_kwargs['data']['status'] == status
        assert rf_kwargs['data']['comment'] == comment
    elif action == 'update' and (status or comment):
        assert len(rf_kwargs) == 1
        assert 'data' in rf_kwargs
        body_len = 0
        if comment:
            body_len += 1
            assert rf_kwargs['data']['comment'] == comment
        if status:
            body_len += 1
            assert rf_kwargs['data']['status'] == status
        assert len(rf_kwargs['data']) == body_len
    else:
        assert len(rf_kwargs) == 0


def test_signoff_helper_bad_signoff_type(safe_client):

    # Set up mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'signoff-types': {'ADV': 'advocate', 'OP': 'operator'},
    }

    err_msg = 'signoff_type must be one of: {st}'.format(
        st=", ".join(mock_si_dict['signoff-types']))
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client._signoff_helper('TS340229zz', '', '', '',
                                        signoff_type='FAKE')


def test_signoff_helper_bad_instrument(safe_client):

    # Set up mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'instruments': {'H1': 'Hanford', 'L1': 'Livingston', 'V1': 'Virgo'},
    }

    err_msg = 'instrument must be one of: {inst}'.format(
        inst=", ".join(mock_si_dict['instruments']))
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client._signoff_helper('TS340229zz', '', '', '',
                                        instrument='FAKE')


def test_signoff_helper_bad_status(safe_client):

    # Set up mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'signoff-statuses': {'OK': 'OKAY', 'NO': 'NOT OKAY'},
    }

    err_msg = 'status must be one of: {status}'.format(
        status=", ".join(mock_si_dict['signoff-statuses']))
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client._signoff_helper('TS340229zz', '', '', '',
                                        status='FAKE')


def test_signoff_helper_operator_signoff_no_instrument(safe_client):

    # Set up mock service info dict
    si_property = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {
        'signoff-types': {'ADV': 'advocate', 'OP': 'operator'},
    }

    err_msg = 'Operator signoffs require an instrument'
    with mock.patch(si_property, mock_si_dict):
        with pytest.raises(ValueError, match=err_msg):
            safe_client._signoff_helper('TS340229zz', '', '', '',
                                        signoff_type='OP')


def test_signoff_helper_bad_action(safe_client):

    err_msg = "action should be 'create', 'update', 'get', or 'delete'"
    with pytest.raises(ValueError, match=err_msg):
        safe_client._signoff_helper('TS340229zz', 'fake', '', '')
