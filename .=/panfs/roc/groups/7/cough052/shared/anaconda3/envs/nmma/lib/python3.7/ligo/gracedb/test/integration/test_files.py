import os

import pytest

# Apply module-level marks
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_file_upload_and_retrieval(client, test_data_dir, create_obj,
                                   obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Create a log with a file upload
    comment = 'test file upload'
    test_file = os.path.join(test_data_dir, 'test_file.txt')
    response = client.writeLog(obj_id, comment, filename=test_file)
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    assert data['filename'] == os.path.basename(test_file)

    # Check file list for obj
    response = client.files(obj_id)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    # Download the file and compare it
    response = client.files(obj_id, os.path.basename(test_file))
    assert response.status_code == 200
    file_from_server = response.read()
    with open(test_file, 'rb') as f:
        file_from_disk = f.read()
    assert file_from_server == file_from_disk


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_upload_file_multiple_versions(client, test_data_dir, create_obj,
                                       obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Create a log with a file upload
    file_name = 'new_file_test.txt'
    comment = 'test file upload'
    fc1 = 'file 1 data'
    response = client.writeLog(obj_id, comment, filename=file_name,
                               filecontents=fc1)
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    assert data['filename'] == file_name
    assert data['file_version'] == 0

    # Create another log using the same file name
    fc2 = 'file 2 data'
    response = client.writeLog(obj_id, comment, filename=file_name,
                               filecontents=fc2)
    assert response.status_code == 201
    data = response.json()
    assert data['comment'] == comment
    assert data['filename'] == file_name
    assert data['file_version'] == 1

    # Check the attached files
    response = client.files(obj_id)
    assert response.status_code == 200
    data = response.json()
    # There should be at least the two files we uploaded and the symlink to
    # the latest one.
    assert len(data) >= 3
    for version in ['', ',0', ',1']:
        assert (file_name + version) in data

    # Download all files and compare the contents
    file1_data = client.files(obj_id, file_name + ',0').read()
    file2_data = client.files(obj_id, file_name + ',1').read()
    file_data = client.files(obj_id, file_name).read()
    assert file1_data.decode() == fc1
    assert file2_data.decode() == fc2
    assert file2_data == file_data
    assert file1_data != file2_data


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_upload_large_file(client, test_data_dir, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Upload a large file (2 MB)
    filename = os.path.join(test_data_dir, 'big.data')
    response = client.writeLog(obj_id, "Large file upload test",
                               filename=filename)
    assert response.status_code == 201
    data = response.json()
    assert data['filename'] == os.path.basename(filename)

    # Download file and compare to file on disk
    # Download the file and compare it
    response = client.files(obj_id, os.path.basename(filename))
    assert response.status_code == 200
    file_from_server = response.read()
    with open(filename, 'rb') as f:
        file_from_disk = f.read()
    assert file_from_server == file_from_disk


@pytest.mark.parametrize("obj_type", ['event', 'superevent'])
def test_upload_binary_file(client, test_data_dir, create_obj, obj_type):
    # Create event or superevent
    obj, obj_id = create_obj(obj_type)

    # Upload a binary file
    filename = os.path.join(test_data_dir, 'upload.data.gz')
    response = client.writeLog(obj_id, "Binary file upload test",
                               filename=filename)
    assert response.status_code == 201
    data = response.json()
    assert data['filename'] == os.path.basename(filename)
