import os
import pickle
import re
import shutil
import sys
import threading
import time
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import Any

from ubuntu_utils import configs

from .duplicate_check import DuplicateCheck
from .execution_recorder import ExecutionRecorder
from .lib.network_utils import ClientSocket, ServerSocket, find_free_port
from .lib.serialization_utils import Serializer
from .settings import Settings
from .utils import Ret, command_print, error_print, execute, success_print


class CommandType(Enum):
    BASH = "BASH"
    EVAL = "EVAL"


class Command:
    def __init__(
        self,
        command: str,
        cmd_type: CommandType = CommandType.BASH,
        ignore_error: bool = False,
        capture: bool = False,
        back_depth: int = 0,
    ):
        self.command = command
        self.cmd_type = cmd_type
        self.ignore_error = ignore_error
        self.capture = capture
        self.back_depth = back_depth

    def __str__(self):
        s = f"{self.__class__.__name__}("
        for key in vars(self).keys():
            s += f"{key}: {getattr(self, key)}, "
        return s + ")"

    __repr__ = __str__


class RootProcess:
    def __init__(
        self, port: int = None, exec_check: bool = True, duplicate_check: bool = True
    ):
        self._host, self._port, self._exec_check = "0.0.0.0", port, exec_check
        if not self._port:
            self._port = find_free_port(self._host)
        self._original_exec_check_status = self._exec_check
        self._interval = float(Settings.interval)
        self._exec_rec = ExecutionRecorder(Settings.execution_record_file)

        if duplicate_check:
            DuplicateCheck(
                RootProcess, include_attrs=["exec", "capture", "replace", "eval"]
            ).check()

        self.user = os.getenv("SUDO_USER")
        self.home = Path(f"/home/{self.user}")
        self.vars = {}

        self._command_queue, self._result_queue = Queue(), Queue()
        self._server_socket = ServerSocket(self._host, self._port)
        self._server_socket.handle(self._handler)
        print(f"Server running on {self._host}:{self._port}")
        Serializer(Settings.shared_file, data_type=dict).dump_json({"port": self._port})
        print("current_vars:")
        configs.print_all_config()

    def _handler(self, client_socket: ClientSocket, addr: Any):
        while True:
            command = self._command_queue.get()
            client_socket.send_pickle(command)

            received_data = client_socket.recv()
            if not received_data:  # if the connection closed, will receive b''
                break
            result = pickle.loads(received_data)
            self._result_queue.put(result)

    def exec(
        self,
        command: str,
        ignore_error: bool | Iterable[int | str | re.Pattern] = False,
        uid: Any = None,
        no_check: bool = False,
        back_depth: int = 0,
        capture: bool = False,
    ) -> Ret:
        if (not self._exec_check or no_check) or (
            not self._exec_rec.has_executed(back_depth=back_depth)
        ):
            # command_print(f'Run > {command}')
            self._command_queue.put(
                Command(command, CommandType.BASH, ignore_error, capture, back_depth)
            )
            ret: Ret = self._result_queue.get()
            self._exec_rec.update(back_depth=back_depth)
        else:
            return Ret()
        time.sleep(self._interval)
        return ret

    def capture(
        self,
        command: str,
        ignore_error: bool | Iterable[int | str | re.Pattern] = False,
        uid: Any = None,
        no_check: bool = False,
        back_depth: int = 0,
    ) -> Ret:
        return self.exec(command, ignore_error, uid, no_check, 1 + back_depth, True)

    def input(self, var_name: str, prompt: str = "") -> str:
        var_value = input(prompt)
        self.vars[var_name] = var_value
        return var_name

    def replace(
        self,
        file: str | Path,
        pattern: str | re.Pattern,
        replacement: str,
        uid: Any = None,
    ) -> str:
        content = Path(file).read_text(encoding="utf-8")
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        new_content = pattern.sub(replacement, content)
        Path(file).write_text(new_content, encoding="utf-8")
        return new_content

    def eval(
        self, command: str, get_result: bool = True, uid: Any = None
    ) -> Any | None:
        self._command_queue.put(Command(command, CommandType.EVAL))
        if get_result:  # if the command causes the 'user_process' shutdown, will not receive the result
            return self._result_queue.get()

    def chdir(self, directory: str | Path) -> Any:
        return self.eval(f'os.chdir("{directory}")')

    def disable_exec_check(self) -> None:
        self._original_exec_check_status = self._exec_check
        self._exec_check = False

    def reset_exec_check(self) -> None:
        self._exec_check = self._original_exec_check_status

    def close(self) -> None:
        self._server_socket.close()

    def close_user_process(self) -> None:
        self.eval("self.close()", get_result=False)

    def close_all(self) -> None:
        self.close_user_process()
        time.sleep(1)
        self.close()

    @staticmethod
    def clean() -> None:
        shutil.rmtree(Settings.tmp_dir, ignore_errors=True)


class UserProcess:
    def __init__(self):
        self.client_socket = ClientSocket("127.0.0.1", self._get_port())
        print(
            f"Connecting to server {self.client_socket.host}:{self.client_socket.port}"
        )
        self.client_socket.connect()
        threading.Thread(target=self._handler).start()

    @staticmethod
    def _get_port() -> int:
        while True:
            if (
                port := Serializer(Settings.shared_file, data_type=dict)
                .load_json()
                .get("port")
            ):
                return port
            time.sleep(0.1)

    def _handler(self):
        while True:
            received_data = self.client_socket.recv()
            if not received_data:
                break
            command: Command = pickle.loads(received_data)
            if command.cmd_type == CommandType.BASH:
                result: Ret = self._exec(**command.__dict__)
            elif command.cmd_type == CommandType.EVAL:
                result: Any = eval(command.command)
            else:
                raise AssertionError(f"Unknown command type {command.cmd_type}")
            self.client_socket.send_pickle(result)

    def _exec(
        self,
        command: str,
        capture: bool = False,
        ignore_error: bool | Iterable[int | str | re.Pattern] = False,
        **kwargs,
    ) -> Ret:
        command_print(f"Run > {command}")
        start_time = time.perf_counter()
        try:
            ret = execute(
                command, capture=capture, ignore_error=ignore_error, show_command=False
            )
        except AssertionError as e:
            error_print(f"Err > elapsed time: {time.perf_counter() - start_time:.4f}s")
            raise e
        success_print(f"Ok  > elapsed time: {time.perf_counter() - start_time:.4f}s")
        return ret

    def close(self):
        self.client_socket.close()
        sys.exit(0)
