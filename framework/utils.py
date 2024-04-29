import os
import subprocess
import io
from colorama import Fore, Back, Style, init

init(autoreset=True)


def command_print(command: str, *args, **kwargs) -> None:
    print(Back.CYAN + command, *args, **kwargs)


def error_print(command: str, *args, **kwargs) -> None:
    print(Back.RED + command, *args, **kwargs)


def success_print(command: str, *args, **kwargs) -> None:
    print(Back.GREEN + command, *args, **kwargs)


def p_os_system(command: str) -> int:
    command_print(command)
    return os.system(command)


def capture_output(command: str) -> tuple[str, str, int]:
    """return the (stdout, stderr, return_code) tuple"""
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
    return stdout_output, error_output, return_code
