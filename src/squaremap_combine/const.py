import importlib.metadata
import re
from collections import OrderedDict
from enum import Enum
from pathlib import Path

import platformdirs
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.theme import Theme

PROJECT_NAME: str = 'squaremap_combine'
PROJECT_VERSION: str = importlib.metadata.version(PROJECT_NAME)
PROJECT_DOCS_URL: str = 'https://squaremap-combine.readthedocs.io/en/latest/'

MODULE_DIR: Path = Path(__file__).absolute().parent
ASSET_DIR: Path = MODULE_DIR / 'asset'
DEFAULT_FONT_PATH: Path = ASSET_DIR / 'FiraCode-SemiBold.ttf'

USER_DATA_DIR: Path = Path(platformdirs.user_data_dir(PROJECT_NAME))
LOGS_DIR: Path = USER_DATA_DIR / 'logs'

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

IMAGE_PX_NOTICE_THRESH: int = 12_000 * 12_000
IMAGE_PX_CONFIRM_THRESH: int = 20_000 * 20_000

class NamedColorHex(str, Enum):
    """
    Common colors as RGBA hexcodes, based off the HTML 4.01 spec: https://www.w3.org/TR/REC-html40/types.html#h-6.5
    """
    CLEAR   = '#00000000'
    BLACK   = '#000000ff'
    SILVER  = '#c0c0c0ff'
    GRAY    = '#808080ff'
    WHITE   = '#ffffffff'
    MAROON  = '#800000ff'
    RED     = '#ff0000ff'
    PURPLE  = '#800080ff'
    FUCHSIA = '#ff00ffff'
    GREEN   = '#008000ff'
    LIME    = '#00ff00ff'
    OLIVE   = '#808000ff'
    YELLOW  = '#ffff00ff'
    NAVY    = '#000080ff'
    BLUE    = '#0000ffff'
    TEAL    = '#008080ff'
    AQUA    = '#00ffffff'

def setup_rich_console() -> Console:
    class Highlighter(RegexHighlighter):
        base_style = 'autohl.'
        highlights = [ # noqa: RUF012
            r"\b(?P<true>True)\b",
            r"\b(?P<false>False)\b",
        ]

    theme = Theme({
        'info': 'cyan',
        'info2': 'bright_cyan',
        'ok': 'bright_green',
        'warn': 'yellow',
        'err': 'red',
        'low': 'grey70',
        'path': 'magenta',
        'path2': 'bright_magenta',

        'autohl.true': 'green',
        'autohl.false': 'red',
    })

    return Console(
        highlighter=Highlighter(),
        theme=theme,
    )

console: Console = setup_rich_console()
