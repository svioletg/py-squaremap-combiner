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
    should be used, a ``float`` is still technically accepted (and converted to ``int``) if it is a whole number, i.e.
    if ends with ``.0``. Otherwise, a ``ValueError`` is raised on initialization.
    """
    x: int
    y: int

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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, tuple):
            return self.as_tuple() == other
        if isinstance(other, (Coord2i, Coord2f)):
            return self.as_tuple() == other.as_tuple()
        return False

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
        if not isinstance(other, (tuple, Coord2i)):
            other = (other, other)

        if direction == 'l':
            return Coord2i(math_op(self.x, other[0]), math_op(self.y, other[1]))
        if direction == 'r':
            return Coord2i(math_op(other[0], self.x), math_op(other[1], self.y))
        raise ValueError(f'_math direction must be \'l\' or \'r\': {direction!r}')

    def as_tuple(self) -> tuple[int, int]:
        """Returns the coordinate as a tuple."""
        return (self.x, self.y)

    def in_bounds(self, rect: 'Rect | tuple[int, int, int, int]') -> bool:
        """Returns whether this coordinate is within the given ``rect``'s bounds."""
        rect = Rect(rect)
        return (self[0] in range(rect.x1, rect.x2 + 1)) and (self[1] in range(rect.y1, rect.y2 + 1))

    def map(self, fn: Callable[[int], int]) -> 'Coord2i':
        """Returns a new ``Coord2i`` instance with ``fn`` applied to its ``x`` and ``y`` attributes."""
        return Coord2i(fn(self.x), fn(self.y))

