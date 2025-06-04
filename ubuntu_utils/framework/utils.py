import functools
import io
import re
import subprocess
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from colorama import Back, init

init(autoreset=True)


def command_print(command: str, *args, **kwargs) -> None:
    print(Back.CYAN + command, *args, **kwargs)


def error_print(command: str, *args, **kwargs) -> None:
    print(Back.RED + command, *args, **kwargs)


def warning_print(command: str, *args, **kwargs) -> None:
    print(Back.YELLOW + command, *args, **kwargs)


def success_print(command: str, *args, **kwargs) -> None:
    print(Back.GREEN + command, *args, **kwargs)


@dataclass
class Ret:
    stdout: str = field(default="")
    stderr: str = field(default="")
    returncode: int = field(default=None)


def _is_raise_error(
    ret: Ret, ignore_error: bool | Iterable[int | str | re.Pattern] = False
) -> bool:
    if ret.returncode != 0:
        if not ignore_error:
            return True
        elif isinstance(ignore_error, bool):
            return False
        elif isinstance(ignore_error, Iterable):
            out = ret.stdout + ret.stderr
            for item in ignore_error:
                if isinstance(item, int):
                    if item == ret.returncode:
                        return False
                elif isinstance(item, str):
                    if item in out:
                        return False
                elif isinstance(item, re.Pattern):
                    if item.search(out):
                        return False
                else:
                    raise TypeError(f"Unsupported type of ignore_error: {type(item)}")
            return True
        else:
            raise TypeError(f"Unsupported type of ignore_error: {type(ignore_error)}")
    return False


def execute(
    command: str,
    ignore_error: bool | Iterable[int | str | re.Pattern] = False,
    show_command: bool = True,
) -> Ret:
    if show_command:
        command_print(command)
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        errors="replace",
    )

    def read_stream(stream, buffer):
        for line in iter(stream.readline, ""):
            print(line, end="\n", flush=True)
            buffer.write(line)

    stdout_thread = threading.Thread(
        target=read_stream, args=(process.stdout, output_buffer)
    )
    stderr_thread = threading.Thread(
        target=read_stream, args=(process.stderr, error_buffer)
    )
    stdout_thread.start()
    stderr_thread.start()
    stdout_thread.join()
    stderr_thread.join()
    process.wait()

    stdout_output = output_buffer.getvalue()
    output_buffer.close()
    error_output = error_buffer.getvalue()
    error_buffer.close()

    return_code = process.returncode

    ret = Ret(stdout_output, error_output, return_code)
    if _is_raise_error(ret, ignore_error):
        raise AssertionError(
            f"Command error occurred. Return code: {ret.returncode}, "
            f"Stdout: {ret.stdout}, Stderr: {ret.stderr}"
        )
    return ret


class ConfigEditor:
    def __init__(
        self,
        path: str | Path | None = None,
        content: str | None = None,
        encoding: str = "utf-8",
    ):
        # Set file path if provided
        self.path = Path(path) if path else None
        self.encoding = encoding

        # Load content from file if path is given; otherwise use provided string
        self.content = content if not self.path else self.path.read_text(self.encoding)

        # Regular expressions for matching config keys and commented keys
        self._key_pattern, self._comment_pattern = re.compile(""), re.compile("")

    def _update_pattern(self, key: str) -> None:
        # Update regex patterns to match active and commented lines for the given key
        self._key_pattern = re.compile(rf"^({key}\s*=\s*.*)", flags=re.MULTILINE)
        self._comment_pattern = re.compile(
            rf"^#\s*({key}\s*=\s*.*)", flags=re.MULTILINE
        )

    @staticmethod
    def _update_and_write(func: Callable):
        # Decorator that updates regex patterns and writes changes to file after modifying content
        @functools.wraps(func)
        def wrapper(self: "ConfigEditor", key: str, *args, **kwargs) -> str:
            self._update_pattern(key)  # Set patterns for current key
            result = func(self, key, *args, **kwargs)  # Perform content modification
            self.content = result  # Update in-memory content

            # If a file is associated, write updated content to disk
            if self.path:
                self.path.write_text(self.content, self.encoding)
            return result

        return wrapper

    @_update_and_write
    def sub_value(self, key: str, value: str) -> str:
        # Substitute the value for the given key
        if self._key_pattern.search(self.content):
            return self._key_pattern.sub(f"{key}={value}", self.content)
        elif self._comment_pattern.search(self.content):
            self.uncomment(key)  # Uncomment first if key is commented
            return self._comment_pattern.sub(f"# {key}={value}", self.content)
        else:
            raise ValueError(f"Nonexistent key: {key}")

    @_update_and_write
    def uncomment(self, key: str) -> str:
        # Uncomment a line for the given key if it is commented
        if not self._key_pattern.search(self.content):
            if self._comment_pattern.search(self.content):
                return self._comment_pattern.sub(r"\1", self.content)
            else:
                raise ValueError(f"Nonexistent key: {key}")
        return self.content

    @_update_and_write
    def comment(self, key: str) -> str:
        # Comment out a key-value line
        self.uncomment(key)  # Make sure it’s not already commented
        return self._key_pattern.sub(r"# \1", self.content)

    def exists(self, key: str, exclude_commented: bool = False) -> bool:
        # Check if a key exists in content; optionally ignore commented lines
        self._update_pattern(key)
        if exclude_commented:
            return bool(self._key_pattern.search(self.content))
        return bool(
            self._key_pattern.search(self.content)
            or self._comment_pattern.search(self.content)
        )

    @_update_and_write
    def append(self, key: str, value: str, preappend: bool = False) -> str:
        # Append a new key-value pair if not exists; otherwise update it
        if self.exists(key):
            self.uncomment(key)
            return self.sub_value(key, value)
        else:
            # Ensure final newline before appending
            if self.content.split("\n")[-1].strip() != "":
                self.content += "\n"

            # Insert at the beginning if preappend is True
            if preappend:
                return f"{key}={value}\n" + self.content

            # Append at the end
            return self.content + f"{key}={value}\n"
