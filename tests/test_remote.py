import hashlib
from pathlib import Path, PosixPath

import pytest

from tests.conftest import RC_DIR
from ubuntu_utils.framework.lib.network_utils import find_free_port
from ubuntu_utils.framework.remote import FileServer, Remote


# Fixture to set up and tear down the FileServer and Remote instance
@pytest.fixture()
def remote_fixture():
    port = find_free_port("127.0.0.1")
    FileServer.RC_DIR = RC_DIR
    FileServer.PORT = port
    print(1)
    file_server = FileServer()
    file_server.start()
    print(1)
    Remote.PORT = port
    remote = Remote()

    # Yield Remote instance to the test
    yield remote

    file_server.close()


# Utility: Compute hash of a file using the given algorithm (default: sha256)
def calculate_file_hash(file_path, algorithm="sha256"):
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 32):
            hash_func.update(chunk)
    return hash_func.hexdigest()


# Utility: Compare two files by their hash to determine if they are identical
def are_files_identical(file1, file2):
    return calculate_file_hash(file1) == calculate_file_hash(file2)


# Test downloading a single file using Remote.get_file
def test_get_file(remote_fixture):
    print(1)
    grub_dst_path = Path("/tmp/grub")
    grub_dst_path.unlink(missing_ok=True)  # Remove the file if it already exists

    # Fetch the file from the server and verify its content and path
    dst_path = remote_fixture.get_file("grub")
    assert dst_path == grub_dst_path
    assert are_files_identical(RC_DIR / "grub", dst_path)

    # If LOCAL_DIR is set, it should use the local path directly
    Remote.LOCAL_DIR = RC_DIR
    dst_path = remote_fixture.get_file("grub")
    assert dst_path == Path(__file__).parent / "resources/grub"


# Test listing all available file paths from the root
def test_get_file_paths(remote_fixture):
    file_paths = remote_fixture.get_file_paths("")
    assert file_paths == [
        PosixPath("grub"),
        PosixPath("commands.py"),
        PosixPath("commands2.py"),
        PosixPath("grub-modified"),
    ]
