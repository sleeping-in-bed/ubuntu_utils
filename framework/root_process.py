import ast
import inspect
import json
import queue
import time
from collections import defaultdict
from typing import Any
from urllib.parse import urljoin
import yaml
from psplpy.middleware_utils import Rabbitmq
from .utils import *


exchange_name = 'ubuntu_utils'
user_mark = 'user'
user_result_mark = 'user_result'
root_process_instance_name = 'r'

project_dir = Path(__file__).parent.parent
resources_dir = project_dir / 'resources'
scripts_dir = project_dir / "scripts"

configs_yaml = project_dir / 'configs.yaml'
configs: dict = yaml.safe_load(configs_yaml.read_text())
if configs.get('packages_dir'):
    packages_dir = Path(configs['packages_dir'])
else:
    packages_dir = project_dir / 'packages'


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
        self._execution_record_file, self._execution_record = _load_dict(configs['execution_record_file'])
        self._execution_record = defaultdict(list, self._execution_record)

    @staticmethod
    def _tracer(back_depth: int = 0) -> tuple[str, str, int, str]:
        """return the (filename, lineno, funcname, code) tuple"""
        back_depth = 2 + back_depth
        current_frame = inspect.currentframe()
        for _ in range(back_depth):
            current_frame = current_frame.f_back
        frame_info = inspect.getframeinfo(current_frame)
        filename = frame_info.filename
        function_name = frame_info.function
        line_number = frame_info.lineno
        code_text = frame_info.code_context[0]
        return filename, function_name, line_number, code_text

    def has_executed(self, back_depth: int = 0) -> bool:
        filename, function_name, line_number, code_text = self._tracer(back_depth=1 + back_depth)
        if code_text in self._execution_record[function_name]:
            warning_print(f'Context: "{filename}, {function_name}, {line_number}, {code_text.strip()}" executed')
            return True
        return False

    def update(self, back_depth: int = 0) -> None:
        filename, function_name, line_number, code_text = self._tracer(back_depth=1 + back_depth)
        self._execution_record[function_name].append(code_text)
        self._execution_record_file.write_text(json.dumps(self._execution_record, ensure_ascii=False, indent=4))


class Check:
    """Check if the same codes exist"""
    class DuplicateCodeError(Exception):
        def __init__(self, function_name: str, duplicate_code_list: list[str]):
            self.function_name = function_name
            self.duplicate_code_list = duplicate_code_list

        def __str__(self):
            return f'Function {self.function_name} has same codes:\n{self.duplicate_code_list}'

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
        feature_string_list = [f'{root_process_instance_name}.{attr}'
                               for attr in dir(RootProcess) if not attr.startswith('__')]

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
            duplicates = self._find_duplicates(filtered_code_list)
            if duplicates:
                raise self.DuplicateCodeError(function_name, duplicates)


class Remote:
    def __init__(self):
        self.remote_url = configs['remote_url']
        self.tmp_dir = _convert_path(configs['tmp_dir'])
        self.download_url = urljoin(self.remote_url, 'download')
        self.upload_url = urljoin(self.remote_url, 'upload')

    def get_file(self, sub_path: str | Path) -> Path:
        save_path = self.tmp_dir / sub_path
        execute(f'sudo mkdir -p "{save_path.parent}"')
        local_path = packages_dir / sub_path
        if local_path.exists():
            execute(f'sudo cp "{local_path}" "{save_path}"')
        else:
            remote_url = urljoin(self.download_url, sub_path)
            execute(f'sudo curl --fail -o "{save_path}" -L {remote_url}')
        return save_path

    def upload_file(self, file_path: Path | str, remote_path: Path | str = '') -> None:
        execute(f'curl -X POST -F "file=@{file_path}" {urljoin(self.upload_url, str(remote_path))}')


class Process:
    def __init__(self, routing_key: str, binding_key: str, show_commands: bool = False):
        self._routing_key = routing_key
        self._binding_key = binding_key
        self.show_commands = show_commands

        self._rabbitmq_sender = Rabbitmq(serializer=Rabbitmq.PICKLE)
        self._rabbitmq_sender.send_init(exchange=exchange_name, routing_keys=[self._routing_key])

        self._rabbitmq_receiver = Rabbitmq(serializer=Rabbitmq.PICKLE)
        self._rabbitmq_receiver.recv_init(exchange=exchange_name, binding_keys=[self._binding_key],
                                          callback=self._callback)
        self._rabbitmq_receiver.start_consuming()

    def _callback(self, ch, method, properties, body): ...

    def close(self) -> None:
        self._rabbitmq_receiver.close(suppress_error=True)


