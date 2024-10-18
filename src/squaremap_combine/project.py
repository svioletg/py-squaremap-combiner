"""
Holds constants and functions regarding general project information to be shared across modules.
"""

import importlib.metadata
import os
from pathlib import Path

import platformdirs

PROJECT_NAME = 'squaremap_combine'
PROJECT_VERSION = importlib.metadata.version('squaremap_combine')
PROJECT_DOCS_URL = 'https://squaremap-combine.readthedocs.io/en/latest/'

MODULE_DIR = Path(os.path.realpath(__file__)).parent

LOGS_DIR = MODULE_DIR / 'logs'
ASSET_DIR = MODULE_DIR / 'asset'
GUI_ASSET_DIR = MODULE_DIR / 'gui/asset'

USER_DATA_DIR = Path(platformdirs.user_data_dir(PROJECT_NAME))

APP_SETTINGS_PATH = USER_DATA_DIR / 'preferences.json'
OPT_AUTOSAVE_PATH = USER_DATA_DIR / 'options-autosave.json'
STYLE_AUTOSAVE_PATH = USER_DATA_DIR / 'style-autosave.json'
