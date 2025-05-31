import os

# Remote test host information
TEST_HOST = "192.168.0.1"  # IP address of the test host
TEST_USER = "ubuntu"  # SSH login username
TEST_PASSWORD = ""  # SSH login password

# Network configuration for ip_configuration()
HOST_IP = "192.168.0.1"  # New IP address to assign to the host
GATEWAY = "192.168.0.254"  # Gateway address to assign

# User credentials on the target host
USERNAME = "ubuntu"  # Username
PASSWORD = ""  # Password of the user
ROOT_PASSWORD = ""  # Root password to be set

# File server settings (used to download files remotely)
FILE_SERVER_HOST = "192.168.0.1"  # IP address of the file server
FILE_SERVER_PORT = 8080  # Port of the file server

# Local fallback directory if no file server is configured
# Some commands may fail without file server and local file dir
LOCAL_FILE_DIR = None  # e.g., "/home/user/files" or leave as None

# GUI presence on the host
HAS_GUI = "auto"  # True / False / "auto" (auto-detect)

# Identity for GPG and Git usage
NAME = ""  # Full name for Git commits
EMAIL = ""  # Email address for Git and GPG

# Docker Hub credentials for login dockerhub
DOCKERHUB_NAME = ""  # Docker Hub username
DOCKERHUB_PASSWORD = ""  # Docker Hub password


def post_processing():
    global HAS_GUI
    if HAS_GUI == "auto":
        HAS_GUI = bool(os.environ.get("DISPLAY"))
    else:
        HAS_GUI = bool(HAS_GUI)


def print_all_config():
    for key, value in globals().items():
        if key.isupper():
            print(f"{key} = {repr(value)}")


post_processing()
