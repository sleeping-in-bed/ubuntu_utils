import re
import shutil

import pytest

from tests.conftest import RC_DIR
from ubuntu_utils.framework.utils import (
    ConfigEditor,
    command_print,
    error_print,
    execute,
    success_print,
    warning_print,
)


def test_print():
    command_print("command")
    error_print("error")
    warning_print("warning")
    success_print("success")


def test_execute(tmp_path):
    test_file = tmp_path / "test"
    test_file.unlink(missing_ok=True)
    execute(f"touch {test_file}")
    assert test_file.exists()

    ret = execute("echo 1")
    assert ret.returncode == 0
    assert ret.stdout == "1\n"
    assert ret.stderr == ""

    with pytest.raises(AssertionError):
        execute(f"mkdir {test_file}")

    ret = execute(f"mkdir {test_file}", ignore_error=["File exist"])
    assert ret.returncode == 1
    assert ret.stdout == ""
    assert "File exists" in ret.stderr

    ret = execute(f"touch {test_file}", ignore_error=True)
    ret = execute(f"mkdir {test_file}", ignore_error=[1])
    ret = execute(f"mkdir {test_file}", ignore_error=[re.compile("File exist")])

    with pytest.raises(AssertionError):
        execute(f"mkdir {test_file}", ignore_error=["Dir exist"])


def test_config_editor(tmp_path):
    grub_path = tmp_path / "grub"
    shutil.copy2(RC_DIR / "grub", grub_path)
    ce = ConfigEditor(grub_path)

    ce.sub_value("GRUB_CMDLINE_LINUX", '"1"')
    ce.uncomment("GRUB_TERMINAL")
    ce.uncomment("GRUB_GFXMODE")
    ce.comment("GRUB_DEFAULT")
    ce.append("GRUB_DISABLE_LINUX_UUID", "true")
    ce.append("GRUB_DISABLE_RECOVERY", '"false"')
    ce.append("TEST1", "1")
    ce.append("TEST2", "2", preappend=True)

    expected = (RC_DIR / "grub-modified").read_text(encoding="utf-8")
    actual = grub_path.read_text(encoding="utf-8")

    assert actual == expected
    assert ce.exists("TEST3") is False
    assert ce.exists("GRUB_BADRAM") is True
