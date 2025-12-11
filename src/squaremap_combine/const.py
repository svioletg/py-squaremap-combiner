import importlib.metadata
from collections import OrderedDict
from enum import Enum
from pathlib import Path

import platformdirs

type Rectangle = tuple[int, int, int, int]

PROJECT_NAME: str = 'squaremap_combine'
PROJECT_VERSION: str = importlib.metadata.version('squaremap_combine')
PROJECT_DOCS_URL: str = 'https://squaremap-combine.readthedocs.io/en/latest/'

MODULE_DIR: Path = Path(__file__).absolute().parent

LOGS_DIR: Path = MODULE_DIR / 'logs'
ASSET_DIR: Path = MODULE_DIR / 'asset'
GUI_ASSET_DIR: Path = MODULE_DIR / 'gui/asset'

USER_DATA_DIR: Path = Path(platformdirs.user_data_dir(PROJECT_NAME))

APP_SETTINGS_PATH: Path = USER_DATA_DIR / 'preferences.json'
OPT_AUTOSAVE_PATH: Path = USER_DATA_DIR / 'options-autosave.json'
STYLE_AUTOSAVE_PATH: Path = USER_DATA_DIR / 'style-autosave.json'

DEFAULT_TIME_FORMAT: str = '?Y-?m-?d_?H-?M-?S'
DEFAULT_COORDS_FORMAT: str = '({x}, {y})'
DEFAULT_OUTFILE_FORMAT: str = '{timestamp}{world}-{detail}.{output_ext}'
"""
:param timestamp: A timestamp format string that will be passed to `strftime()`.
:param world:
:param detail:
:param output_ext:
"""

SQMAP_DETAIL: dict[int, int] = {0: 8, 1: 4, 2: 2, 3: 1}
"""Square-blocks-per-pixel for each detail level."""

RGB_CHANNEL_MAX: int = 255

SQMAP_DETAIL_LEVELS: OrderedDict[int, float] = OrderedDict({
    0: 1.0,
    1: 1 / 2,
    2: 1 / 4,
    3: 1 / 8,
})

class NamedColorHex(str, Enum):
    CLEAR   = '#00000000'
    WHITE   = '#ffffff'
    BLACK   = '#000000'
    RED     = '#ff0000'
    YELLOW  = '#ffff00'
    GREEN   = '#00ff00'
    CYAN    = '#00ffff'
    BLUE    = '#0000ff'
    MAGENTA = '#ff00ff'
