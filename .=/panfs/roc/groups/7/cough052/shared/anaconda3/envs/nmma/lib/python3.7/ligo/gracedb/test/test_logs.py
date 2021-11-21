try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


@pytest.mark.parametrize(
    "log_number",
    ['str', 1.23, [1], (2,), "", {'key': 'value'}]
)
def test_bad_log_number(safe_client, log_number):
    err_str = 'log_number should be an int'
    with pytest.raises(TypeError, match=err_str):
        safe_client.logs('TS121212abc', log_number=log_number)


@pytest.mark.parametrize("log_number", [None, 12])
def test_superevent_logs(safe_client, log_number):
    superevent_id = 'TS190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if log_number:
        template_key = 'superevent-log-detail-template'
    else:
        template_key = 'superevent-log-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.logs(superevent_id, log_number=log_number)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    num_kwargs = 1
    if log_number:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['superevent_id'] == superevent_id
    if log_number:
        assert template_call_kwargs['N'] == log_number


@pytest.mark.parametrize("log_number", [None, 12])
def test_event_logs(safe_client, log_number):
    graceid = 'T123456'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if log_number:
        template_key = 'event-log-detail-template'
    else:
        template_key = 'event-log-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.logs(graceid, log_number=log_number)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    num_kwargs = 1
    if log_number:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['graceid'] == graceid
    if log_number:
        assert template_call_kwargs['N'] == log_number


@pytest.mark.parametrize(
    "is_event,obj_id,tag_name,display_name",
    [
        (True, "T123456", None, None),
        (False, "TS121212abc", None, None),
        (True, "T123456", 'test', None),
        (True, "T123456", ('new_tag',), None),
        (True, "T123456", ['tag1', 'tag2'], None),
        (False, "TS121212abc", 'tag1', 'tag1_disp'),
        (False, "TS121212abc", ['tag1'], 'tag1_disp'),
        (False, "TS121212abc", set(['tag1']), set(['tag1_disp'])),
    ]
)
def test_write_log(safe_client, is_event, obj_id, tag_name, display_name):
    # Comment
    comment = 'test'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'event-log-template'
    else:
        template_key = 'superevent-log-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.writeLog(obj_id, comment, tag_name=tag_name,
                             displayName=display_name)

    # Test call to self.post
    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 2
    assert 'data' in post_call_kwargs
    assert 'files' in post_call_kwargs
    request_body = post_call_kwargs['data']
    assert request_body['comment'] == comment
    assert isinstance(request_body['tagname'], list)
    assert isinstance(request_body['displayName'], list)
    if not tag_name:
        assert request_body['tagname'] == []
    elif isinstance(tag_name, str):
        assert request_body['tagname'] == [tag_name]
    elif isinstance(tag_name, (list, tuple, set)):
        assert request_body['tagname'] == list(tag_name)
    if not display_name:
        assert request_body['displayName'] == []
    elif isinstance(display_name, str):
        assert request_body['displayName'] == [display_name]
    elif isinstance(tag_name, (list, tuple, set)):
        assert request_body['displayName'] == list(display_name)

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
    "tag_name,legacy_tagname",
    [
        (None, None),
        (None, ['test_tag']),
        (['tag1'], None),
        (['tag1'], ['tag2']),
    ]
)
def test_write_log_legacy_tagname(safe_client, tag_name, legacy_tagname):
    # Comment
    comment = 'test'

    # Set up kwargs
    method_kwargs = {}
    if tag_name:
        method_kwargs['tag_name'] = tag_name
    if legacy_tagname:
        method_kwargs['tagname'] = legacy_tagname

    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-log-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.writeLog('TS121212abc', comment, **method_kwargs)

    # Test call to self.post
    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 2
    assert 'data' in post_call_kwargs
    assert 'files' in post_call_kwargs
    request_body = post_call_kwargs['data']
    assert request_body['comment'] == comment
    if legacy_tagname and not tag_name:
        assert request_body['tagname'] == legacy_tagname
    else:
        if tag_name is None:
            tag_name = []
        assert request_body['tagname'] == tag_name


@pytest.mark.parametrize(
    "tag_name,display_name",
    [
        (None, 'tag1_disp'),
        ('tag1', ['tag1_disp1', 'tag1_disp2']),
        (['tag1', 'tag2'], 'tag1_disp'),
        (['tag1', 'tag2'], ['tag1_disp1', 'tag1_disp2', 'tag2_disp']),
    ]
)
def test_write_log_bad_tags(safe_client, tag_name, display_name):
    err_msg = ("For a list of tags, either provide no display names or a "
               "display name for each tag")
    with pytest.raises(ValueError, match=err_msg):
        safe_client.writeLog('TS121212abc', 'test', tag_name=tag_name,
                             displayName=display_name)
