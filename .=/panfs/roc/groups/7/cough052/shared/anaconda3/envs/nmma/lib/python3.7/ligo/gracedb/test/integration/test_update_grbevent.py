import os
import pytest
from ligo.gracedb.exceptions import HTTPError

# Apply module-level marks
pytestmark = pytest.mark.integration


def test_update_grbevent(client, test_data_dir):
    """Test update GRB event"""
    # Setup: create a GRB event
    event_file = os.path.join(test_data_dir, 'fermi-test.xml')
    response = client.createEvent('Test', 'Fermi', event_file, search='GRB')
    assert response.status_code == 201
    initial_data = response.json()
    gid = initial_data['graceid']

    # Update the grbevent's parameters
    redshift = 3.4
    designation = 'very good'
    ra = 12.34
    try:
        response = client.update_grbevent(
            gid,
            redshift=redshift,
            designation=designation,
            ra=ra
        )
        new_data = response.json()

        # Even though they're test GRB events, unprivileged users
        # can't update GRB events. So try to catch a 200 error
        # in the case of an admin or grb user, and 403 otherwise.
        # This came up with setting up the gitlab integration instance.

        assert response.status_code == 200
        # Compare results
        initial_grb_params = initial_data['extra_attributes']['GRB']
        new_grb_params = new_data['extra_attributes']['GRB']
        assert new_grb_params['ra'] == ra
        assert new_grb_params['redshift'] == redshift
        assert new_grb_params['designation'] == designation
        assert new_grb_params['ra'] != initial_grb_params['ra']
        assert new_grb_params['redshift'] != initial_grb_params['redshift']

    except HTTPError as e:
        assert e.status_code == 403
