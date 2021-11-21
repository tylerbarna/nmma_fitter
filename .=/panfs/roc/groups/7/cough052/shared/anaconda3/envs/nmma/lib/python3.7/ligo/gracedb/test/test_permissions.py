try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


def test_get_superevent_permissions(safe_client):
    superevent_id = 'TS190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-permission-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.permissions(superevent_id)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs['superevent_id'] == superevent_id


def test_get_event_permissions(safe_client):
    graceid = 'T123456'

    err_msg = 'Not implemented for events'
    with pytest.raises(NotImplementedError, match=err_msg):
        safe_client.permissions(graceid)


@pytest.mark.parametrize("action", ['expose', 'hide'])
def test_modify_superevent_permissions(safe_client, action):
    superevent_id = 'TS121212a'

    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = \
        {'superevent-permission-modify-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.modify_permissions(superevent_id, action)

    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 1
    assert 'data' in post_call_kwargs
    assert post_call_kwargs['data'] == {'action': action}

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    assert template_call_kwargs['superevent_id'] == superevent_id


@pytest.mark.parametrize("action", ['expose', 'hide'])
def test_modify_event_permissions(safe_client, action):
    graceid = 'T123456'
    err_msg = 'Not implemented for events'
    with pytest.raises(NotImplementedError, match=err_msg):
        safe_client.modify_permissions(graceid, action)


@pytest.mark.parametrize("action", ['other', 1, 3.4, False, (), ['hide']])
def test_modify_permissions_bad_action(safe_client, action):
    superevent_id = 'TS121212abc'
    err_msg = "action should be 'expose' or 'hide'"
    with pytest.raises(ValueError, match=err_msg):
        safe_client.modify_permissions(superevent_id, action)
