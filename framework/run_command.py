import ast
import json
from pathlib import Path
import yaml
import inspect
import time
from collections import defaultdict
from typing import Any
from urllib.parse import urljoin
from .utils import *


project_dir = Path(__file__).parent.parent
resources_dir = project_dir / 'resources'
packages_dir = project_dir / 'packages'
configs_yaml = project_dir / 'configs.yaml'
configs: dict = yaml.safe_load(configs_yaml.read_text())


def _convert_path(path: str) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return project_dir / path


def _debug_print(*args, **kwargs) -> None:
    if configs['debug']:
        print(*args, **kwargs)


def _load_dict(path: str) -> tuple[Path, dict]:
    path = _convert_path(path)
    if not path.exists() or not path.read_text().strip():
        return path, {}
    dictionary = json.loads(path.read_text())
    return path, dictionary


class ExecutionRecorder:
    def __init__(self):
        self.execution_record_file, self.execution_record = _load_dict(configs['execution_record_file'])
        self.execution_record = defaultdict(list, self.execution_record)

    @staticmethod
    def _tracer(back_depth: int = 2) -> tuple[str, str, int, str]:
        """return the (filename, lineno, funcname, code) tuple"""
        current_frame = inspect.currentframe()
        for _ in range(back_depth):
            current_frame = current_frame.f_back
        frame_info = inspect.getframeinfo(current_frame)
        filename = frame_info.filename
        function_name = frame_info.function
        line_number = frame_info.lineno
        code_text = frame_info.code_context[0]
        return filename, function_name, line_number, code_text

    def has_executed(self, back_depth: int = 3) -> bool:
        filename, function_name, line_number, code_text = self._tracer(back_depth=back_depth)
        if code_text in self.execution_record[function_name]:
            _debug_print(f'Context: "{filename}, {function_name}, {line_number}, {code_text.strip()}" executed')
            return True
        return False

    def update(self, back_depth: int = 3) -> None:
        filename, function_name, line_number, code_text = self._tracer(back_depth=back_depth)
        self.execution_record[function_name].append(code_text)
        self.execution_record_file.write_text(json.dumps(self.execution_record, ensure_ascii=False, indent=4))


class DuplicateCodeError(Exception):
    def __init__(self, function_name: str, duplicate_code_list: list[str]):
        self.function_name = function_name
        self.duplicate_code_list = duplicate_code_list

    def __str__(self):
        return f'Function {self.function_name} has same codes:\n{self.duplicate_code_list}'


class Check:
    def __init__(self):
        self.commands_path = project_dir / 'commands.py'

    def _extract_functions_and_code(self):
        source_code = self.commands_path.read_text()
        parsed_ast = ast.parse(source_code)
        functions_and_code = {}
        for node in ast.walk(parsed_ast):
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                function_code = ast.get_source_segment(source_code, node)
                functions_and_code[function_name] = function_code
        return functions_and_code

    @staticmethod
    def _filter_code(code_list: list[str]) -> list[str]:
        filtered_code = []
        feature_string_list = [f'r.{attr}' for attr in dir(Run) if not attr.startswith('__')]

        for code in code_list:
            for feature in feature_string_list:
                if feature in code:
                    filtered_code.append(code)
                    break
        return filtered_code

    @staticmethod
    def _find_duplicates(lst: list) -> list:
        unique_items = set(lst)
        duplicates = []

        if len(unique_items) != len(lst):
            for item in unique_items:
                if lst.count(item) > 1:
                    duplicates.append(item)

        return duplicates

    def check(self):
        function_dict = self._extract_functions_and_code()
        for function_name, function_code in function_dict.items():
            code_list = function_code.split('\n')
            filtered_code_list = self._filter_code(code_list)
            print(filtered_code_list)
            duplicates = self._find_duplicates(filtered_code_list)
            if duplicates:
                raise DuplicateCodeError(function_name, duplicates)


class Run:
    BLANK = ' ' * 6

    def __init__(self, enable_exec_check: bool = True, show_commands: bool = False, _check: Check = None):
        self.enable_exec_check = enable_exec_check
        self.show_commands = show_commands
        (_check or Check()).check()
        self._exec_rec = ExecutionRecorder()
        self._vars_file, self.vars = _load_dict(configs['vars_file'])

    def _exec(self, command: str, capture: bool = False, ignore_error: bool = False) -> str | None:
        command_print(f'Run > {command}')
        if not self.show_commands:
            start_time = time.time()
            if capture:
                stdout, stderr, return_code = capture_output(command)
            else:
                return_code = os.system(command)
            end_time = time.time()
            if return_code != 0 and not ignore_error:
                error_print(f'Err > return code: {return_code}, elapsed time: {end_time - start_time:.4f}s')
                raise AssertionError
            else:
                success_print(f'Ok  > elapsed time: {end_time - start_time:.4f}s')
            if capture:
                return stdout

    def exec(self, command: str, capture: bool = False, ignore_error: bool = False, uid: Any = None,
             _back_depth: int = 3) -> str | None:
        if not self.enable_exec_check or not self._exec_rec.has_executed(back_depth=_back_depth):
            result = self._exec(command, capture, ignore_error)
            self._exec_rec.update(back_depth=_back_depth)
            return result

    def capture(self, command: str, ignore_error: bool = False, uid: Any = None, _back_depth: int = 4) -> str:
        return self.exec(command, True, ignore_error, uid, _back_depth) or ''

    def input(self, var_name: str, prompt: str = '') -> Any:
        if not hasattr(self.vars, var_name):
            var_value = input(prompt)
            setattr(self.vars, var_name, var_value)
            return var_value
        return getattr(self.vars, var_name)

    def replace(self, file: str | Path, old: str, new: str, uid: Any = None, _back_depth: int = 4) -> None:
        self.exec(f"sudo sed -i 's/{old}/{new}/g' {file}", uid=uid, _back_depth=_back_depth)


class Remote:
    def __init__(self):
        self.remote_url = configs['remote_url']
        self.tmp_dir = _convert_path(configs['tmp_dir'])
        self.download_url = urljoin(self.remote_url, 'download')

    def get_file(self, sub_path: str | Path) -> Path:
        save_path = self.tmp_dir / sub_path
        r.exec(f'sudo mkdir -p {save_path.parent}')
        local_path = packages_dir / sub_path
        if local_path.exists():
            r.exec(f'sudo cp {local_path} {save_path}')
        else:
            remote_url = urljoin(self.download_url, sub_path)
            r.exec(f'sudo curl -o {save_path} {remote_url}')
        return save_path


r: Run = Run()
remote: Remote = Remote()
