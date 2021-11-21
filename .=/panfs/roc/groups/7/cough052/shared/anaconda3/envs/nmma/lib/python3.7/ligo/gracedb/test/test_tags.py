try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


@pytest.mark.parametrize("is_event", [True, False])
def test_get_tags(safe_client, is_event):
    if is_event:
        obj_id = 'T123456'
    else:
        obj_id = 'TS190302abc'
    N = 2

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'taglist-template'
    else:
        template_key = 'superevent-log-tag-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up allowed_labels mock
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.tags(obj_id, N)

    # Test call args to get() method
    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 2
    assert template_call_kwargs['N'] == N
    if is_event:
        assert template_call_kwargs['graceid'] == obj_id
    else:
        assert template_call_kwargs['superevent_id'] == obj_id


@pytest.mark.parametrize(
    "is_event,display_name",
    [
        (True, None),
        (False, None),
        (True, 'test_disp'),
        (False, 'test_disp'),
    ]
)
def test_add_tag(safe_client, is_event, display_name):
    if is_event:
        obj_id = 'T123456'
        request_func = 'ligo.gracedb.client.GraceDBClient.put'
    else:
        obj_id = 'TS190302abc'
        request_func = 'ligo.gracedb.client.GraceDBClient.post'
    N = 7
    tag_name = 'test_tag'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'tag-template'
    else:
        template_key = 'superevent-log-tag-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    with mock.patch(request_func) as mock_rf, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.addTag(obj_id, N, tag_name, displayName=display_name)

    rf_call_args, rf_call_kwargs = mock_rf.call_args
    assert len(rf_call_args) == 1
    assert len(rf_call_kwargs) == 1
    assert 'data' in rf_call_kwargs
    if is_event:
        if display_name:
            assert len(rf_call_kwargs['data']) == 1
            assert rf_call_kwargs['data']['displayName'] == display_name
        else:
            assert rf_call_kwargs['data'] == {}
    else:
        assert rf_call_kwargs['data']['name'] == tag_name
        if display_name:
            assert len(rf_call_kwargs['data']) == 2
            assert rf_call_kwargs['data']['displayName'] == display_name
        else:
            assert len(rf_call_kwargs['data']) == 1

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert template_call_kwargs['N'] == N
    if is_event:
        assert len(template_call_kwargs) == 3
        assert template_call_kwargs['graceid'] == obj_id
        assert template_call_kwargs['tag_name'] == tag_name
    else:
        assert len(template_call_kwargs) == 2
        assert template_call_kwargs['superevent_id'] == obj_id


@pytest.mark.parametrize("is_event", [True, False])
def test_remove_tag(safe_client, is_event):
    if is_event:
        obj_id = 'T123456'
    else:
        obj_id = 'TS190302abc'
    N = 7
    tag_name = 'test_tag'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'tag-template'
    else:
        template_key = 'superevent-log-tag-detail-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up allowed_labels mock
    with mock.patch('ligo.gracedb.rest.GraceDb.delete') as mock_delete, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.removeTag(obj_id, N, tag_name)

    delete_call_args, delete_call_kwargs = mock_delete.call_args
    assert len(delete_call_args) == 1
    assert len(delete_call_kwargs) == 0

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 3
    assert template_call_kwargs['N'] == N
    assert template_call_kwargs['tag_name'] == tag_name
    if is_event:
        assert template_call_kwargs['graceid'] == obj_id
    else:
        assert template_call_kwargs['superevent_id'] == obj_id
