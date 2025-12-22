import re
from collections.abc import Callable, Generator
from itertools import batched
from json import JSONEncoder
from pathlib import Path
from typing import Any, Self

from PIL import Image, ImageDraw

from squaremap_combine.const import RGB_CHANNEL_MAX, NamedColorHex


class ImplementableJSONEncoder(JSONEncoder):
    """
    Extended JSON encoder that attempts to call a ``__json__`` method on the object being serialized, falling back on
    default JSONEncoder behavior otherwise.
    """
    def default(self, o: Any) -> Any:  # noqa: ANN401
        if hasattr(o, '__json__'):
            return o.__json__()
        return super().default(o)

class Color:
    """
    Represents a 24-bit color.

    Format strings available:

    ============================= ========================
    Specifier                     Output
    ============================= ========================
    ``{Color(255, 0, 255):x}``    ``ff00ff``
    ``{Color(255, 0, 255):rgb}``  ``(255, 0, 255)``
    ``{Color(255, 0, 255):rgba}`` ``(255, 0, 255, 255)``
    ============================= ========================

    """
    HEXCODE_REGEX: re.Pattern[str] = re.compile(r"^[0-9a-f]{3}$|^[0-9a-f]{6}$|^[0-9a-f]{8}$")

    def __init__(self, red: int, green: int, blue: int, alpha: int = RGB_CHANNEL_MAX) -> None:
        if any(channel > RGB_CHANNEL_MAX for channel in (red, green, blue, alpha)):
            raise ValueError(
                f'Channel values must be between 0 and {RGB_CHANNEL_MAX}: ({red}, {green}, {blue}, {alpha})',
            )
        self.red   = red
        self.green = green
        self.blue  = blue
        self.alpha = alpha

    def __repr__(self) -> str:
        return f'Color<{self:x}>({self.red}, {self.green}, {self.blue}, {self.alpha})'

    def __str__(self) -> str:
        return self.__repr__()

    def __format__(self, fmt: str) -> str:
        if fmt == 'x':
            return self.as_hex()
        if fmt == 'rgb':
            return str(self.as_rgb())
        if fmt == 'rgba':
            return str(self.as_rgba())
        return self.__str__()

    def __iter__(self) -> Generator[int]:
        yield from (self.red, self.green, self.blue, self.alpha)

    def __hash__(self) -> int:
        return self.as_rgba().__hash__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Color):
            return False
        return self.as_rgba() == other.as_rgba()

    def __json__(self) -> str:
        return '#' + self.as_hex()

    @staticmethod
    def ensure_hex_format(hexcode: str) -> str | None:
        """
        Checks whether the given string is a valid 6 or 8 character hexcode, and returns the string if so, returning
        ``None`` if invalid. A 3 or 6-character hexcode will be converted to 8 by this function.
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
        Creates a ``Color`` instance from the a hexcode string. String must be either 3, 6, or 8 characters long.
        If 3 characters are used, they are doubled to create a 6-character hexcode to be used instead.
        The last 2 characters of an 8-character hexcode are used for the alpha value.
        Any 6-character hexcode will have the resulting color's alpha assumed to be 255.
        """
        if not (hexcode := cls.ensure_hex_format(hex_string)):
            raise ValueError('Invalid hexcode given; must be 3, 6, or 8 characters long')
        return cls(*[int(''.join(channel), 16) for channel in batched(hexcode, 2)])

    @classmethod
    def from_name(cls, name: NamedColorHex | str, alpha: int | None = None) -> Self:
        """
        Returns a ``Color`` instance created from hexcode found in the ``NamedColorHex`` enum.

        :param alpha: An alpha value for the resulting color. If not ``None``, this value will override the hexcode's
            alpha value.

        :raises ValueError: Raised if the given ``name`` does not exist as a ``NamedColorHex`` key.
        """
        try:
            name = name if isinstance(name, NamedColorHex) else NamedColorHex[name.upper()]
        except KeyError as e:
            raise ValueError(f'Not a recognized color name: {name}') from e

        alpha_hex = f'{alpha:0{2}x}' if alpha is not None else name.value[-2:]
        return cls.from_hex(name.value[:-2] + alpha_hex)

    def copy(self) -> 'Color':
        """Returns a new ``Color`` instance with the same channel values as this instance."""
        return Color(*self.as_rgba())

    def as_hex(self, *, prefix: bool = True) -> str:
        """
        Converts this color to an 8-character hexcode string, with leading ``#`` by default.

        :param prefix: Whether to include ``#`` at the beginning of the string.
        """
        return ('#' if prefix else '') + ''.join(f'{channel:0{2}x}' for channel in self)

    def as_rgb(self) -> tuple[int, int, int]:
        """Converts this color to a three-integer tuple representing its RGB values."""
        return self.red, self.green, self.blue

    def as_rgba(self) -> tuple[int, int, int, int]:
        """Converts this color to a four-integer tuple representing its RGBA values."""
        return self.red, self.green, self.blue, self.alpha

def coerce_to[A, B](val: A | B, cls: type[B], coerce_fn: Callable[[A], B] | None = None) -> B:
    """
    Returns ``val`` if ``val`` is an instance of ``cls``, otherwise calls ``coerce_fn`` on ``val`` and returns the
    result. If ``coerce_fn`` is ``None``, ``cls`` will be used as the callable.
    """
    coerce_fn = coerce_fn or cls
    if isinstance(val, cls):
        return val
    return coerce_fn(val) # type: ignore

def snap_num(num: int | float, mult: int, snap_fn: Callable[[int | float], int]) -> int:
    """
    Snaps the given ``num`` to the smallest or largest (depending on the outcome of ``snap_fn``) multiple. of ``mult``.
    """
    return mult * (snap_fn(num / mult))

def draw_corners(img: Image.Image | str | Path, *, length: int = 8, fill: Color | str = 'red') -> Image.Image:
    """
    Loads an image, either as an existing ``Image`` object or from a path, and draws lines of ``length`` pixels for
    each corner of the image, returning the edited image.

    .. note::
        Note that if given an ``Image`` object, the image will be edited in-place due to how
        Pillow's ``ImageDraw.Draw`` method works.
    """
    if not isinstance(img, Image.Image):
        img = Image.open(img)
    if isinstance(fill, Color):
        fill = fill.as_hex()
    length -= 1

    draw = ImageDraw.Draw(img)
    iw, ih = img.size

    # Top left
    draw.line((0, 0, length, 0), fill=fill)
    draw.line((0, 0, 0, length), fill=fill)

    # Top right
    draw.line((iw - 1, 0, iw - (length + 1), 0), fill=fill)
    draw.line((iw - 1, 0, iw - 1, length), fill=fill)

    # Bottom left
    draw.line((0, ih - 1, length, ih - 1), fill=fill)
    draw.line((0, ih - 1, 0, ih - (length + 1)), fill=fill)

    # Bottom right
    draw.line((iw - 1, ih - 1, iw - (length + 1), ih - 1), fill=fill)
    draw.line((iw - 1, ih - 1, iw - 1, ih - (length + 1)), fill=fill)

    return img
