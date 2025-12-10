"""
Miscellaneous helper utility functions and classes.
"""

import operator
import re
from collections.abc import Callable, Generator, Iterator
from itertools import batched
from json import JSONEncoder
from math import floor
from typing import Any, Literal, Protocol, Self, cast

from squaremap_combine.const import RGB_CHANNEL_MAX
from squaremap_combine.type_alias import Rectangle


class ConfirmationCallback(Protocol):
    """Typing protocol for `combine_core.Combiner.combine()`'s `confirmation_callback` argument."""
    def __call__(self, message: str, *args: Any, **kwargs: Any) -> bool:
        ...

class Color:
    """
    Represents a 24-bit color.
    Can be constructed from supplied `red`, `green`, `blue`, and `alpha` values between 0 and 255,
    or `from_hex()` can be used to create a `Color` instance from a hexcode string.

    It can then be converted back out to hex code, three-integer tuple representing RGB, or four-integer tuple
    representing RGBA.

    Format strings are also available:

    | Specifier          | Output                 |
    |--------------------|------------------------|
    | `"{magenta:hex}"`  | `"ff00ff"`             |
    | `"{magenta:rgb}"`  | `"(255, 0, 255)"`      |
    | `"{magenta:rgba}"` | `"(255, 0, 255, 255)"` |
    """
    HEXCODE_REGEX = re.compile(r"^[0-9a-f]{3}$|^[0-9a-f]{6}$|^[0-9a-f]{8}$")

    def __init__(self, red: int, green: int, blue: int, alpha: int = RGB_CHANNEL_MAX) -> None:
        if any(channel > RGB_CHANNEL_MAX for channel in (red, green, blue, alpha)):
            raise ValueError(
                f'Channel values must be between 0 and {RGB_CHANNEL_MAX}: ({red}, {green}, {blue}, {alpha})',
            )
        self.red   = red
        self.green = green
        self.blue  = blue
        self.alpha = alpha

    def __iter__(self) -> Generator[int]:
        yield from (self.red, self.green, self.blue, self.alpha)

    def __repr__(self) -> str:
        return f'Color<#{self:x}>(red={self.red}, green={self.green}, blue={self.blue}, alpha={self.alpha})'

    def __str__(self) -> str:
        return self.__repr__()

    def __format__(self, fmt: str) -> str:
        if fmt == 'x':
            return self.to_hex()
        if fmt == 'rgb':
            return str(self.to_rgb())
        if fmt == 'rgba':
            return str(self.to_rgba())
        return self.__str__()

    @staticmethod
    def ensure_hex_format(hexcode: str) -> str | None:
        """
        Checks whether the given string is a valid 6 or 8 character hexcode, and returns the string if so, returning
        `None` if invalid. A 3 or 6-character hexcode will be converted to 8 by this function.
        """
        hexcode = hexcode.lstrip('#')
        if not re.match(Color.HEXCODE_REGEX, hexcode):
            return None
        if len(hexcode) == 3:  # noqa: PLR2004
            hexcode = ''.join(f'{ch * 2}' for ch in hexcode)
        if len(hexcode) == 6:  # noqa: PLR2004
            hexcode += 'ff'
        return hexcode

    @classmethod
    def from_hex(cls, hex_string: str) -> Self:
        """
        Creates a `Color` instance from the a hexcode string. String must be either 3, 6, or 8 characters long.
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
        return ''.join(f'{channel:0{2}x}' for channel in self)

class Coord2i:
    """Represents a 2D integer coordinate pair."""
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f'Coord2i(x={self.x}, y={self.y})'

    def __str__(self) -> str:
        return f'({self.x}, {self.y})'

    def __iter__(self) -> Iterator[int]:
        yield from (self.x, self.y)

    def as_tuple(self) -> tuple[int, int]:
        """Returns the coordinate as a tuple."""
        return (self.x, self.y)

    def _math(self,
            math_op: Callable,
            other: 'int | tuple[int, int] | Coord2i',
            direction: Literal['l', 'r']='l',
        ) -> 'Coord2i':
        if isinstance(other, int):
            other = (other, other)
        elif isinstance(other, Coord2i):
            other = (other.x, other.y)

        if direction == 'l':
            return Coord2i(math_op(self.x, other[0]), math_op(self.y, other[1]))
        if direction == 'r':
            return Coord2i(math_op(other[0], self.x), math_op(other[1], self.y))
        raise ValueError(f'_math direction must be "l" or "r"; got {direction!r}')

    def __add__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.add, other)
    def __radd__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.add, other, 'r')

    def __sub__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.sub, other)
    def __rsub__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.sub, other, 'r')

    def __mul__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.mul, other)
    def __rmul__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.mul, other, 'r')

    def __floordiv__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.floordiv, other)
    def __rfloordiv__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.floordiv, other, 'r')

    def __pow__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.pow, other)
    def __rpow__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.pow, other, 'r')

class StyleJSONEncoder(JSONEncoder):
    """Extended JSON encoder to aid in serializing `CombinerStyle` objects."""
    def default(self, o: Any) -> tuple | dict:  # noqa: ANN401
        if isinstance(o, Color):
            return tuple(o)
        return o.__dict__

def confirm_yn(message: str, *, override: bool = False) -> bool:
    """Prompts the user for confirmation, only returning true if "Y" or "y" was entered."""
    return override or (input(f'{message} (y/n) ').strip().lower() == 'y')

def filled_tuple[T](source_tuple: tuple[T] | tuple[T, T]) -> tuple[T, T]:
    """
    Takes a tuple of no more than two values, and returns the original tuple if two values are present, or a new tuple
    consisting of the first value having been doubled if only one value is present.
    """
    return source_tuple if len(source_tuple) == 2 else (source_tuple[0], source_tuple[0])  # noqa: PLR2004

def snap_num(num: int | float, mult: int, snap_func: Callable[[int | float], int]) -> int:
    """Snaps the given `num` to the smallest or largest (depending on the given `snap_method`) multiple. of `mult`."""
    return mult * (snap_func(num / mult))

def snap_box(box: Rectangle, multiple: int) -> Rectangle:
    """
    Snaps the given four box coordinates to their lowest `multiple` they can reside in. See `snap_num`.
    Since regions are named based off of their "coordinate" as their top-left point, the lowest multiples are all that
    matter.
    """
    return cast(Rectangle, tuple(snap_num(n, multiple, floor) for n in box))