class RootProcess(Process):
    def __init__(self, routing_key: str, binding_key: str, show_commands: bool = False,
                 enable_exec_check: bool = True, _check: Check = None):
        super().__init__(routing_key, binding_key, show_commands)
        self._enable_exec_check = enable_exec_check
        self._interval = float(configs['interval'])
        self._exec_rec = ExecutionRecorder()
        self._vars_file, self.vars = _load_dict(configs['vars_file'])
        self._original_exec_check_status = self._enable_exec_check
        self._result_queue = queue.Queue()
        (_check or Check()).check()

        self.user = os.environ.get('SUDO_USER')
        self.home = Path(f'/home/{self.user}')

    def _callback(self, ch, method, properties, body) -> None:
        self._result_queue.put(body['result'])

    @staticmethod
    def _has_executed(func: Callable):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Ret:
            no_check = kwargs.get('no_check') or False
            _back_depth = kwargs.get('_back_depth') or 0
            if not self._enable_exec_check or no_check:
                ret = func(self, *args, **kwargs)
            elif not self._exec_rec.has_executed(back_depth=_back_depth):
                ret = func(self, *args, **kwargs)
                self._exec_rec.update(back_depth=_back_depth)
            else:
                return Ret()
            time.sleep(self._interval)
            return ret
        return wrapper

    @_has_executed
    def exec(self, command: str, capture: bool = False, ignore_error: bool = False, uid: Any = None, *args,
             no_check: bool = False, _back_depth: int = 0) -> Ret:
        command_print(f'Run > {command}')
        if args: raise AssertionError
        self._rabbitmq_sender.basic_publish({'command_type': 'bash', 'command': command, 'capture': capture,
                                             'ignore_error': ignore_error, 'uid': uid})
        return self._result_queue.get()

    def capture(self, command: str, ignore_error: bool = False, uid: Any = None,
                no_check: bool = False, _back_depth: int = 0) -> Ret:
        return self.exec(command, True, ignore_error, uid, no_check=no_check, _back_depth=1 + _back_depth)

    def input(self, var_name: str, prompt: str = '') -> str:
        if not self.vars.get(var_name):
            var_value = input(prompt)
            self.vars[var_name] = var_value
        return var_name

    def replace(self, file: str | Path, old: str, new: str, uid: Any = None,
                no_check: bool = False, _back_depth: int = 0) -> Ret:
        return self.exec(f"sudo sed -i 's/{old}/{new}/g' {file}",
                         uid=uid, no_check=no_check, _back_depth=1 + _back_depth)

    def chdir(self, directory: str | Path):
        self._rabbitmq_sender.basic_publish({'command_type': 'eval', 'command': f'os.chdir("{directory}")'})
        return self._result_queue.get()

    def disable_exec_check(self) -> None:
        self._original_exec_check_status = self._enable_exec_check
        self._enable_exec_check = False

    def reset_exec_check(self) -> None:
        self._enable_exec_check = self._original_exec_check_status

    def close_user_process(self) -> None:
        self._rabbitmq_sender.basic_publish({'command_type': 'eval', 'command': 'self.close()'})


class UserProcess(Process):
    def _exec(self, command: str, capture: bool = False, ignore_error: bool = False, uid: Any = None) -> Ret:
        command_print(f'Run > {command}')
        if not self.show_commands:
            start_time = time.time()
            try:
                ret = execute(command, capture=capture, ignore_error=ignore_error, show_command=False)
            except AssertionError as e:
                error_print(f'Err > elapsed time: {time.time() - start_time:.4f}s')
                raise e
            success_print(f'Ok  > elapsed time: {time.time() - start_time:.4f}s')
            return ret
        return Ret()

    def _callback(self, ch, method, properties, body) -> None:
        command_type = body.pop('command_type')
        if command_type == 'bash':
            result = self._exec(**body)
        elif command_type == 'eval':
            result = eval(body['command'])
        else:
            raise AssertionError(f'Unknown command_type {command_type}')
        self._rabbitmq_sender.basic_publish({'result_mark': self._routing_key, 'result': result})