class Coord2f:
    """Represents a 2D float coordinate pair."""
    x: float
    y: float

    @overload
    def __init__(self, x_or_xy: int | float, y: int | float) -> None: ...
    @overload
    def __init__(self, x_or_xy: 'tuple[int | float, int | float] | Coord2i | Coord2f', y: None = None) -> None: ...
    def __init__(self,
            x_or_xy: 'int | float | tuple[int | float, int | float] | Coord2i | Coord2f',
            y: int | float | None = None,
        ) -> None:
        """
        :param x_or_xy: Either a tuple of two floats, or an X coordinate. Can also be another ``Coord2f`` instance,
            in which case a new ``Coord2f`` is returned with the same coordinate values.
        :param y: Y coordinate if ``x_or_xy`` is not a tuple. A ``TypeError`` is raised if ``y`` is supplied a
            not-``None`` value when ``x_or_xy`` is a tuple.
        """
        if isinstance(x_or_xy, (Coord2i, Coord2f)):
            self.x = float(x_or_xy.x)
            self.y = float(x_or_xy.y)
            return

        if isinstance(x_or_xy, tuple):
            if y is not None:
                raise TypeError('Coord2f.__init__() received a tuple for argument \'x_or_xy\', but argument \'y\' also'
                    + f' received a value: {y!r}')
            x, y = x_or_xy
        else:
            x = x_or_xy
            if y is None:
                raise TypeError('Coord2f.__init__() missing 1 required positional argument: \'y\'')

        self.x = float(x)
        self.y = float(y)

    def __repr__(self) -> str:
        return f'Coord2f(x={self.x}, y={self.y})'

    def __str__(self) -> str:
        return f'({self.x}, {self.y})'

    def __iter__(self) -> Generator[float]:
        yield from (self.x, self.y)

    def __getitem__(self, idx: int) -> float:
        return (self.x, self.y)[idx]

    def __hash__(self) -> int:
        return self.as_tuple().__hash__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, tuple):
            return self.as_tuple() == other
        if isinstance(other, (Coord2i, Coord2f)):
            return self.as_tuple() == other.as_tuple()
        return False

    def __add__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.add, other)
    def __radd__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.add, other, 'r')

    def __sub__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.sub, other)
    def __rsub__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.sub, other, 'r')

    def __mul__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.mul, other)
    def __rmul__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.mul, other, 'r')

    def __floordiv__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.floordiv, other)
    def __rfloordiv__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.floordiv, other, 'r')

    def __truediv__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.truediv, other)
    def __rtruediv__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.truediv, other, 'r')

    def __pow__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.pow, other)
    def __rpow__(self, other: 'int | float | tuple[int | float, int | float] | Coord2f') -> 'Coord2f':
        return self._math(operator.pow, other, 'r')

    def _math(self,
            math_op: Callable[[int | float, int | float], float],
            other: 'int | float | tuple[int | float, int | float] | Coord2f',
            direction: Literal['l', 'r']='l',
        ) -> 'Coord2f':
        if not isinstance(other, (tuple, Coord2f)):
            other = (other, other)

        if direction == 'l':
            return Coord2f(float(math_op(self.x, other[0])), float(math_op(self.y, other[1])))
        if direction == 'r':
            return Coord2f(float(math_op(other[0], self.x)), float(math_op(other[1], self.y)))
        raise ValueError(f'_math direction must be "l" or "r"; got {direction!r}')

    def as_tuple(self) -> tuple[float, float]:
        """Returns the coordinate as a tuple."""
        return (self.x, self.y)

    def as_int(self, round_fn: Callable[[float], int] | None = None) -> Coord2i:
        """
        Returns this ``Coord2f`` as a :py:class:``~squaremap_combine.geo.Coord2i``, with both coordinates rounded with
        ``round_fn``. By default, `int()` is called on both values.
        """
        round_fn = round_fn or int
        return Coord2i(round_fn(self.x), round_fn(self.y))

    def in_bounds(self, rect: 'Rect | tuple[int, int, int, int]') -> bool:
        """Returns whether this coordinate is within the given ``rect``'s bounds."""
        rect = Rect(rect)
        return (self[0] in range(rect.x1, rect.x2 + 1)) and (self[1] in range(rect.y1, rect.y2 + 1))

    def map(self, fn: Callable[[float], float]) -> 'Coord2f':
        """Returns a new ``Coord2f`` instance with ``fn`` applied to its ``x`` and ``y`` attributes."""
        return Coord2f(fn(self.x), fn(self.y))

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

    def __init__(self, coords_or_rect: 'Rect | tuple[int, int, int, int]') -> None:
        """
        :param coords_or_rect: A tuple of rectangle coordinates (top-left to bottom-right, i.e. X1, Y1, X2, Y2), or
            another ``Rect`` object.
        """
        self.x1, self.y1, self.x2, self.y2 = coords_or_rect

    def __repr__(self) -> str:
        return f'Rect({self.x1!r}, {self.y1!r}, {self.x2!r}, {self.y2!r}, size={self.size})'

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
        return cls((center[0] - radius[0], center[1] - radius[1], center[0] + radius[0], center[1] + radius[1]))

    @classmethod
    def from_size(cls, width: int, height: int, center: Coord2i | tuple[int, int] | None) -> Self:
        """
        Returns a new ``Rect`` of the given size. Will be created with its top left coordinate at ``0, 0`` by default
        unless ``center`` is specified.
        """
        if center:
            return cls((
                center[0] - (width // 2),
                center[1] - (height // 2),
                center[0] + (width // 2) + (width % 2),
                center[1] + (height // 2) + (height % 2),
            ))
        return cls((0, 0, width, height))

    def as_tuple(self) -> tuple[int, int, int, int]:
        """Returns the X1, Y1, X2, and Y2 values as a ``tuple``."""
        return (self.x1, self.y1, self.x2, self.y2)

    def copy(self) -> 'Rect':
        """Returns a new ``Rect`` with the same coordinates as this instance."""
        return Rect(self)

    def in_bounds(self, coord: Coord2i | Coord2f | tuple[int | float, int | float]) -> bool:
        """Returns whether ``coord`` is within this ``Rect`` object's bounds."""
        return Coord2f(coord).in_bounds(self)

    def map(self, fn: Callable[[int], int]) -> 'Rect':
        """Returns a new ``Rect`` with ``fn`` applied to all coordinate values."""
        return Rect((fn(self.x1), fn(self.y1), fn(self.x2), fn(self.y2)))

    def resize(self, xy: Coord2i | tuple[int, int] | int = 0, *, from_center: bool = False) -> 'Rect':
        """
        Returns a new ``Rect`` resized by `xy`, based off of this instance's size. By default, the ``Rect`` is resized
        from the top-left corner, keeping its coordinate intact and only adding to the bottom-right coordinate. If
        ``from_center`` is ``True``, it will be resized outward in all directions from the center of the ``Rect``.
        """
        xy = Coord2i(xy if not isinstance(xy, int) else (xy, xy))
        if from_center:
            xy = xy.map(lambda n: n // 2)
            return Rect((self.x1 - xy.x, self.y1 - xy.y, self.x2 + xy.x, self.y2 + xy.y))
        else:
            return Rect((self.x1, self.y1, self.x2 + xy.x, self.y2 + xy.y))

    def translate_by(self, xy: Coord2i | tuple[int, int] | int = 0) -> 'Rect':
        """Returns a new ``Rect`` with this instance's coordinates shifted by ``xy``."""
        xy = Coord2i(xy if not isinstance(xy, int) else (xy, xy))
        return Rect((self.x1 + xy.x, self.y1 + xy.y, self.x2 + xy.x, self.y2 + xy.y))

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
        self.rect = Rect(rect)
        self.step = step
        self.origin = Coord2i(origin)

    def __repr__(self) -> str:
        return f'Grid({self.rect!r}, step={self.step!r}, origin={self.origin.as_tuple()})'

    @property
    def steps_x(self) -> tuple[int, ...]:
        if self.step == 0:
            return ()
        boundary: tuple[int, int] = (
            snap_num(self.rect.x1, self.step, ceil) + self.origin.x,
            snap_num(self.rect.x2, self.step, floor) + self.origin.x,
        )
        return tuple(range(boundary[0], min(self.origin.x, boundary[1]) + 1, self.step)) \
            + tuple(range(self.origin.x, boundary[1] + 1, self.step))[1:]

    @property
    def steps_y(self) -> tuple[int, ...]:
        if self.step == 0:
            return ()
        boundary: tuple[int, int] = (
            snap_num(self.rect.y1, self.step, ceil) + self.origin.y,
            snap_num(self.rect.y2, self.step, floor) + self.origin.y,
        )
        return tuple(range(boundary[0], min(self.origin.y, boundary[1]) + 1, self.step)) \
            + tuple(range(self.origin.y, boundary[1] + 1, self.step))[1:]

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
        return cls(Rect((x1, y1, x2, y2)), step=step)

    def copy(self, *, step: int | None = None) -> 'Grid':
        """
        Returns a new ``Grid`` with the same coordinates and step value (unless specified otehrwise) as this instance.
        """
        return Grid(self.rect.as_tuple(), step=self.step if step is None else step)

    def map(self,
            fn: Callable[[int], int],
            *,
            origin: Coord2i | tuple[int, int] | Literal['keep'] | None = None,
        ) -> 'Grid':
        """
        Returns a new ``Grid`` with ``fn`` applied to all coordinate values of its ``rect``.

        :param origin: A new origin to give to the resulting grid. If `None` (default), the origin is automatically
            re-calculated based off of its relative distance from the top left corner. Alternatively, ``'keep'`` can be
            given to preserve the ``Grid``'s origin without any modification.
        """
        if origin == 'keep':
            origin = self.origin
        if not origin:
            tl, br = self.rect.corners[0], self.rect.corners[-1]
            offset_factor: tuple[float, float] = (
                (self.origin.x - tl.x) / (br.x - tl.x),
                (self.origin.y - tl.y) / (br.y - tl.y),
            )
            new_tl: Coord2i = tl.map(fn)
            new_br: Coord2i = br.map(fn)
            origin = Coord2i(
                round((new_br.x - new_tl.x) * offset_factor[0] + new_tl.x),
                round((new_br.y - new_tl.y) * offset_factor[1] + new_tl.y),
            )
        return Grid(self.rect.map(fn), step=self.step, origin=origin)

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
        return Grid(self.rect.translate_by(xy), step=self.step, origin=self.origin + xy)

    def translate_to(self, xy: Coord2i | tuple[int, int]) -> 'Grid':
        """
        Returns a new ``Grid`` with this instance's ``rect`` coordinates shifted such that its top left coordinate
        equals ``xy``.
        Refer to :py:meth:`~squaremap_combine.geo.Rect.translate_to`.
        """
        return Grid(self.rect.translate_to(xy), step=self.step, origin=self.origin - (self.rect.corners[0] - xy))

    def iter_steps(self) -> Generator[Coord2i]:
        """
        Yields :py:class:`~squaremap_combine.geo.Coord2i` objects from a :py:class:``~itertools.product`` iterator of
        the x- and y-axis steps.
        """
        yield from map(Coord2i, product(self.steps_x, self.steps_y))

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

    def project(self,
        coord: Coord2i | tuple[int, int],
        other_grid: 'Grid',
    ) -> Coord2i:
        """
        Returns a :py:class:`~squaremap_combine.util.Coord2i` from this ``Grid`` as if it were at the same relative
        position on ``other_grid``.

        >>> g1 = Grid((-100, -100, 100, 100))
        >>> g2 = Grid((0, 0, 100, 100))
        >>> assert g1.transpose_coord(Coord2i(0, 0), g2) == Coord2i(50, 50)
        """
        tr_a, br_a = self.rect.corners[0], self.rect.corners[-1]
        tr_b, br_b = other_grid.rect.corners[0], other_grid.rect.corners[-1]
        offset_factor: Coord2f = Coord2f(coord - tr_a) / Coord2f(br_a - tr_a)
        return ((Coord2f(br_b - tr_b) * offset_factor) + Coord2f(tr_b)).as_int()
