import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from ubuntu_utils.framework.utils import *
