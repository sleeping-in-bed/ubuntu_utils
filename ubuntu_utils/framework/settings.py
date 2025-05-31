import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "libs"))
from .lib.other_utils import ClassProperty


class Settings:
    PROJECT_DIR = Path(__file__).parent.parent.parent

    src_dir: Path = ClassProperty(lambda cls: cls.PROJECT_DIR / "ubuntu_utils")
    resources_dir: Path = ClassProperty(lambda cls: cls.src_dir / "resources")
    scripts_dir: Path = ClassProperty(lambda cls: cls.src_dir / "scripts")
    tmp_dir: Path = ClassProperty(lambda cls: cls.PROJECT_DIR / "tmp")
    files_dir: Path = ClassProperty(lambda cls: cls.PROJECT_DIR / "files")

    shared_file: Path = ClassProperty(lambda cls: cls.tmp_dir / "shared.json")
    execution_record_file: Path = ClassProperty(lambda cls: cls.tmp_dir / "exec.json")
    configs_file: Path = ClassProperty(lambda cls: cls.src_dir / "configs.py")

    root_process_instance_name = "r"
    interval = 0.1


Settings.tmp_dir.mkdir(exist_ok=True)
Settings.files_dir.mkdir(exist_ok=True)
