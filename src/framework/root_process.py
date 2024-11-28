import pickle
import queue
import sys
import threading
from enum import Enum
from urllib.parse import urljoin
from .utils import *
from .ubuntu_utils_network import *
from .execution_recorder import ExecutionRecorder
from .configs import configs
from .check import Check


class State(Enum):
    BUSY = 'BUSY'
    FREE = 'FREE'


class Process(Enum):
    MAIN_PROCESS = 'MAIN_PROCESS'
    FREE_PROCESS = 'FREE_PROCESS'


class CommandType(Enum):
    BASH = 'BASH'
    EVAL = 'EVAL'


class Command:
    def __init__(self, command: str, c_type: CommandType = CommandType.BASH, ignore_error: bool = False,
                 capture: bool = False, process: Process = Process.MAIN_PROCESS):
        self.command = command
        self.c_type = c_type
        self.ignore_error = ignore_error
        self.capture = capture
        self.process = process
        self.back_depth = back_depth


class CommandId:
    def __init__(self):
        self.id = 0
        self.lock = threading.Lock()

    def get(self) -> int:
        with self.lock:
            current_id = self.id
            self.id += 1
            return current_id


class ThreadingRun:
    def __init__(self, exec_rec, enable_exec_check, free_task):
        self.exec_rec = exec_rec
        self.free_task = free_task
        self.enable_exec_check = enable_exec_check
        self.c_id: CommandId = CommandId()

        self.port = find_free_port()
        self.running_command_list = []
        self.command_result_dict = {}

    def _result_collector(self):
        while True:
            if self.command_result_dict:
                for c_id in self.running_command_list:
                    if c_id in self.command_result_dict:
                        self.running_command_list.remove(c_id)
                        ret: Command = self.command_result_dict.pop(c_id)
                        self.exec_rec.update(back_depth=ret.back_depth)
            else:
                time.sleep(1)

    def threading_exec(self, command: str, ignore_error: bool = False, uid: Any = None,
             no_check: bool = False, _back_depth: int = 0, capture: bool = False,
             process: Process = Process.FREE_PROCESS) -> None:
        if (not self.enable_exec_check or no_check) or (not self.exec_rec.has_executed(back_depth=_back_depth)):
            command_print(f'Threading Run > {command}')
            c_id = self.c_id.get()
            self.running_command_list.append(c_id)
            self.command_que.put(Command(command, CommandType.BASH, ignore_error, capture, process))




