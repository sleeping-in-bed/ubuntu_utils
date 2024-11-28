from commands import *


def common_procedure():
    try:
        general_upgrade()
        pre_settings()
        install_docker()
        install_pycharm()
        install_chrome()
        if not is_vmware():
            install_nvidia_container_toolkit()
            set_proxy()
            install_vmware_workstation()
            install_wps()
            install_mission_center()
            install_vlc()
        install_sougoupinyin()
        post_settings()
    finally:
        close_all()


def ubuntu_docker():
    try:
        general_upgrade()
        pre_settings()
        install_docker()
        post_settings()
    finally:
        close_all()


if __name__ == '__main__':
    common_procedure()
