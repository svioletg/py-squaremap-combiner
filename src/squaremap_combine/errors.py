REPORT_BUG_MESSAGE: str = 'This is likely a bug;' + \
    ' please open an issue at https://github.com/svioletg/py-squaremap-combiner/issues and provide the above traceback'

class CombineError(Exception):
    """
    Raised when anything in the image combination process fails where no other type of exception would be applicable.
    """

class ErrMsg:
    """Messages to for errors that are generally unexpected and should be reported."""
    GAME_ZERO_IS_NONE: str = 'Could not locate the game world\'s center point! ' + REPORT_BUG_MESSAGE
    BBOX_IS_NONE: str = 'getbbox() failed! ' + REPORT_BUG_MESSAGE
