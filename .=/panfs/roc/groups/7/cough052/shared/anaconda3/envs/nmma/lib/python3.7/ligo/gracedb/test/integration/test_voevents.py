from xml.etree import ElementTree

import pytest

# Apply module-level marks
pytestmark = pytest.mark.integration


###############################################################################
# TEST DATA ###################################################################
###############################################################################
PRELIMINARY_VOEVENT_DATA = {
    'skymap_type': None,
    'skymap_filename': None,
    'internal': True,
    'hardware_inj': False,
    'open_alert': False,
    'CoincComment': False,
    'ProbHasNS': 0.1,
    'ProbHasRemnant': 0.9,
    'BNS': 0.2,
    'NSBH': 0.3,
    'BBH': 0.4,
    'Terrestrial': 0.5,
    'MassGap': 0.6,
}

INITIAL_VOEVENT_DATA = {
    'skymap_type': 'new',
    'skymap_filename': 'fake_skymap.txt',
    'internal': True,
    'hardware_inj': False,
    'open_alert': False,
    'CoincComment': False,
    'ProbHasNS': 0.1,
    'ProbHasRemnant': 0.9,
    'BNS': 0.2,
    'NSBH': 0.3,
    'BBH': 0.4,
    'Terrestrial': 0.5,
    'MassGap': 0.6,
}


###############################################################################
# UTILITY FUNCTIONS ###########################################################
###############################################################################
def get_citations_dict(obj_id, voevent_file_text):
    # Parse XML
    xml_data = ElementTree.fromstring(voevent_file_text)
    citations_dict = {}
    for ei in xml_data.findall('./Citations/EventIVORN'):
        citations_dict[ei.text] = ei.attrib['cite']
    return citations_dict


