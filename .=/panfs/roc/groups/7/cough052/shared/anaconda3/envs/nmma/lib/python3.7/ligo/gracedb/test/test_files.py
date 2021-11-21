try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import os

import pytest


@pytest.mark.parametrize("filename", ['file.txt', "", None])
def test_superevent_files(safe_client, filename):
    superevent_id = 'S190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if filename:
        template_key = 'superevent-file-detail-template'
    else:
        template_key = 'superevent-file-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.files(superevent_id, filename=filename)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    if filename:
        stream_args = {'stream': True}
    else:
        stream_args = {}
    assert get_call_kwargs == stream_args

    # Test template call kwargs
    num_kwargs = 1
    if filename:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['superevent_id'] == superevent_id
    if filename:
        assert template_call_kwargs['file_name'] == filename


@pytest.mark.parametrize("filename", ['file.txt', "", None])
def test_event_files(safe_client, filename):
    graceid = 'T123456'

    # Set up templates mock
    mock_template = mock.MagicMock()
    template_key = 'files-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.files(graceid, filename=filename)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    if filename:
        stream_args = {'stream': True}
    else:
        stream_args = {}
    assert get_call_kwargs == stream_args

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 2
    assert template_call_kwargs['graceid'] == graceid
    if not filename:
        filename = ""
    assert template_call_kwargs['filename'] == filename


@pytest.mark.parametrize(
    "filename,filecontents",
    [
        ('file.txt', None),
        ('subdir1/subdir2/file.txt', None),
        ('-', None),
        ('file.txt', 'fc1'),
        ('subdir1/subdir2/file.txt', 'fc2'),
        ('-', 'fc3'),
    ]
)
def test_write_log_with_file(safe_client, filename, filecontents):
    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-log-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up mock open
    open_func = 'ligo.gracedb.rest.open'
    mock_data = 'fake data'
    open_mocker = mock.mock_open(read_data=mock_data)

    # Set up mock sys.stdin.read
    stdin_obj = 'ligo.gracedb.rest.sys.stdin'
    mock_stdin_data = 'fake stdin data'

    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(open_func, open_mocker), \
         mock.patch(stdin_obj) as mock_stdin, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127

        mock_stdin.read.return_value = mock_stdin_data
        safe_client.writeLog('TS121212a', 'test', filename=filename,
                             filecontents=filecontents)

    # Test call to self.post
    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 2
    assert 'data' in post_call_kwargs
    assert 'files' in post_call_kwargs

    # Test file contents
    post_files = post_call_kwargs['files']
    assert len(post_files) == 1
    assert 'upload' in post_files
    post_files = post_files['upload']
    if filecontents is None:
        if filename == '-':
            assert post_files[0] == 'stdin'
            assert post_files[1] == mock_stdin_data
        else:
            assert post_files[0] == os.path.basename(filename)
            assert post_files[1] == open_mocker()
    else:
        assert post_files[0] == os.path.basename(filename)
        assert post_files[1] == filecontents


def test_write_log_with_filecontents_handler(safe_client):
    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-log-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up mock filecontents
    filename = 'file.txt'
    filecontents = mock.MagicMock()
    mock_data = 'more fake data'
    filecontents.read.return_value = mock_data

    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127

        safe_client.writeLog('TS121212a', 'test', filename=filename,
                             filecontents=filecontents)

    # Test call to self.post
    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 2
    assert 'data' in post_call_kwargs
    assert 'files' in post_call_kwargs

    # Test file contents
    post_files = post_call_kwargs['files']
    assert len(post_files) == 1
    assert 'upload' in post_files
    post_files = post_files['upload']
    assert post_files[0] == os.path.basename(filename)
    assert post_files[1] == filecontents
    assert post_files[2] == 'text/plain'
