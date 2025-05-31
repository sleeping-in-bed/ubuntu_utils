from pathlib import Path

import paramiko
from paramiko.sftp_client import SFTPClient
from scp import SCPClient


class SSH:
    def __init__(self, host: str, username: str, password: str, **kwargs):
        self.host = host
        self.username = username
        self.password = password
        self.kwargs = kwargs

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(hostname=host, username=username, password=password, **kwargs)
        self.sftp: SFTPClient = self.ssh.open_sftp()
        self.scp = SCPClient(self.ssh.get_transport())

    def exec_command(
        self, command: str, show_info: bool = True, auto_pw: bool = False
    ) -> None:
        if auto_pw:
            command = f"echo {self.password} | sudo -S {command}"
        if show_info:
            print(command)
        stdin, stdout, stderr = self.ssh.exec_command(command)
        if show_info:
            print(stdout.read().decode(errors="replace"))
            print(stderr.read().decode(errors="replace"))

    def put(self, local_path: str | Path, remote_path: str | Path) -> None:
        self.scp.put(local_path, remote_path, recursive=True, preserve_times=True)

    def get(self, remote_path: str | Path, local_path: str | Path) -> None:
        self.scp.get(remote_path, local_path, recursive=True, preserve_times=True)

    def close(self):
        self.scp.close()
        self.sftp.close()
        self.ssh.close()
