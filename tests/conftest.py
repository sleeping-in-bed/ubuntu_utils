import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "libs"))

RC_DIR = Path(__file__).parent / "resources"
TMP_DIR = Path(__file__).parent / "tmp"
TMP_DIR.mkdir(exist_ok=True, parents=True)

EXECUTION_RECORD_FILE = TMP_DIR / "exec.json"
