"""
Dataclasses for usage across GUI modules.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class UserData:
    """Data model to provide typing and consistency to using `dearpygui`'s `user_data` parameter.
    Every attribute is optional.
    """
    other: Any = None
    """Miscellaneous info to be passed on for any purpose. Should only be used if no other properties fit."""
    cb_display_with: Optional[str | int] = None
    """ID of an item to call `dearpygui.dearpygui.set_value` on with the callback return value."""
    cb_store_in: Optional[str | int] = None
    """ID of an item whose `user_data` will be used to store the callback return value."""
    cb_forward_to: Optional[Callable[..., None]] = None
    """A callable to forward the callback return value to."""

@dataclass
class CallbackArgs(dict):
    """Typed arguments for callback functions."""
    sender: str | int
    app_data: Any
    user_data: UserData

    def __iter__(self):
        for i in self.__annotations__: # pylint: disable=no-member; it does exist
            yield getattr(self, i[0])
