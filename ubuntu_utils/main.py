from commands import *

try:
    pre_settings()
finally:
    r.close_all()
#
#
# def common_procedure():
#     try:
#         pre_settings()
#         install_docker()
#         install_pycharm()
#         install_chrome()
#         if not is_vmware():
#             install_nvidia_container_toolkit()
#             set_proxy()
#             install_vmware_workstation()
#             install_wps()
#             install_mission_center()
#             install_vlc()
#         install_sougoupinyin()
#         post_settings()
#     finally:
#         r.close_all()
#
#
# def ubuntu_docker():
#     try:
#         pre_settings()
#         install_docker()
#         post_settings()
#     finally:
#         r.close_all()
#
#
# if __name__ == '__main__':
#     common_procedure()
