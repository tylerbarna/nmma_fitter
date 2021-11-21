try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

import pytest


@pytest.mark.parametrize("voevent_number", [None, 12])
def test_superevent_voevents(safe_client, voevent_number):
    superevent_id = 'TS190302abc'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if voevent_number:
        template_key = 'superevent-voevent-detail-template'
    else:
        template_key = 'superevent-voevent-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.voevents(superevent_id, voevent_num=voevent_number)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    num_kwargs = 1
    if voevent_number:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['superevent_id'] == superevent_id
    if voevent_number:
        assert template_call_kwargs['N'] == voevent_number


@pytest.mark.parametrize("voevent_number", [None, 12])
def test_event_voevents(safe_client, voevent_number):
    graceid = 'T123456'

    # Set up templates mock
    mock_template = mock.MagicMock()
    if voevent_number:
        template_key = 'voevent-detail-template'
    else:
        template_key = 'voevent-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'
    with mock.patch('ligo.gracedb.rest.GraceDb.get') as mock_get, \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.voevents(graceid, voevent_num=voevent_number)

    get_call_args, get_call_kwargs = mock_get.call_args
    assert len(get_call_args) == 1
    assert get_call_kwargs == {}

    # Test template call kwargs
    num_kwargs = 1
    if voevent_number:
        num_kwargs += 1
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == num_kwargs
    assert template_call_kwargs['graceid'] == graceid
    if voevent_number:
        assert template_call_kwargs['N'] == voevent_number


@pytest.mark.parametrize("is_event", [True, False])
def test_create_voevent(safe_client, is_event):
    if is_event:
        obj_id = "T123456"
    else:
        obj_id = "TS121212abc"

    # Generate data
    voevent_type = 'PR'
    voevent_data = {
        'skymap_type': 'new',
        'skymap_filename': 'skymap.fits.gz',
        'internal': False,
        'open_alert': True,
        'hardware_inj': True,
        'CoincComment': False,
        'ProbHasNS': 0.6,
        'ProbHasRemnant': 0.7,
        'BNS': 0.1,
        'NSBH': 0.2,
        'BBH': 0.3,
        'Terrestrial': 0.4,
        'MassGap': 0.5,
    }

    # Set up templates mock
    mock_template = mock.MagicMock()
    if is_event:
        template_key = 'voevent-list-template'
    else:
        template_key = 'superevent-voevent-list-template'
    mock_template_dict = {template_key: mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up emgroup mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'voevent-types': {voevent_type: 'preliminary'}}

    with mock.patch('ligo.gracedb.rest.GraceDb.post') as mock_post, \
         mock.patch(si_prop, mock_si_dict), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        safe_client.createVOEvent(obj_id, voevent_type, **voevent_data)

    # Test call to self.post
    post_call_args, post_call_kwargs = mock_post.call_args
    assert len(post_call_args) == 1
    assert len(post_call_kwargs) == 1
    assert 'data' in post_call_kwargs
    request_body = post_call_kwargs['data']
    request_voevent_type = request_body.pop('voevent_type')
    assert request_voevent_type == voevent_type
    for k in voevent_data:
        assert request_body[k] == voevent_data[k]

    # Test template call kwargs
    template_call_args, template_call_kwargs = mock_template.format.call_args
    assert template_call_args == ()
    assert len(template_call_kwargs) == 1
    if is_event:
        call_key = 'graceid'
    else:
        call_key = 'superevent_id'
    assert template_call_kwargs[call_key] == obj_id


def test_create_voevent_bad_voevent_type(safe_client):
    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-voevent-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up emgroup mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'voevent-types': {'PR': 'preliminary'}}

    err_msg = "voevent_type must be one of: {vts}".format(
        vts=",'".join(list(mock_si_dict['voevent-types'].values())))
    with mock.patch(si_prop, mock_si_dict), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        with pytest.raises(ValueError, match=err_msg):
            safe_client.createVOEvent('TS121212a', 'OTHER_TYPE')


def test_create_initial_voevent_no_skymap(safe_client):
    # Set up templates mock
    mock_template = mock.MagicMock()
    mock_template_dict = {'superevent-voevent-list-template': mock_template}
    template_prop = 'ligo.gracedb.rest.GraceDb.templates'

    # Set up emgroup mock
    si_prop = 'ligo.gracedb.rest.GraceDb.service_info'
    mock_si_dict = {'voevent-types': {'IN': 'initial'}}

    err_msg = "Skymap file is required for 'initial' VOEvents"
    with mock.patch(si_prop, mock_si_dict), \
         mock.patch(template_prop, mock_template_dict):  # noqa: E127
        with pytest.raises(ValueError, match=err_msg):
            safe_client.createVOEvent('TS121212a', 'IN')
