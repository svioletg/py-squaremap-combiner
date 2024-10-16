"""
Miscellaneous helper utility functions and classes.
"""

import re
import sys
from functools import wraps
from itertools import batched
from json import JSONEncoder
from math import floor
from typing import Any, Callable, Concatenate, ParamSpec, Protocol, Self, TypeVar

import loguru

from squaremap_combine.project import LOGS_DIR
from squaremap_combine.type_alias import Rectangle

T = TypeVar('T')
P = ParamSpec('P')
"""@private"""

class ConfirmationCallback(Protocol):
    """Typing protocol for `combine_core.Combiner.combine()`'s `confirmation_callback` argument."""
    def __call__(self, message: str, *args: Any, **kwargs: Any) -> bool:
        ...

class Color:
    """Represents a 24-bit color.
    Can be constructed from supplied `red`, `green`, `blue`, and `alpha` values between 0 and 255,
    or `from_hex()` can be used to create a `Color` instance from a hexcode string.

    It can then be converted back out to hex code, three-integer tuple representing RGB, or four-integer tuple representing RGBA.

    Format strings are also available:

    | Specifier          | Output                 |
    |--------------------|------------------------|
    | `"{magenta:hex}"`  | `"ff00ff"`             |
    | `"{magenta:rgb}"`  | `"(255, 0, 255)"`      |
    | `"{magenta:rgba}"` | `"(255, 0, 255, 255)"` |
    """
    HEXCODE_REGEX = re.compile(r"^[0-9a-f]{3}$|^[0-9a-f]{6}$|^[0-9a-f]{8}$")
    COMMON: dict[str, tuple[int, ...]] = {
        'transparent': (  0,   0,   0,   0),
        'white'      : (255, 255, 255),
        'black'      : (  0,   0,   0),
        'red'        : (255,   0,   0),
        'green'      : (  0, 255, 0  ),
        'blue'       : (  0,   0, 255),
        'yellow'     : (255, 255,   0),
        'magenta'    : (255,   0, 255),
        'cyan'       : (  0, 255, 255),
    }

    def __init__(self, red: int, green: int, blue: int, alpha: int=255):
        if 0 >= red > 255:
            raise ValueError(f'Channel value cannot be less than 0 or more than 255; was given a red value of {red}')
        self.red   = red
        if 0 >= green > 255:
            raise ValueError(f'Channel value cannot be less than 0 or more than 255; was given a green value of {green}')
        self.green = green
        if 0 >= blue > 255:
            raise ValueError(f'Channel value cannot be less than 0 or more than 255; was given a blue value of {blue}')
        self.blue  = blue
        if 0 >= alpha > 255:
            raise ValueError(f'Channel value cannot be less than 0 or more than 255; was given an alpha value of {alpha}')
        self.alpha = alpha

    def __iter__(self):
        for i in [self.red, self.green, self.blue, self.alpha]:
            yield i

    def __repr__(self) -> str:
        return f'Color(red={self.red}, green={self.green}, blue={self.blue}, alpha={self.alpha})'

    def __str__(self) -> str:
        return self.__repr__()

    def __format__(self, fmt: str) -> str:
        if fmt.startswith('hex'):
            return self.to_hex()[:int(fmt.split('hex')[1] or len(self.to_hex()) + 1)]
        if fmt == 'rgb':
            return str(self.to_rgb())
        if fmt == 'rgba':
            return str(self.to_rgba())
        return self.__str__()

    @staticmethod
    def ensure_hex_format(hexcode: str) -> str | None:
        """Checks whether the given string is a valid 6 or 8 character hexcode, and returns the string if so, returning `None` if invalid.
        A 3 or 6 character hexcode will be converte to 8 by this function.
        """
        if not re.match(Color.HEXCODE_REGEX, hexcode):
            return None
        if len(hexcode) == 3:
            hexcode *= 2
        if len(hexcode) == 6:
            hexcode += 'ff'
        return hexcode

    @classmethod
    def from_name(cls, color_name: str) -> Self:
        """Creates a `Color` from a common name. The name must be present in the `Color.COMMON` dictionary."""
        return cls(*cls.COMMON[color_name])

    @classmethod
    def from_hex(cls, hex_string: str) -> Self:
        """Creates a `Color` instance from the a hexcode string.
        String must be either 3, 6, or 8 characters long.
        If 3 characters are used, they are doubled to create a 6-character hexcode to be used instead.
        The last 2 characters of an 8-character hexcode are used for the alpha value.
        Any 6-character hexcode will have the resulting color's alpha assumed to be 255.
        """
        if not (hexcode := cls.ensure_hex_format(hex_string)):
            raise ValueError('Invalid hexcode given; must be 3, 6, or 8 characters long')
        return cls(*[int(''.join(channel), 16) for channel in batched(hexcode, 2)])

    def to_rgb(self) -> tuple[int, int, int]:
        """Converts this color to a three-integer tuple representing its RGB values."""
        return self.red, self.green, self.blue

    def to_rgba(self) -> tuple[int, int, int, int]:
        """Converts this color to a four-integer tuple representing its RGBA values."""
        return self.red, self.green, self.blue, self.alpha

    def to_hex(self) -> str:
        """Converts this color to a hexcode string."""
        return ''.join([hex(channel)[2:].zfill(2) for channel in self])

