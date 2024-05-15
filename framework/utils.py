import functools
import os
import re
import subprocess
import io
from pathlib import Path
from typing import Callable

from colorama import Fore, Back, Style, init

init(autoreset=True)


class Ret:
    def __init__(self, stdout: str = '', stderr: str = '', returncode: int = None):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode
        self._seq = [self.stdout, self.stderr, self.returncode]

    def __getitem__(self, index):
        return self._seq[index]


def command_print(command: str, *args, **kwargs) -> None:
    print(Back.CYAN + command, *args, **kwargs)


def error_print(command: str, *args, **kwargs) -> None:
    print(Back.RED + command, *args, **kwargs)


def warning_print(command: str, *args, **kwargs) -> None:
    print(Back.YELLOW + command, *args, **kwargs)


def success_print(command: str, *args, **kwargs) -> None:
    print(Back.GREEN + command, *args, **kwargs)


def _is_raise_error(ret: Ret, ignore_error: bool | list | tuple) -> bool:
    if ret.returncode != 0:
        if not ignore_error:
            return True
        elif isinstance(ignore_error, bool):
            return False
        elif isinstance(ignore_error, (list, tuple)):
            out = ret.stdout or '' + ret.stderr or ''
            for i in ignore_error:
                if isinstance(i, int) and i == ret.returncode:
                    return False
                elif isinstance(i, str) and i in out:
                    return False
                elif isinstance(i, re.Pattern) and i.search(out):
                    return False
                else:
                    raise TypeError(f"Unsupported type of ignore_error: {type(i)}")
            return True
        else:
            raise TypeError(f"Unsupported type of ignore_error: {type(ignore_error)}")
    return False


def execute(command: str, capture: bool = False, ignore_error: bool | list | tuple = False,
            show_command: bool = True) -> Ret:
    if show_command:
        command_print(command)
    if isinstance(ignore_error, (list, tuple)):
        capture = True
    if capture:
        output_buffer = io.StringIO()
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   bufsize=1, universal_newlines=True)
        for line in iter(process.stdout.readline, ''):
            print(line, end='', flush=True)
            output_buffer.write(line)
        process.wait()
        stdout_output = output_buffer.getvalue()
        output_buffer.close()

        error_output = process.stderr.read()
        if error_output:
            print(error_output, end='', flush=True)
        return_code = process.returncode
        ret = Ret(stdout_output, error_output, return_code)
    else:
        ret = Ret(returncode=os.system(command))
    if _is_raise_error(ret, ignore_error):
        raise AssertionError(f"Command error occurred. Return code: {ret.returncode}")
    return ret


def capture(command: str, ignore_error: bool | list | tuple = False, show_command: bool = True) -> Ret:
    return execute(command, capture=True, ignore_error=ignore_error, show_command=show_command)


class ConfigEditor:
    def __init__(self, path: str | Path = None, string: str = None, encoding: str = 'utf-8'):
        self.path = Path(path) if path else None
        self.encoding = encoding
        self.string = string if not self.path else self.path.read_text(self.encoding)
        self._key_pattern, self._comment_pattern = re.compile(''), re.compile('')

    def _update_pattern(self, key: str) -> None:
        self._key_pattern = re.compile(fr'^({key}=.*)', flags=re.MULTILINE)
        self._comment_pattern = re.compile(fr'^#\s*({key}=.*)', flags=re.MULTILINE)

    @staticmethod
    def _update_and_write(func: Callable):
        @functools.wraps(func)
        def wrapper(self: 'ConfigEditor', key: str, *args, **kwargs) -> str:
            self._update_pattern(key)

            result = func(self, key, *args, **kwargs)

            self.string = result
            if self.path:
                self.path.write_text(self.string, self.encoding)
            return result

        return wrapper

    @_update_and_write
    def sub_value(self, key: str, value: str) -> str:
        if self._key_pattern.search(self.string):
            return self._key_pattern.sub(f'{key}={value}', self.string)
        elif self._comment_pattern.search(self.string):
            self.uncomment(key)
            return self._comment_pattern.sub(f'# {key}={value}', self.string)
        else:
            raise ValueError(f'Nonexistent key: {key}')

    @_update_and_write
    def uncomment(self, key: str) -> str:
        # if not found the uncommented key
        if not self._key_pattern.search(self.string):
            if self._comment_pattern.search(self.string):
                return self._comment_pattern.sub(r'\1', self.string)
            else:
                raise ValueError(f'Nonexistent key: {key}')
        return self.string

    @_update_and_write
    def comment(self, key: str) -> str:
        self.uncomment(key)
        return self._key_pattern.sub(r'# \1', self.string)

    def exists(self, key: str, exclude_commented: bool = False) -> bool:
        self._update_pattern(key)
        if exclude_commented:
            return bool(self._key_pattern.search(self.string))
        return bool(self._key_pattern.search(self.string) or self._comment_pattern.search(self.string))

    @_update_and_write
    def append(self, key: str, value: str, preappend: bool = False) -> str:
        if self.exists(key):
            self.uncomment(key)
            return self.sub_value(key, value)
        else:
            # check if the last line is empty, if not empty, add a new line to append new key
            if not self.string.split('\n')[-1].strip() == '':
                self.string += '\n'
            if preappend:
                return f'{key}={value}\n' + self.string
            return self.string + f'{key}={value}\n'


class FileWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
