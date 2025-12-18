"""
Geometry classes and functions.
"""

import operator
from collections.abc import Callable, Generator, Iterable
from itertools import product
from math import ceil, floor
from typing import Literal, Self, overload

from squaremap_combine.util import snap_num


class Coord2i:
    """
    Represents a 2D integer coordinate pair. While ``x`` and ``y`` are typed as only ``int``, and explicit conversion
    should be used, a ``float`` is still technically accepted if it is a whole number, i.e. if ends with ``.0``.
    Otherwise, a ``ValueError`` is raised on initialization.
    """
    @overload
    def __init__(self, x_or_xy: int, y: int) -> None: ...
    @overload
    def __init__(self, x_or_xy: 'tuple[int, int] | Coord2i', y: None = None) -> None: ...
    def __init__(self, x_or_xy: 'int | tuple[int, int] | Coord2i', y: int | None = None) -> None:
        """
        Initializes a ``Coord2i`` with either a single tuple argument, or two coordinate arguments.

        :param x_or_xy: Either a tuple of two integers, or an X coordinate. Can also be another ``Coord2i`` instance,
            in which case a new ``Coord2i`` is returned with the same coordinate values.
        :param y: Y coordinate if ``x_or_xy`` is not a tuple. A ``TypeError`` is raised if ``y`` is supplied a
            not-``None`` value when ``x_or_xy`` is a tuple.
        """
        if isinstance(x_or_xy, Coord2i):
            self.x = x_or_xy.x
            self.y = x_or_xy.y
            return

        if isinstance(x_or_xy, tuple):
            if y is not None:
                raise TypeError('Coord2i.__init__() received a tuple for argument \'x_or_xy\', but argument \'y\' also'
                    + f' received a value: {y!r}')
            x, y = x_or_xy
        else:
            x = x_or_xy
            if y is None:
                raise TypeError('Coord2i.__init__() missing 1 required positional argument: \'y\'')

        if (x % 1) != 0:
            raise ValueError(f'Coord2i.x must be an int or whole number: {x!r}')
        self.x = int(x)
        if (y % 1) != 0:
            raise ValueError(f'Coord2i.y must be an int or whole number: {y!r}')
        self.y = int(y)

    def __repr__(self) -> str:
        return f'Coord2i(x={self.x}, y={self.y})'

    def __str__(self) -> str:
        return f'({self.x}, {self.y})'

    def __iter__(self) -> Generator[int]:
        yield from (self.x, self.y)

    def __getitem__(self, idx: int) -> int:
        return (self.x, self.y)[idx]

    def __hash__(self) -> int:
        return self.as_tuple().__hash__()

    def __eq__(self, other: 'Coord2i') -> bool:
        return self.as_tuple() == other.as_tuple()

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

    def _math(self,
            math_op: Callable[[int, int], int],
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

    def as_tuple(self) -> tuple[int, int]:
        """Returns the coordinate as a tuple."""
        return (self.x, self.y)

    def map(self, fn: Callable[[int], int]) -> 'Coord2i':
        """Returns a new ``Coord2i`` instance with ``fn`` applied to its ``x`` and ``y`` attributes."""
        return Coord2i(fn(self.x), fn(self.y))

class Rect:
    """Represents a simple 2D rectangle."""
    x1: int
    """Top-left X coordinate."""
    y1: int
    """Top-left Y coordinate."""
    x2: int
    """Bottom-right X coordinate."""
    y2: int
    """Bottom-right Y coordinate."""

    def __init__(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __repr__(self) -> str:
        return f'Rect(x1={self.x1!r}, y1={self.y1!r}, x2={self.x2!r}, y2={self.y2!r})'

    def __iter__(self) -> Generator[int]:
        yield from self.as_tuple()

    def __getitem__(self, idx: int) -> int:
        return self.as_tuple()[idx]

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def center(self) -> Coord2i:
        """The center coordinate."""
        return Coord2i(self.x1 + (self.width // 2), self.y1 + (self.height // 2))

    @property
    def corners(self) -> tuple[Coord2i, Coord2i, Coord2i, Coord2i]:
        """
        Returns the four corner coordinates as :py:class:`~squaremap_combine.geo.Coord2i` objects.

        :returns corners: (top-left, top-right, bottom-left, bottom-right)
        """
        return (
            Coord2i(self.x1, self.y1),
            Coord2i(self.x2, self.y1),
            Coord2i(self.x1, self.y2),
            Coord2i(self.x2, self.y2),
        )

    @classmethod
    def from_radius(cls,
            radius: int | Coord2i | tuple[int, int],
            center: Coord2i | tuple[int, int] | None = (0, 0),
        ) -> Self:
        """Returns a new ``Rect`` based on a given radius and origin coordinate."""
        radius = (radius, radius) if isinstance(radius, int) else radius
        center = center or (0, 0)
        if any(n <= 0 for n in radius):
            raise ValueError(f'Rect radius must be greater than zero in both directions: {radius!r}')
        return cls(center[0] - radius[0], center[1] - radius[1], center[0] + radius[0], center[1] + radius[1])

    @classmethod
    def from_size(cls, width: int, height: int, center: Coord2i | tuple[int, int] | None) -> Self:
        """
        Returns a new ``Rect`` of the given size. Will be created with its top left coordinate at ``0, 0`` by default
        unless ``center`` is specified.
        """
        if center:
            return cls(
                center[0] - (width // 2),
                center[1] - (height // 2),
                center[0] + (width // 2) + (width % 2),
                center[1] + (height // 2) + (height % 2),
            )
        return cls(0, 0, width, height)

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Returns the X1, Y1, X2, and Y2 values as a ``tuple``."""
        return (self.x1, self.y1, self.x2, self.y2)

    def copy(self) -> 'Rect':
        """Returns a new ``Rect`` with the same coordinates as this instance."""
        return Rect(*self.as_tuple())

    def map(self, fn: Callable[[int], int]) -> 'Rect':
        """Returns a new ``Rect`` with ``fn`` applied to all coordinate values."""
        return Rect(fn(self.x1), fn(self.y1), fn(self.x2), fn(self.y2))

    def resize(self, xy: Coord2i | tuple[int, int] | int = 0, *, from_center: bool = False) -> 'Rect':
        """
        Returns a new ``Rect`` resized by `xy`, based off of this instance's size. By default, the ``Rect`` is resized
        from the top-left corner, keeping its coordinate intact and only adding to the bottom-right coordinate. If
        ``from_center`` is ``True``, it will be resized outward in all directions from the center of the ``Rect``.
        """
        xy = Coord2i(xy if not isinstance(xy, int) else (xy, xy))
        if from_center:
            xy = xy.map(lambda n: n // 2)
            return Rect(self.x1 - xy.x, self.y1 - xy.y, self.x2 + xy.x, self.y2 + xy.y)
        else:
            return Rect(self.x1, self.y1, self.x2 + xy.x, self.y2 + xy.y)

    def translate_by(self, xy: Coord2i | tuple[int, int] | int = 0) -> 'Rect':
        """Returns a new ``Rect`` with this instance's coordinates shifted by ``xy``."""
        xy = Coord2i(xy if not isinstance(xy, int) else (xy, xy))
        return Rect(self.x1 + xy.x, self.y1 + xy.y, self.x2 + xy.x, self.y2 + xy.y)

    def translate_to(self, xy: Coord2i | tuple[int, int]) -> 'Rect':
        """
        Returns a new ``Rect`` with this instance's coordinates shifted such that its top left coordinate
        equals ``xy``.
        """
        return self.translate_by(xy - self.corners[0])

class Grid:
    """Represents a 2D grid with defined corners and a step value."""
    rect: Rect
    step: int
    """An interval to count steps or divisions in the grid by."""
    origin: Coord2i
    """The origin point from which grid steps should be counted outward from."""

    def __init__(self,
            rect: Rect | tuple[int, int, int, int],
            *,
            step: int = 0,
            origin: Coord2i | tuple[int, int] = (0, 0),
        ) -> None:
        self.rect = rect if isinstance(rect, Rect) else Rect(*rect)
        self.step = step
        self.origin = Coord2i(origin)

    def __repr__(self) -> str:
        return f'Grid(rect={self.rect!r}, step={self.step!r})'

    @property
    def steps_x(self) -> tuple[int, ...]:
        if self.step == 0:
            return ()
        boundary: tuple[int, int] = (
            snap_num(self.rect.x1, self.step, ceil) + self.origin.x,
            snap_num(self.rect.x2, self.step, floor) + self.origin.x,
        )
        return tuple(range(boundary[0], min(self.origin.x, boundary[1]) + 1, self.step)) \
            + tuple(range(self.origin.x, boundary[1], self.step))[1:]

    @property
    def steps_y(self) -> tuple[int, ...]:
        if self.step == 0:
            return ()
        boundary: tuple[int, int] = (snap_num(self.rect.y1, self.step, ceil), snap_num(self.rect.y2, self.step, floor))
        return tuple(range(boundary[0], min(self.origin.y, boundary[1]) + 1, self.step)) \
            + tuple(range(self.origin.y, boundary[1], self.step))[1:]

    @property
    def steps_count(self) -> int:
        """The total number of X,Y coordinates that exist on this grid by ``step``."""
        return len(self.steps_x) * len(self.steps_y)

    @classmethod
    def from_steps(cls, source_steps: Iterable[Coord2i | tuple[int, int]], step: int = 0) -> Self:
        """Returns a ``Grid`` with bounds defined by a given set of X,Y coordinate steps."""
        source_steps = list(source_steps)
        if len(source_steps) == 0:
            raise ValueError('Cannot create a Grid from an empty sequence of steps')
        x1, y1, x2, y2 = 0, 0, 0, 0
        for coord in source_steps:
            x1 = min(x1, coord[0])
            y1 = min(y1, coord[0])
            x2 = max(x2, coord[0])
            y2 = max(y2, coord[0])
        return cls(Rect(x1, y1, x2, y2), step=step)

    def copy(self, *, step: int | None = None) -> 'Grid':
        """
        Returns a new ``Grid`` with the same coordinates and step value (unless specified otehrwise) as this instance.
        """
        return Grid(self.rect.as_tuple(), step=self.step if step is None else step)

    def map(self, fn: Callable[[int], int]) -> 'Grid':
        """Returns a new ``Grid`` with ``fn`` applied to all coordinate values of its ``rect``."""
        return Grid(self.rect.map(fn), step=self.step)

    def resize(self, xy: Coord2i | tuple[int, int] | int = 0, *, from_center: bool = False) -> 'Grid':
        """
        Returns a new ``Grid`` resized by `xy`, based off of this instance's ``rect`` size.
        Refer to :py:meth:`~squaremap_combine.geo.Rect.resize`.
        """
        return Grid(self.rect.resize(xy, from_center=from_center), step=self.step)

    def translate_by(self, xy: Coord2i | tuple[int, int] | int = 0) -> 'Grid':
        """
        Returns a new ``Grid`` with this instance's ``rect`` coordinates shifted by ``xy``.
        Refer to :py:meth:`~squaremap_combine.geo.Rect.translate_by`.
        """
        return Grid(self.rect.translate_by(xy), step=self.step)

    def translate_to(self, xy: Coord2i | tuple[int, int]) -> 'Grid':
        """
        Returns a new ``Grid`` with this instance's ``rect`` coordinates shifted such that its top left coordinate
        equals ``xy``.
        Refer to :py:meth:`~squaremap_combine.geo.Rect.translate_to`.
        """
        return Grid(self.rect.translate_to(xy), step=self.step)

    def iter_steps(self) -> Generator[tuple[int, int]]:
        """Yields from a :py:class:``~itertools.product`` iterator of the x- and y-axis steps."""
        yield from product(self.steps_x, self.steps_y)

    def snap_coord(self,
            coord: Coord2i | tuple[int, int],
            round_fn: Callable[[int | float], int] | None = None,
        ) -> Coord2i:
        """
        Returns the nearest grid interval coordinate for a given coordinate. For example; where ``coord`` is ``(4, 7)``,
        and this ``Grid``'s ``step`` is 10, ``.snap_coord(coord)`` would return ``Coord2i(0, 10)``.

        :param round_fn: A function of ``(int) -> int`` to use for rounding the divided value in the formula. By default
            the built-in ``round`` is used, but ``math.floor`` or ``math.ceil`` for example could be used to snap to the
            lower or higher coordinate point respectively.
        """
        coord = coord if isinstance(coord, Coord2i) else Coord2i(*coord)
        round_fn = round_fn or round
        return coord.map(lambda n: snap_num(n, self.step, round_fn))
