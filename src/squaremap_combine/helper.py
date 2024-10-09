"""Miscellaneous helper and auxiliary utility functions."""

from functools import wraps
from math import floor
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar

from squaremap_combine.type_alias import Rectangle

T = TypeVar('T')
P = ParamSpec('P')

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