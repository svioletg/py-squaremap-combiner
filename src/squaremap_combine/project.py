"""
Holds constants and functions regarding general project information to be shared across modules.
"""

import importlib.metadata
import os
from pathlib import Path

import platformdirs

PROJECT_NAME = 'squaremap_combine'
PROJECT_VERSION = importlib.metadata.version('squaremap_combine')

MODULE_DIR = Path(os.path.realpath(__file__)).parent
LOGS_DIR = MODULE_DIR / 'logs'
GUI_ASSETS = MODULE_DIR / 'gui/asset'

def user_data_dir() -> Path:
    """Retrieves the user data directory for the current OS using `platformdirs`."""
    return Path(platformdirs.user_data_dir(PROJECT_NAME))
