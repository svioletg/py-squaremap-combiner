from collections import OrderedDict
from enum import Enum

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
