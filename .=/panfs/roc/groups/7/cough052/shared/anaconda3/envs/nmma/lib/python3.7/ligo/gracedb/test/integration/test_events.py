import os

import pytest


# Apply module-level mark
pytestmark = pytest.mark.integration


def test_create_gstlal(client, test_data_dir):
    # Create gstlal event
    filename = os.path.join(test_data_dir, 'cbc-lm.xml')
    response = client.createEvent('Test', 'gstlal', filename)
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'gstlal'
    assert data['gpstime'] == 971609248.151741
    assert data['extra_attributes']['CoincInspiral']['snr'] == 9.31793628458239


def test_create_gstlal_with_missing_table_entry(client, test_data_dir):
    # Create gstlal event, with a missing snglinspiral table
    # entry. The event should get made and the table populated with
    # a None entry.
    filename = os.path.join(test_data_dir, 'cbc-lm-missing-entry.xml')
    response = client.createEvent('Test', 'gstlal', filename)
    assert response.status_code == 201
    data = response.json()

    # Make sure warnings are empty:
    assert data['warnings'] == []

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'gstlal'
    assert data['gpstime'] == 971609248.151741
    assert data['extra_attributes']['CoincInspiral']['snr'] == 9.31793628458239

    # Extra results. Assert that the snr snglinspiral table entry is empty
    assert data['extra_attributes']['SingleInspiral'][0].get('snr') is None


def test_create_gstlal_no_ilwdchar(client, test_data_dir):
    # Create gstlal event, where the ligol ilwd:char entries
    # have been replaced with int8's.
    filename = os.path.join(test_data_dir, 'cbc-lm-no-ilwdchar.xml')
    response = client.createEvent('Test', 'gstlal', filename)
    assert response.status_code == 201
    data = response.json()

    # Make sure warnings are empty:
    assert data['warnings'] == []

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'gstlal'
    assert data['gpstime'] == 971609248.151741
    # Also, this assert will fail if the event is not read correctly:
    assert data['extra_attributes']['CoincInspiral']['snr'] == 9.31793628458239


@pytest.mark.xfail
def test_create_pycbc(client, test_data_dir):
    # Create PyCBC event - need to get a PyCBC data file and clean it up,
    # but the files are very large, so this would be quite an undertaking
    raise NotImplementedError()


def test_create_mbta(client, test_data_dir):
    # Create MBTA event
    filename = os.path.join(test_data_dir, 'cbc-mbta.xml')
    response = client.createEvent('Test', 'MBTAOnline', filename)
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'MBTAOnline'
    assert data['gpstime'] == 1078903329.421037
    assert data['extra_attributes']['CoincInspiral']['mass'] == \
        2.963776448988085


def test_create_spiir(client, test_data_dir):
    # Create SPIIR event
    filename = os.path.join(test_data_dir, 'spiir-test.xml')
    response = client.createEvent('Test', 'spiir', filename)
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert response.status_code == 201
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'spiir'
    assert data['extra_attributes']['CoincInspiral']['mass'] == 3.98
    assert data['far'] == 3.27e-07


def test_create_spiir_no_ilwdchar(client, test_data_dir):
    # Create SPIIR event, with ilwd:char entires converted to int8s
    filename = os.path.join(test_data_dir, 'spiir-test-no-ilwdchar.xml')
    response = client.createEvent('Test', 'spiir', filename)
    assert response.status_code == 201
    data = response.json()

    # Make sure warnings are empty:
    assert data['warnings'] == []

    # Test results
    assert response.status_code == 201
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'spiir'
    assert data['extra_attributes']['CoincInspiral']['mass'] == 3.98
    assert data['far'] == 3.27e-07


def test_create_cwb(client, test_data_dir):
    # Create CWB event
    filename = os.path.join(test_data_dir, 'burst-cwb.txt')
    response = client.createEvent('Test', 'CWB', filename)
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'CWB'
    assert data['far'] == 0.00019265
    assert data['extra_attributes']['MultiBurst']['amplitude'] == 5.017162


def test_create_olib(client, test_data_dir):
    # Create oLIB event
    filename = os.path.join(test_data_dir, 'olib-test.json')
    response = client.createEvent('Test', 'oLIB', filename)
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'oLIB'
    assert data['far'] == 7.22e-06
    assert data['extra_attributes']['LalInferenceBurst']['bci'] == 1.111
    assert data['extra_attributes']['LalInferenceBurst']['bsn'] == 7.19


def test_create_hardwareinjection(client, test_data_dir):
    # Create hardware injection event
    inst = 'H1'
    filename = os.path.join(test_data_dir, 'sim-inj.xml')
    response = client.createEvent(
        'Test', 'HardwareInjection', filename, instrument=inst,
        source_channel="", destination_channel=""
    )
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'HardwareInjection'
    assert data['instruments'] == inst


def test_create_external(client, test_data_dir):
    # Create external GRB event
    filename = os.path.join(test_data_dir, 'fermi-test.xml')
    response = client.createEvent('Test', 'Fermi', filename, search='GRB')
    assert response.status_code == 201
    data = response.json()

    # Test results
    assert data['group'] == 'Test'
    assert data['pipeline'] == 'Fermi'
    assert data['extra_attributes']['GRB']['error_radius'] == 8.8374
    assert data['extra_attributes']['GRB']['ra'] == 345.99


@pytest.mark.parametrize("offline", [True, False])
def test_creation_with_offline(client, test_data_dir, offline):
    filename = os.path.join(test_data_dir, 'cbc-lm.xml')
    response = client.createEvent('Test', 'gstlal', filename, offline=offline)
    assert response.status_code == 201
    data = response.json()
    assert data['offline'] == offline


def test_creation_with_labels(client, test_data_dir):
    labels = ['INJ', 'DQV']
    filename = os.path.join(test_data_dir, 'cbc-lm.xml')
    response = client.createEvent('Test', 'gstlal', filename, labels=labels)
    assert response.status_code == 201
    data = response.json()
    assert len(data['labels']) == len(labels)
    for l in labels:
        assert l in data['labels']


def test_replace_event(client, test_data_dir):
    # Create an event
    filename = os.path.join(test_data_dir, 'cbc-lm.xml')
    response = client.createEvent('Test', 'gstlal', filename)
    assert response.status_code == 201
    data1 = response.json()
    graceid = data1['graceid']

    # Check gpstime
    assert data1['gpstime'] == 971609248.151741

    # Replace it
    new_data_file = os.path.join(test_data_dir, 'cbc-lm2.xml')
    response = client.replaceEvent(graceid, new_data_file)
    assert response.status_code == 202

    # Get event data and check that gpstime has changed
    response = client.event(graceid)
    assert response.status_code == 200
    data2 = response.json()
    assert data2['gpstime'] == 971609249.151741


def test_get_event(client, test_data_dir):
    # Create gstlal event
    filename = os.path.join(test_data_dir, 'cbc-lm.xml')
    response = client.createEvent('Test', 'gstlal', filename)
    assert response.status_code == 201
    data1 = response.json()
    graceid = data1['graceid']

    # Get event and compare
    response = client.event(graceid)
    assert response.status_code == 200
    data2 = response.json()
    for k in data2:
        assert data1[k] == data2[k]


def test_search(client, create_event):
    # Create an event
    event = create_event()

    # Search by ID
    response = client.events(event['graceid'])
    results_list = list(response)
    assert len(results_list) == 1
    assert results_list[0]['graceid'] == event['graceid']
