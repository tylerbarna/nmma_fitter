try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


@pytest.mark.parametrize(
    "is_event,label_name",
    [
        (True, ""),
        (False, ""),
        (True, 'LABEL_NAME'),
        (False, 'LABEL_NAME'),
    ]
)
def test_get_labels(safe_client, is_event, label_name):
    if is_event:
        obj_id = 'T123456'
    else:
        obj_id = 'TS190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'event-label-template'
    else:
        if label_name:
            template_key = 'superevent-label-detail-template'
        else:
            template_key = 'superevent-label-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up allowed_labels mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'labels': ['LABEL_NAME']}
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(si_prop, mock_si_dict), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.labels(obj_id, label=label_name)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    if is_event:
        assert len(template_call_kwargs) == 2
        assert template_call_kwargs['graceid'] == obj_id
        assert template_call_kwargs['label'] == label_name
    else:
        if label_name:
            assert len(template_call_kwargs) == 2
            assert template_call_kwargs['superevent_id'] == obj_id
            assert template_call_kwargs['label_name'] == label_name
        else:
            assert len(template_call_kwargs) == 1
            assert template_call_kwargs['superevent_id'] == obj_id


def test_get_label_bad_label_name(safe_client):
    # Set up allowed_labels mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'labels': ['LABEL_NAME']}

    label = 'bad_label'
    err_msg = "Label '{label}' does not exist in the database".format(
        label=label)
    with mock.patch(si_prop, mock_si_dict):
        with pytest.raises(NameError, match=err_msg):
            safe_client.labels('T123456', label=label)


@pytest.mark.parametrize("is_event", [True, False])
def test_write_label(safe_client, is_event):
    label = 'TEST_LABEL'
    if is_event:
        obj_id = 'T123456'
        request_function = 'ligo.gracedb.client.GraceDBClient.put'
    else:
        obj_id = 'TS190302abc'
        request_function = 'ligo.gracedb.client.GraceDBClient.post'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'event-label-template'
    else:
        template_key = 'superevent-label-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up allowed_labels mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'labels': [label]}
    with mock.patch(si_prop, mock_si_dict), \
         mock.patch(request_function) as mock_rf, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.writeLabel(obj_id, label)

    rf_call_args, rf_call_kwargs = mock_rf.call_args
    assert len(rf_call_args) == 1
    assert len(rf_call_kwargs) == 1
    assert 'data' in rf_call_kwargs
    if is_event:
        assert rf_call_kwargs['data'] == {}
    else:
        assert rf_call_kwargs['data'] == {'name': label}

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    if is_event:
        assert len(template_call_kwargs) == 2
        assert template_call_kwargs['graceid'] == obj_id
        assert template_call_kwargs['label'] == label
    else:
        assert len(template_call_kwargs) == 1
        assert template_call_kwargs['superevent_id'] == obj_id


def test_write_label_bad_label_name(safe_client):
    # Set up allowed_labels mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'labels': ['LABEL_NAME']}

    label = 'bad_label'
    err_msg = "Label '{label}' does not exist in the database".format(
        label=label)
    with mock.patch(si_prop, mock_si_dict):
        with pytest.raises(NameError, match=err_msg):
            safe_client.writeLabel('T123456', label)


@pytest.mark.parametrize("is_event", [True, False])
def test_remove_label(safe_client, is_event):
    label = 'TEST_LABEL'
    if is_event:
        obj_id = 'T123456'
    else:
        obj_id = 'TS190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'event-label-template'
    else:
        template_key = 'superevent-label-detail-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up allowed_labels mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'labels': [label]}
    with mock.patch('ligo.gracedb.rest.GraceDb.delete') as mock_delete, \
         mock.patch(si_prop, mock_si_dict), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.removeLabel(obj_id, label)

    delete_call_args, delete_call_kwargs = mock_delete.call_args
    assert len(delete_call_args) == 1
    assert len(delete_call_kwargs) == 0

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 2
    if is_event:
        assert template_call_kwargs['graceid'] == obj_id
        assert template_call_kwargs['label'] == label
    else:
        assert template_call_kwargs['superevent_id'] == obj_id
        assert template_call_kwargs['label_name'] == label
