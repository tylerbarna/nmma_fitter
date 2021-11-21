import pytest

# Set module-level marks
pytestmark = pytest.mark.integration


def test_ping(client):
    response = client.ping()
    assert response.status_code == 200


@pytest.mark.parametrize(
    "resource",
    ['api_versions', 'server_version', 'links', 'templates', 'groups',
     'pipelines', 'searches', 'allowed_labels', 'superevent_categories',
     'em_groups', 'voevent_types', 'signoff_types', 'signoff_statuses',
     'instruments']
)
def test_api_root_content(client, resource):
    assert getattr(client, resource) is not None
