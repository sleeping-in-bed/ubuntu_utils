import io
import re
import time
from unittest.mock import patch

import pytest

from ubuntu_utils.framework.process import RootProcess, UserProcess
from ubuntu_utils.framework.settings import Settings


@pytest.fixture
def root_process(tmp_path):
    print(tmp_path)
    Settings.tmp_dir = tmp_path
    rp = RootProcess(duplicate_check=False)
    rp.start()
    time.sleep(0.5)
    UserProcess()
    yield rp
    rp.close_all()


def test_exec(root_process, capsys):
    root_process.exec("echo hello")
    root_process.exec("echo world")

    out = capsys.readouterr().out
    print(repr(out))
    run_regex = (
        r".*Run > echo hello\n"
        r".*Ok  > elapsed time: \d+\.\d+s\n"
        r".*Run > echo world\n"
        r".*Ok  > elapsed time: \d+\.\d+s\n"
    )
    assert re.search(run_regex, out, re.DOTALL)


def test_capture(root_process):
    result = root_process.capture("echo 1")
    assert result.stdout == "1\n"
    assert result.stderr == ""
    assert result.returncode == 0


@patch("builtins.input", side_effect=["Hello"])
def test_input(mock_input, root_process):
    root_process.input("test", "please input\n")
    assert root_process.vars["test"] == "Hello"


def test_replace(root_process, tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("Hello\n0.001s\n", encoding="utf-8")

    root_process.replace(file_path, "Hello", "World")
    assert file_path.read_text(encoding="utf-8") == "World\n0.001s\n"

    root_process.replace(file_path, re.compile(r"\d\.\d+s"), "100s")
    assert file_path.read_text(encoding="utf-8") == "World\n100s\n"


def test_chdir(root_process):
    root_process.chdir("/")
    pwd = root_process.capture("pwd")
    assert pwd.stdout == "/\n"


@patch("sys.stdout", new_callable=io.StringIO)
def test_disable_exec_check_and_reset_exec_check(mock_stdout, root_process):
    run = r".*Run > echo hello\n"
    ok = r".*Ok  > elapsed time: \d+\.\d+s\n"
    executed = r'.*Context: ".*/test_process.py, .+, \d+, .*echo hello.*" executed\n'

    root_process.exec("echo hello")
    root_process.exec("echo hello")

    output = mock_stdout.getvalue()
    assert re.search(run + ok + executed, output, re.DOTALL)

    root_process.disable_exec_check()
    root_process.exec("echo hello")
    output = mock_stdout.getvalue()
    assert re.search(run + ok + executed + run + ok, output, re.DOTALL)

    root_process.reset_exec_check()
    root_process.exec("echo hello")
    output = mock_stdout.getvalue()
    assert re.search(run + ok + executed + run + ok + executed, output, re.DOTALL)
