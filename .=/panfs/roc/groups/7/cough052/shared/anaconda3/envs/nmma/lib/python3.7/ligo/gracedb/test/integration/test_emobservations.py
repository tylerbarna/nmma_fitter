import datetime

import pytest

# Apply module-level marks
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_emobservations(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Compile EM observation data
    emgroup = client.em_groups[0]
    ra_list = [1, 2, 3, 4]
    ra_width_list = [0.5] * len(ra_list)
    dec_list = [5, 6, 7, 8]
    dec_width_list = [0.7] * len(dec_list)
    now = datetime.datetime.utcnow()
    start_time_list = list(
        map(lambda i: (now + datetime.timedelta(seconds=i)).isoformat(),
            [0, 1, 2, 3])
    )
    duration_list = [1] * len(start_time_list)
    comment = "test comment"

    # Create EM observation and check results
    response = client.writeEMObservation(
        obj_id, emgroup, ra_list, ra_width_list, dec_list, dec_width_list,
        start_time_list, duration_list, comment=comment
    )
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    assert data['group'] == emgroup
    assert len(data['footprints']) == len(ra_list)
    for emf in data['footprints']:
        N = emf['N']
        assert emf['ra'] == ra_list[N - 1]
        assert emf['dec'] == dec_list[N - 1]
        assert emf['raWidth'] == ra_width_list[N - 1]
        assert emf['decWidth'] == dec_width_list[N - 1]
        assert emf['exposure_time'] == duration_list[N - 1]
    emo_N = data['N']

    # Get list of emobservations and check results
    response = client.emobservations(obj_id)
    assert response.status_code == 200
    data = response.json()
    assert len(data['observations']) == 1
    assert data['observations'][0]['N'] == emo_N

    # Retrieve the individual emobservation directly
    response = client.emobservations(obj_id, emo_N)
    assert response.status_code == 200
    data = response.json()
    assert data['comment'] == comment
    assert data['group'] == emgroup
    assert len(data['footprints']) == len(ra_list)
    for emf in data['footprints']:
        N = emf['N']
        assert emf['ra'] == ra_list[N - 1]
        assert emf['dec'] == dec_list[N - 1]
        assert emf['raWidth'] == ra_width_list[N - 1]
        assert emf['decWidth'] == dec_width_list[N - 1]
        assert emf['exposure_time'] == duration_list[N - 1]
