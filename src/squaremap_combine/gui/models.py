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
    display: Optional[str | int] = None
    """The ID of a GUI element whose value should be set to the result of this element's callback."""
    forward: Optional[Callable[..., None]] = None
    """A callable to forward the result of this element's callback to."""

@dataclass
class CallbackArgs(dict):
    """Typed arguments for callback functions."""
    sender: str | int
    app_data: Any
    user_data: UserData

    def __iter__(self):
        for i in self.__annotations__: # pylint: disable=no-member; it does exist
            yield getattr(self, i[0])
