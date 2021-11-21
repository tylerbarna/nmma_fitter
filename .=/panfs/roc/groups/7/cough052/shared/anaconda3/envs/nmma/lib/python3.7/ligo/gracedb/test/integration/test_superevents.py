import pytest
from ligo.gracedb.exceptions import HTTPError

# Apply module-level mark
pytestmark = pytest.mark.integration


def test_basic_creation_and_retrieval(client, create_event):
    event = create_event()
    response = client.createSuperevent(1, 2, 3, event['graceid'], category='T')
    assert response.status_code == 201
    data = response.json()
    assert data['preferred_event'] == event['graceid']
    assert data['t_start'] == 1
    assert data['t_0'] == 2
    assert data['t_end'] == 3
    assert data['category'] == 'Test'

    response = client.superevent(data['superevent_id'])
    assert response.status_code == 200
    data = response.json()
    assert data['preferred_event'] == event['graceid']
    assert data['t_start'] == 1
    assert data['t_0'] == 2
    assert data['t_end'] == 3
    assert data['category'] == 'Test'


def test_creation_with_already_used_preferred_event(client, create_event):
    event = create_event()
    response = client.createSuperevent(1, 2, 3, event['graceid'], category='T')
    assert response.status_code == 201
    data = response.json()
    assert data['preferred_event'] == event['graceid']
    assert data['t_start'] == 1
    assert data['t_0'] == 2
    assert data['t_end'] == 3
    assert data['category'] == 'Test'

    # Try to create new superevent with an existing
    # preferred event:
    with pytest.raises(HTTPError):
        response = client.createSuperevent(1, 2, 3, event, category='T')


def test_creation_with_events(client, create_event):
    event1 = create_event()
    event2 = create_event()
    event3 = create_event()
    response = client.createSuperevent(
        1, 2, 3, event1['graceid'], category='T',
        events=[event2['graceid'], event3['graceid']]
    )
    assert response.status_code == 201
    data = response.json()
    assert data['preferred_event'] == event1['graceid']
    assert data['t_start'] == 1
    assert data['t_0'] == 2
    assert data['t_end'] == 3
    assert data['category'] == 'Test'
    assert len(data['gw_events']) == 3
    for ev in [event1, event2, event3]:
        assert ev['graceid'] in data['gw_events']


def test_creation_with_labels(client, create_event):
    labels = ['INJ', 'DQV']
    event = create_event()
    response = client.createSuperevent(1, 2, 3, event['graceid'], category='T',
                                       labels=labels)
    assert response.status_code == 201
    data = response.json()
    assert data['preferred_event'] == event['graceid']
    assert data['t_start'] == 1
    assert data['t_0'] == 2
    assert data['t_end'] == 3
    assert data['category'] == 'Test'
    assert len(data['labels']) == len(labels)
    for l in labels:
        assert l in data['labels']


@pytest.mark.parametrize(
    "params",
    [
        {'t_0': 3463},
        {'t_start': 208, 't_end': 28992},
        {'preferred_event': True},
        {'t_start': 972, 't_0': 1028, 't_end': 1098, 'preferred_event': True},
        {'t_start': 972, 't_0': 1028, 't_end': 1098, 'preferred_event': True},
        {'t_start': 1024, 't_0': 2048, 't_end': 4096, 'preferred_event': True,
         'em_type': 'EM_TYPE_TEST'},
        {'t_start': 1025, 't_0': 2049, 't_end': 4097, 'preferred_event': True,
         'em_type': 'EM_TYPE_TEST', 'time_coinc_far': 1234.0},
        {'t_start': 1025, 't_0': 2049, 't_end': 4097, 'preferred_event': True,
         'em_type': 'EM_TYPE_TEST', 'time_coinc_far': 1234.0,
         'space_coinc_far': 12345.0},
    ]
)
def test_update(client, create_event, create_superevent, params):
    # Create a superevent
    superevent = create_superevent()

    # Create a new event if we're going to change the preferred_event
    if 'preferred_event' in params:
        event = create_event()
        params['preferred_event'] = event['graceid']

    # Update the superevent
    response = client.updateSuperevent(superevent['superevent_id'], **params)

    # Check results
    assert response.status_code == 200
    data = response.json()
    for p in params:
        assert data[p] == params[p]

    # Check that old preferred event is still in the superevent's events
    if 'preferred_event' in params:
        assert len(data['gw_events']) == 2
        assert event['graceid'] in data['gw_events']


def test_event_addition_and_removal(client, create_event, create_superevent):
    # Create superevent and another event
    superevent = create_superevent()
    new_event = create_event()

    # Add new event to superevent
    response = client.addEventToSuperevent(superevent['superevent_id'],
                                           new_event['graceid'])

    # Check results
    assert response.status_code == 201
    data = response.json()
    assert data['graceid'] == new_event['graceid']

    # Pull down superevent and check results
    response = client.superevent(superevent['superevent_id'])
    assert response.status_code == 200
    data = response.json()
    # Preferred event didn't change
    assert data['preferred_event'] == superevent['preferred_event']
    # Both events are in list
    assert len(data['gw_events']) == 2
    assert superevent['preferred_event'] in data['gw_events']
    assert new_event['graceid'] in data['gw_events']

    # Remove event
    response = client.removeEventFromSuperevent(superevent['superevent_id'],
                                                new_event['graceid'])
    assert response.status_code == 204

    # Pull down superevent and check results
    response = client.superevent(superevent['superevent_id'])
    assert response.status_code == 200
    data = response.json()
    # Preferred event didn't change
    assert data['preferred_event'] == superevent['preferred_event']
    # Only one event in list
    assert len(data['gw_events']) == 1
    assert superevent['preferred_event'] in data['gw_events']
    assert new_event['graceid'] not in data['gw_events']

    # Try remove event again, should get error
    with pytest.raises(HTTPError):
        client.removeEventFromSuperevent(
            superevent['superevent_id'], new_event['graceid']
        )

    # Try remove preferred event, should get error
    with pytest.raises(HTTPError):
        client.removeEventFromSuperevent(
            superevent['superevent_id'], superevent['preferred_event']
        )


def test_confirm_as_gw(client, create_superevent):
    # Create superevent
    superevent = create_superevent()

    # Check its status
    assert superevent['gw_id'] is None
    assert not superevent['superevent_id'].startswith('TGW')
    assert 'GW' not in superevent['superevent_id'][:3]

    # Confirm it as a GW
    response = client.confirm_superevent_as_gw(superevent['superevent_id'])
    assert response.status_code == 200
    data = response.json()
    gw_id = data['gw_id']
    assert gw_id.startswith('TGW') or 'GW' in gw_id[:3]

    # Try to update again
    with pytest.raises(HTTPError):
        client.confirm_superevent_as_gw(superevent['superevent_id'])

    # Test getting data using both IDs
    response = client.superevent(superevent['superevent_id'])
    assert response.status_code == 200
    s_id_data = response.json()
    response = client.superevent(gw_id)
    assert response.status_code == 200
    gw_id_data = response.json()
    for k in s_id_data:
        assert s_id_data[k] == gw_id_data[k]


def test_search(client, create_superevent):
    # Create a superevent
    superevent = create_superevent()

    # Search by ID
    response = client.superevents(superevent['superevent_id'])
    results_list = list(response)
    assert len(results_list) == 1
    assert results_list[0]['superevent_id'] == superevent['superevent_id']