###############################################################################
# TESTS #######################################################################
###############################################################################
@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_preliminary_voevent(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Create VOEvent and check results
    response = client.createVOEvent(obj_id, 'PR', **PRELIMINARY_VOEVENT_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data['voevent_type'] == 'PR'
    assert data['skymap_type'] == PRELIMINARY_VOEVENT_DATA['skymap_type']
    assert data['skymap_filename'] == \
        PRELIMINARY_VOEVENT_DATA['skymap_filename']
    assert data['internal'] == PRELIMINARY_VOEVENT_DATA['internal']
    assert data['hardware_inj'] == PRELIMINARY_VOEVENT_DATA['hardware_inj']
    assert data['open_alert'] == PRELIMINARY_VOEVENT_DATA['open_alert']
    assert data['coinc_comment'] == PRELIMINARY_VOEVENT_DATA['CoincComment']
    assert data['prob_has_ns'] == PRELIMINARY_VOEVENT_DATA['ProbHasNS']
    assert data['prob_has_remnant'] == \
        PRELIMINARY_VOEVENT_DATA['ProbHasRemnant']
    assert data['prob_bns'] == PRELIMINARY_VOEVENT_DATA['BNS']
    assert data['prob_nsbh'] == PRELIMINARY_VOEVENT_DATA['NSBH']
    assert data['prob_bbh'] == PRELIMINARY_VOEVENT_DATA['BBH']
    assert data['prob_terrestrial'] == PRELIMINARY_VOEVENT_DATA['Terrestrial']
    assert data['prob_mass_gap'] == PRELIMINARY_VOEVENT_DATA['MassGap']


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_initial_voevent(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Upload a fake skymap file
    response = client.writeLog(
        obj_id, "Fake skymap file",
        filename=INITIAL_VOEVENT_DATA['skymap_filename'],
        filecontents="Fake skymap."
    )
    assert response.status_code == 201

    # Create a preliminary VOEvent to update
    response = client.createVOEvent(obj_id, 'PR', **PRELIMINARY_VOEVENT_DATA)
    assert response.status_code == 201
    preliminary_data = response.json()

    # Create VOEvent and check results
    response = client.createVOEvent(obj_id, 'IN', **INITIAL_VOEVENT_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data['voevent_type'] == 'IN'
    assert data['skymap_type'] == INITIAL_VOEVENT_DATA['skymap_type']
    assert data['skymap_filename'] == INITIAL_VOEVENT_DATA['skymap_filename']
    assert data['internal'] == INITIAL_VOEVENT_DATA['internal']
    assert data['hardware_inj'] == INITIAL_VOEVENT_DATA['hardware_inj']
    assert data['open_alert'] == INITIAL_VOEVENT_DATA['open_alert']
    assert data['coinc_comment'] == INITIAL_VOEVENT_DATA['CoincComment']
    assert data['prob_has_ns'] == INITIAL_VOEVENT_DATA['ProbHasNS']
    assert data['prob_has_remnant'] == INITIAL_VOEVENT_DATA['ProbHasRemnant']
    assert data['prob_bns'] == INITIAL_VOEVENT_DATA['BNS']
    assert data['prob_nsbh'] == INITIAL_VOEVENT_DATA['NSBH']
    assert data['prob_bbh'] == INITIAL_VOEVENT_DATA['BBH']
    assert data['prob_terrestrial'] == INITIAL_VOEVENT_DATA['Terrestrial']
    assert data['prob_mass_gap'] == INITIAL_VOEVENT_DATA['MassGap']

    # Check citations
    response = client.files(obj_id, data['filename'])
    assert response.status_code == 200
    voevent_file_text = response.read()
    citations_dict = get_citations_dict(obj_id, voevent_file_text)
    assert len(citations_dict) == 1
    assert preliminary_data['ivorn'] in citations_dict
    assert citations_dict[preliminary_data['ivorn']] == 'supersedes'


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_update_voevent(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Upload a fake skymap file
    response = client.writeLog(
        obj_id, "Fake skymap file",
        filename=INITIAL_VOEVENT_DATA['skymap_filename'],
        filecontents="Fake skymap."
    )
    assert response.status_code == 201

    # Create a preliminary VOEvent to update
    response = client.createVOEvent(obj_id, 'PR', **PRELIMINARY_VOEVENT_DATA)
    assert response.status_code == 201
    preliminary_data = response.json()

    # Create an initial VOEvent to update
    response = client.createVOEvent(obj_id, 'IN', **INITIAL_VOEVENT_DATA)
    assert response.status_code == 201
    initial_data = response.json()

    # Create VOEvent and check results
    response = client.createVOEvent(obj_id, 'UP', **INITIAL_VOEVENT_DATA)
    assert response.status_code == 201
    data = response.json()
    assert data['voevent_type'] == 'UP'
    assert data['skymap_type'] == INITIAL_VOEVENT_DATA['skymap_type']
    assert data['skymap_filename'] == INITIAL_VOEVENT_DATA['skymap_filename']
    assert data['internal'] == INITIAL_VOEVENT_DATA['internal']
    assert data['hardware_inj'] == INITIAL_VOEVENT_DATA['hardware_inj']
    assert data['open_alert'] == INITIAL_VOEVENT_DATA['open_alert']
    assert data['coinc_comment'] == INITIAL_VOEVENT_DATA['CoincComment']
    assert data['prob_has_ns'] == INITIAL_VOEVENT_DATA['ProbHasNS']
    assert data['prob_has_remnant'] == INITIAL_VOEVENT_DATA['ProbHasRemnant']
    assert data['prob_bns'] == INITIAL_VOEVENT_DATA['BNS']
    assert data['prob_nsbh'] == INITIAL_VOEVENT_DATA['NSBH']
    assert data['prob_bbh'] == INITIAL_VOEVENT_DATA['BBH']
    assert data['prob_terrestrial'] == INITIAL_VOEVENT_DATA['Terrestrial']
    assert data['prob_mass_gap'] == INITIAL_VOEVENT_DATA['MassGap']

    # Check citations
    response = client.files(obj_id, data['filename'])
    assert response.status_code == 200
    voevent_file_text = response.read()
    citations_dict = get_citations_dict(obj_id, voevent_file_text)
    assert len(citations_dict) == 2
    assert preliminary_data['ivorn'] in citations_dict
    assert initial_data['ivorn'] in citations_dict
    assert citations_dict[preliminary_data['ivorn']] == 'supersedes'
    assert citations_dict[initial_data['ivorn']] == 'supersedes'


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_retraction_voevent(client, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Upload a fake skymap file
    response = client.writeLog(
        obj_id, "Fake skymap file",
        filename=INITIAL_VOEVENT_DATA['skymap_filename'],
        filecontents="Fake skymap."
    )
    assert response.status_code == 201

    # Create a preliminary VOEvent to retract
    response = client.createVOEvent(obj_id, 'PR', **PRELIMINARY_VOEVENT_DATA)
    assert response.status_code == 201
    preliminary_data = response.json()

    # Create a retraction VOEvent
    response = client.createVOEvent(obj_id, 'RE')
    assert response.status_code == 201
    retraction_data = response.json()
    assert retraction_data['voevent_type'] == 'RE'

    # Check citations
    response = client.files(obj_id, retraction_data['filename'])
    assert response.status_code == 200
    voevent_file_text = response.read()
    citations_dict = get_citations_dict(obj_id, voevent_file_text)
    assert len(citations_dict) == 1
    assert preliminary_data['ivorn'] in citations_dict
    assert citations_dict[preliminary_data['ivorn']] == 'retraction'
