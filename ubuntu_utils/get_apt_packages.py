from pathlib import Path

import configs

from ubuntu_utils.framework.lib.serialization_utils import Serializer
from ubuntu_utils.framework.settings import Settings
from ubuntu_utils.framework.ssh import SSH


def get_apt_packages(packages: list[str]):
    remote_path = f"/home/{configs.TEST_USER}/ubuntu_utils"
    s = SSH(configs.TEST_HOST, configs.TEST_USER, configs.TEST_PASSWORD)
    s.exec_command(f"mkdir -p {remote_path}/files/apt_offline")
    s.exec_command("sudo apt update", auto_pw=True)
    s.exec_command("sudo apt install -y apt-offline", auto_pw=True)
    s.exec_command(
        f"sudo {remote_path}/ubuntu_utils/scripts/apt-offline-sh {' '.join(packages)}",
        auto_pw=True,
    )
    s.get(f"{remote_path}/files/apt_offline", Settings.files_dir)
    s.close()


if __name__ == "__main__":
    package_list = []
    if not package_list:
        package_list = Serializer(
            Path(__file__).parent / "get_apt_packages.json", data_type=list
        ).load_json()
    get_apt_packages(package_list)