class StyleJSONEncoder(JSONEncoder):
    """Extended JSON encoder to aid in serializing `CombinerStyle` objects."""
    def default(self, o: Any) -> tuple | dict:
        if isinstance(o, Color):
            return tuple(o)
        return o.__dict__

def enable_logging(logger: 'loguru.Logger', stdout_level: str='INFO') -> tuple[int, int]:
    """Adds handlers (after clearing previous ones) to the given `loguru` logger and returns their `int` identifiers.

    :param logger: `loguru.Logger` to add handles to.
    :param stdout_level: What level to set the `stdout` stream's handler to. Defaults to "INFO".

    :returns: stdout handler ID, file handler ID
    :rtype: int
    """
    logger.remove()

    logger.level('WARNING', color='<yellow>')
    logger.level('ERROR', color='<red>')

    stdout_handler = logger.add(sys.stdout, colorize=True,
        format="<level>[{time:HH:mm:ss}] {level}: {message}</level>", level=stdout_level, diagnose=False)
    file_handler = logger.add(LOGS_DIR / '{time:YYYY-MM-DD_HH-mm-ss}.log',
        format="[{time:HH:mm:ss}] {level}: {message}", level='DEBUG', mode='w', retention=5, diagnose=False)

    return stdout_handler, file_handler

def confirm_yn(message: str, override: bool=False) -> bool:
    """Prompts the user for confirmation, only returning true if "Y" or "y" was entered."""
    return override or (input(f'{message} (y/n) ').strip().lower() == 'y')

def filled_tuple(source_tuple: tuple[T] | tuple[T, T]) -> tuple[T, T]:
    """Takes a tuple of no more than two values, and returns the original tuple if two values are present,
    or a new tuple consisting of the first value having been doubled if only one value is present.
    """
    return source_tuple if len(source_tuple) == 2 else (source_tuple[0], source_tuple[0])

def copy_method_signature(source: Callable[Concatenate[Any, P], T]) -> Callable[[Callable[..., T]], Callable[Concatenate[Any, P], T]]:
    """Copies a method signature onto the decorated method.

    Taken from: https://github.com/python/typing/issues/270#issuecomment-1346124813
    """
    def wrapper(target: Callable[..., T]) -> Callable[Concatenate[Any, P], T]:
        @wraps(source)
        def wrapped(self: Any, /, *args: P.args, **kwargs: P.kwargs) -> T: # pylint: disable=no-member
            return target(self, *args, **kwargs)
        return wrapped
    return wrapper

def snap_num(num: int | float, multiple: int, snap_method: Callable) -> int:
    """Snaps the given `num` to the smallest or largest (depending on the given `snap_method`) `multiple` it can reside in."""
    return multiple * (snap_method(num / multiple))

def snap_box(box: Rectangle, multiple: int) -> Rectangle:
    """Snaps the given four box coordinates to their lowest `multiple` they can reside in. See `snap_num`.
    Since regions are named based off of their "coordinate" as their top-left point, the lowest multiples are all that matter.
    """
    return tuple(map(lambda n: snap_num(n, multiple, floor), box)) # type: ignore
