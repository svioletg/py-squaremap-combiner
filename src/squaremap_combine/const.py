import importlib.metadata
import re
from collections import OrderedDict
from enum import Enum
from pathlib import Path

import platformdirs

PROJECT_NAME: str = 'squaremap_combine'
PROJECT_VERSION: str = importlib.metadata.version(PROJECT_NAME)
PROJECT_DOCS_URL: str = 'https://squaremap-combine.readthedocs.io/en/latest/'

MODULE_DIR: Path = Path(__file__).absolute().parent
ASSET_DIR: Path = MODULE_DIR / 'asset'
GUI_ASSET_DIR: Path = MODULE_DIR / 'gui/asset'

USER_DATA_DIR: Path = Path(platformdirs.user_data_dir(PROJECT_NAME))
LOGS_DIR: Path = USER_DATA_DIR / 'logs'

DEFAULT_COORDS_FORMAT: str = ' X {x}\n Y {y}'

SQMAP_ZOOM_BPP: OrderedDict[int, int] = OrderedDict({
    0: 8,
    1: 4,
    2: 2,
    3: 1,
})
"""Square-blocks-per-pixel for each squaremap detail level."""

SQMAP_TILE_SIZE: int = 512
"""The width and height of squaremap tile images, in pixels."""
SQMAP_TILE_BLOCKS: int = 512
"""The number of blocks a single squaremap tile covers."""

SQMAP_TILE_NAME_REGEX: re.Pattern[str] = re.compile(r"(-?\d+)_(-?\d+)")

RGB_CHANNEL_MAX: int = 255

IMAGE_SIZE_WARN_THRESH: int = 20_000

class NamedColorHex(str, Enum):
    """Common colors as RGBA hexcodes."""
    CLEAR   = '#00000000'
    WHITE   = '#ffffffff'
    BLACK   = '#000000ff'
    RED     = '#ff0000ff'
    YELLOW  = '#ffff00ff'
    GREEN   = '#00ff00ff'
    CYAN    = '#00ffffff'
    BLUE    = '#0000ffff'
    MAGENTA = '#ff00ffff'
