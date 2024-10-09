"""Exceptions and common error messages for use across the package."""

REPORT_BUG = 'This is likely a bug;' + \
    ' please open an issue at https://github.com/svioletg/py-squaremap-combiner/issues and provide the above traceback'

class CombineError(Exception):
    """Raised when anything in the image combination process fails when
    no other type of exception would be applicable.
    """

class AssertionMessage:
    """Messages to use when certain assertions have failed."""
    GAME_ZERO_IS_NONE = 'Could not locate the game world\'s center point! ' + REPORT_BUG
    BBOX_IS_NONE = 'getbbox() failed! ' + REPORT_BUG
