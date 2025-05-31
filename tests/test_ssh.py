import socket
import tempfile
import time
from pathlib import Path

import docker
import docker.errors
import paramiko
import pytest

from ubuntu_utils.framework.ssh import SSH


@pytest.fixture()
def ssh_test_container():
    client = docker.from_env()

    # Remove existing container if it already exists
    try:
        existing = client.containers.get("ssh-test-container")
        existing.remove(force=True)
    except docker.errors.NotFound:
        pass

    # Build the Docker image from the current directory
    image, _ = client.images.build(
        path=Path(__file__).parent.__str__(), tag="ssh-test-image"
    )

    # Run the container with SSH port exposed
    container = client.containers.run(
        image="ssh-test-image",
        name="ssh-test-container",
        ports={"22/tcp": 2222},
        detach=True,
    )

    # Wait until the SSH server is available
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", 2222), timeout=1):
                break
        except OSError:
            time.sleep(1)
    else:
        container.remove(force=True)
        raise RuntimeError("SSH server is not ready")

    # Yield connection details to the test
    yield {
        "host": "127.0.0.1",
        "port": 2222,
        "username": "testuser",
        "password": "testpass",
        "container": container,
    }

    # Clean up the container after the test
    container.remove(force=True)


def test_put_and_get_file(ssh_test_container):
    # Try connecting to the SSH server with retries
    for _ in range(20):
        try:
            ssh = SSH(
                host=ssh_test_container["host"],
                port=ssh_test_container["port"],
                username=ssh_test_container["username"],
                password=ssh_test_container["password"],
            )
            break
        except paramiko.ssh_exception.SSHException:
            time.sleep(1)
    else:
        ssh_test_container["container"].remove(force=True)
        raise RuntimeError("SSH connection failed after multiple attempts")

    # Create local temporary directories for upload and download
    with (
        tempfile.TemporaryDirectory() as local_dir,
        tempfile.TemporaryDirectory() as download_dir,
    ):
        test_file = Path(local_dir) / "hello.txt"
        content = "Hello pytest + docker"
        test_file.write_text(content)

        # Upload the test file to the remote container
        ssh.put(local_dir, "/home/testuser/test_upload")

        # Run a remote command to confirm the upload
        ssh.exec_command("ls -l /home/testuser/test_upload")

        # Download the uploaded file back to a local directory
        ssh.get("/home/testuser/test_upload", Path(download_dir))

        # Validate that the downloaded file exists and matches the original content
        downloaded_file = Path(download_dir) / "test_upload/hello.txt"
        assert downloaded_file.exists()
        assert downloaded_file.read_text() == content

    ssh.close()
