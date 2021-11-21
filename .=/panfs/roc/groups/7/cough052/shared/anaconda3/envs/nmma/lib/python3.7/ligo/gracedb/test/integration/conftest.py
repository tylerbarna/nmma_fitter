import os

import pytest

from ligo.gracedb.rest import GraceDb


@pytest.fixture
def client():
    """A full client instance for use in integration tests"""
    service_url = os.environ.get(
        'TEST_SERVICE',
        'https://gracedb-test.ligo.org/api/'
    )
    return GraceDb(service_url=service_url)


@pytest.fixture
def test_data_dir():
    d = os.environ.get(
        'TEST_DATA_DIR',
        os.path.join(os.path.dirname(__file__), 'data')
    )
    return d


@pytest.fixture
def create_event(client, test_data_dir):
    def _inner(pipeline='gstlal', search='LowMass',
               filename=os.path.join(test_data_dir, 'cbc-lm.xml')):
        response = client.createEvent('Test', pipeline, filename,
                                      search=search)
        return response.json()
    return _inner


@pytest.fixture
def create_superevent(client, test_data_dir, create_event):
    def _inner(
        pipeline='gstlal', search='LowMass',
        filename=os.path.join(test_data_dir, 'cbc-lm.xml'),
        t_start=1, t_0=2, t_end=3
    ):
        event = create_event(pipeline=pipeline, search=search,
                             filename=filename)
        response = client.createSuperevent(t_start, t_0, t_end,
                                           event['graceid'], category='T')
        return response.json()
    return _inner


@pytest.fixture
def create_obj(client, test_data_dir, create_event, create_superevent):
    def _inner(
        obj_type='event', pipeline='gstlal', search='LowMass',
        filename=os.path.join(test_data_dir, 'cbc-lm.xml'),
        t_start=1, t_0=2, t_end=3
    ):
        event = create_event(pipeline=pipeline, search=search,
                             filename=filename)
        if obj_type == 'superevent':
            response = client.createSuperevent(t_start, t_0, t_end,
                                               event['graceid'], category='T')
            obj = response.json()
            obj_id = obj['superevent_id']
        elif obj_type == 'event':
            obj = event
            obj_id = event['graceid']
        else:
            raise ValueError("obj_type must be 'event' or 'superevent'")
        return obj, obj_id
    return _inner
