from pathlib import Path
import yaml


class Configs:
    def __init__(self):
        self.project_dir = Path(__file__).parent.parent.parent
        self.src_dir = self.project_dir / 'src'
        self.resources_dir = self.src_dir / 'resources'
        self.scripts_dir = self.src_dir / "scripts"
        self.tmp_dir = self.src_dir / "tmp"
        self.packages_dir = self.project_dir / 'packages'
        self.port_file = self.tmp_dir / 'port.json'
        self.execution_record_file = self.tmp_dir / 'exec.json'

        self.configs_yaml = self.project_dir / 'configs.yaml'
        self.configs: dict = yaml.safe_load(self.configs_yaml.read_text(encoding='utf-8'))

        if value := self.configs.get('debug'):
            self.debug = value
        if value := self.configs.get('vars_file'):
            self.vars_file = value
        if value := self.configs.get('remote_url'):
            self.remote_url = value
        if value := self.configs.get('interval'):
            self.interval = value
        if value := self.configs.get('packages_dir'):
            self.packages_dir = Path(value)


configs = Configs()
