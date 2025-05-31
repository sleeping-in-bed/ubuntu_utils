import subprocess
from pathlib import Path

import configs

from ubuntu_utils.framework.settings import Settings
from ubuntu_utils.framework.ssh import SSH


def git_tracked_files(cwd: str | Path = Path.cwd()) -> list[Path]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            text=True,
            cwd=cwd,
        )
        return [cwd / Path(line.strip()) for line in output.splitlines()]
    except subprocess.CalledProcessError as e:
        print("Git command failed:", e)
        return []


remote_path = f"/home/{configs.TEST_USER}/ubuntu_utils"
s = SSH(configs.TEST_HOST, configs.TEST_USER, configs.TEST_PASSWORD)

s.exec_command(f"sudo rm -rf {remote_path}", auto_pw=True)
for file in git_tracked_files(Settings.PROJECT_DIR):
    remote_file = remote_path / file.relative_to(Settings.PROJECT_DIR)
    s.exec_command(f"mkdir -p {remote_file.parent}")
    s.put(file, remote_file)

s.close()
