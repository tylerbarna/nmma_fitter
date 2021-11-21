import pytest

# Apply module-level mark
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_labels(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Add a label
    label1 = 'DQV'
    response = client.writeLabel(obj_id, label1)
    assert response.status_code == 201
    data = response.json()
    # NOTE: events API returns empty response - should be fixed
    if obj_type == 'superevent':
        assert data['name'] == label1
    elif obj_type == 'event':
        assert data == '{}'

    # Add another label
    label2 = 'INJ'
    response = client.writeLabel(obj_id, label2)
    assert response.status_code == 201
    data = response.json()
    # NOTE: events API returns empty response - should be fixed
    if obj_type == 'superevent':
        assert data['name'] == label2
    elif obj_type == 'event':
        assert data == '{}'

    # Get list of labels
    response = client.labels(obj_id)
    assert response.status_code == 200
    data = response.json()
    obj_labels = [l['name'] for l in data['labels']]
    assert len(obj_labels) == 2
    assert label1 in obj_labels
    assert label2 in obj_labels

    # Pull down an individual label
    response = client.labels(obj_id, label2)
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == label2

    # Remove a label
    response = client.removeLabel(obj_id, label1)
    assert response.status_code == 204

    # Get event and double check
    if obj_type == 'event':
        method = 'event'
    elif obj_type == 'superevent':
        method = 'superevent'
    response = getattr(client, method)(obj_id)
    assert response.status_code == 200
    data = response.json()
    assert len(data['labels']) == 1
    assert label1 not in data['labels']
    assert label2 in data['labels']
