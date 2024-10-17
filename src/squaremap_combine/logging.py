"""
Handles setting up logger for the whole project. The logger should then be imported only from this module.
"""

import sys

import loguru
from loguru import logger

from squaremap_combine.project import LOGS_DIR

logger.level('GUI_COMMAND', no=0)

logger.remove() # Don't output anything if this is just being imported

def enable_logging(target_logger: 'loguru.Logger', stdout_level: str='INFO') -> tuple[int, int]:
    """Adds handlers (after clearing previous ones) to the given `loguru` logger and returns their `int` identifiers.

    :param target_logger: `loguru.Logger` to add handles to.
    :param stdout_level: What level to set the `stdout` stream's handler to. Defaults to "INFO".

    :returns: stdout handler ID, file handler ID
    :rtype: int
    """
    target_logger.remove()

    target_logger.level('WARNING', color='<yellow>')
    target_logger.level('ERROR', color='<red>')

    stdout_handler = target_logger.add(sys.stdout, colorize=True,
        format="<level>[{time:HH:mm:ss}] {level}: {message}</level>", level=stdout_level, diagnose=False)
    file_handler = target_logger.add(LOGS_DIR / '{time:YYYY-MM-DD_HH-mm-ss}.log',
        format="[{time:HH:mm:ss}] {level}: {message}", level='DEBUG', mode='w', retention=5, diagnose=False)

    return stdout_handler, file_handler
