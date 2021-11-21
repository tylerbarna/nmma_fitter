import pytest

# Apply module-level marks
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_logs(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Create a log
    comment = 'test comment'
    response = client.writeLog(obj_id, comment)
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    log_N = data['N']

    # Pull down list of logs for the event
    response = client.logs(obj_id)
    assert response.status_code == 200
    data = response.json()
    assert len(data['log']) >= 1

    # Pull down individual log
    response = client.logs(obj_id, log_N)
    assert response.status_code == 200
    data = response.json()
    assert data['comment'] == comment
    assert data['N'] == log_N


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_log_creation_with_tags(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Create a log with tags
    comment = 'test log with tags'
    tags = ['test_tag1', 'test_tag2']
    response = client.writeLog(obj_id, comment, tag_name=tags)
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    for t in tags:
        assert t in data['tag_names']


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_log_tag_and_untag(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Create a log
    comment = 'test log, add/remove tags later'
    response = client.writeLog(obj_id, comment)
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    log_N = data['N']

    # Add a tag
    tag = 'test_tag'
    response = client.addTag(obj_id, log_N, tag)
    assert response.status_code == 201

    # Get log and check tag status
    response = client.logs(obj_id, log_N)
    assert response.status_code == 200
    data = response.json()
    assert len(data['tag_names']) == 1
    assert tag in data['tag_names']

    # Remove tag
    response = client.removeTag(obj_id, log_N, tag)
    assert response.status_code == 204

    # Get log and check tag status
    response = client.logs(obj_id, log_N)
    assert response.status_code == 200
    data = response.json()
    assert len(data['tag_names']) == 0
