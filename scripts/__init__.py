from pathlib import Path
import sys

project_dir = Path(__file__).parent.parent
sys.path.append(str(project_dir))

from framework.utils import *
