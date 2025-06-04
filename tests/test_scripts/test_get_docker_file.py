from ubuntu_utils.scripts.lib.get_docker_file import copy_from_image


def test_copy_from_image(tmp_path):
    copy_from_image("ubuntu:22.04", "/root", tmp_path)
    assert (tmp_path / "root/.bashrc").exists()
    assert (tmp_path / "root/.profile").exists()
