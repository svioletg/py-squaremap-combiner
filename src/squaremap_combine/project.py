"""
Holds constants regarding general project information to be shared across modules.
"""

import importlib.metadata
import os
from pathlib import Path

PROJECT_VERSION = importlib.metadata.version('squaremap_combine')
MODULE_DIR = Path(os.path.realpath(__file__)).parent
LOGS_DIR = MODULE_DIR / 'logs'