class RootProcess:
    def __init__(self, host: str = '127.0.0.1', port: int = 12345,
                 enable_exec_check: bool = True, _check: Check = None):
        self._host, self._port = host, port
        self._enable_exec_check = enable_exec_check
        self._original_exec_check_status = self._enable_exec_check
        self._interval = float(configs.interval)
        self._exec_rec = ExecutionRecorder(configs.execution_record_file)
        self._vars_file = configs.vars_file
        self.vars = load_dict(self._vars_file)
        (_check or Check([attr for attr in dir(RootProcess) if not attr.startswith('__')])).check()

        self.user = os.environ.get('SUDO_USER')
        self.home = Path(f'/home/{self.user}')

        self.threading_command = {}
        self._process_state_dict: dict[str, State] = {}
        self.lock = threading.Lock()
        self.command_id = 0
        self._command_queue, self._result_queue = {}, {}
        self._server_socket = UbuntuUtilsServerSocket(self._host, self._port)
        self._server_socket.handle(self._handler)

    def _handler(self, client_socket: UbuntuUtilsClientSocket, addr: Any):
        process_name = pickle.loads(client_socket.recv())
        if process_name in self._process_state_dict:
            raise ValueError(f'Process name "{process_name}" already exists.')
        self._process_state_dict[process_name] = State.FREE
        while True:
            self._process_state_dict[process_name] = State.BUSY
            client_socket.send(pickle.dumps(self._command_queue.get()))
            received_data = client_socket.recv()
            self._process_state_dict[process_name] = State.FREE
            if not received_data:
                break
            self._result_queue.put(pickle.loads(received_data))

    def exec(self, command: str, ignore_error: bool = False, uid: Any = None,
             no_check: bool = False, _back_depth: int = 0, capture: bool = False,
             process: Process = Process.MAIN_PROCESS) -> Ret:
        if (not self._enable_exec_check or no_check) or (not self._exec_rec.has_executed(back_depth=_back_depth)):
            command_print(f'Run > {command}')
            self._command_queue.put(Command(command, CommandType.BASH, ignore_error, capture, process))
            ret = self._result_queue.get()
            self._exec_rec.update(back_depth=_back_depth)
        else:
            return Ret()
        time.sleep(self._interval)
        return ret

    def capture(self, command: str, ignore_error: bool = False, uid: Any = None,
                no_check: bool = False, _back_depth: int = 0, process: Process = Process.MAIN_PROCESS) -> Ret:
        return self.exec(command, ignore_error, uid, no_check, 1 + _back_depth, True, process)

    def input(self, var_name: str, prompt: str = '') -> str:
        if not self.vars.get(var_name):
            var_value = input(prompt)
            self.vars[var_name] = var_value
        return var_name

    def replace(self, file: str | Path, old: str, new: str, uid: Any = None,
                no_check: bool = False, _back_depth: int = 0) -> Ret:
        return self.exec(f"sudo sed -i 's/{old}/{new}/g' {file}",
                         uid=uid, no_check=no_check, _back_depth=1 + _back_depth)

    def eval(self, command: str, get_result: bool = True) -> Any | None:
        self._command_queue.put({'type': 'eval', 'command': command})
        if get_result:  # if the command causes the user_process shutdown, will not receive the result
            return self._result_queue.get()

    def chdir(self, directory: str | Path):
        return self.eval(f'os.chdir("{directory}")')

    def disable_exec_check(self) -> None:
        self._original_exec_check_status = self._enable_exec_check
        self._enable_exec_check = False

    def reset_exec_check(self) -> None:
        self._enable_exec_check = self._original_exec_check_status

    def close(self):
        self._server_socket.close()

    def close_user_process(self) -> None:
        self.eval('self.close()', get_result=False)


class UserProcess:
    def __init__(self, host: str = '127.0.0.1', port: int = 12345, process_name: str = Process.MAIN_PROCESS):
        self._host, self._port = host, port
        self.process_name = process_name
        self.client_socket = UbuntuUtilsClientSocket(self._host, self._port)
        self.client_socket.connect()
        threading.Thread(target=self._handler).start()

    def _handler(self):
        self.client_socket.send(pickle.dumps(self.process_name))
        while True:
            body = pickle.loads(self.client_socket.recv())
            command_type = body.pop('type')
            if command_type == 'bash':
                result: Ret = self._exec(**body)
            elif command_type == 'eval':
                result: Any = eval(body['command'])
            else:
                raise AssertionError(f'Unknown command_type {command_type}')
            self.client_socket.send(pickle.dumps(result))

    def _exec(self, command: str, capture: bool = False, ignore_error: bool = False) -> Ret:
        command_print(f'Run > {command}')
        start_time = time.perf_counter()
        try:
            ret = execute(command, capture=capture, ignore_error=ignore_error, show_command=False)
        except AssertionError as e:
            error_print(f'Err > elapsed time: {time.perf_counter() - start_time:.4f}s')
            raise e
        success_print(f'Ok  > elapsed time: {time.perf_counter() - start_time:.4f}s')
        return ret

    def close(self):
        self.client_socket.close()
        sys.exit(0)


class Remote:
    def __init__(self):
        self.remote_url = configs.remote_url
        self.tmp_dir = Path('/tmp')
        self.download_url = urljoin(self.remote_url, 'download')
        self.upload_url = urljoin(self.remote_url, 'upload')

    def get_file(self, sub_path: str | Path) -> Path:
        save_path = self.tmp_dir / sub_path
        execute(f'sudo mkdir -p "{save_path.parent}"')
        local_path = configs.packages_dir / sub_path
        if local_path.exists():
            execute(f'sudo cp "{local_path}" "{save_path}"')
        else:
            remote_url = urljoin(self.download_url, sub_path)
            execute(f'sudo curl --fail -o "{save_path}" -L {remote_url}')
        return save_path

    def upload_file(self, file_path: Path | str, remote_path: Path | str = '') -> None:
        execute(f'curl -X POST -F "file=@{file_path}" {urljoin(self.upload_url, str(remote_path))}')
