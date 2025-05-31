import pytest

from tests.conftest import RC_DIR
from ubuntu_utils.framework.duplicate_check import DuplicateCheck
from ubuntu_utils.framework.process import RootProcess


def test_check():
    DuplicateCheck(RootProcess, RC_DIR / "commands.py").check()

    with pytest.raises(DuplicateCheck.DuplicateCodeError):
        DuplicateCheck(RootProcess, RC_DIR / "commands2.py").check()
