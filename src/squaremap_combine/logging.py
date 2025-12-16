import sys
from pathlib import Path

from loguru import logger

from squaremap_combine.const import LOGS_DIR

logger.level('GUI_COMMAND', no=0)

logger.remove()

def enable_logging(stdout_level: str = 'INFO', output_dir: Path = LOGS_DIR) -> tuple[int, int]:
    """Adds handlers (after clearing previous ones) to the given `loguru` logger and returns their identifiers.

    :param stdout_level: What level to set the `stdout` stream's handler to. Defaults to "INFO".
    :param output_dir: Specify what directory log files should be stored in for this logger.
        Defaults to the value of `squaremap_combine.project.LOGS_DIR`.

    :returns handlers: stdout handler ID, file handler ID
    """
    logger.remove()

    logger.level('WARNING', color='<yellow>')
    logger.level('ERROR', color='<red>')

    stdout_handler: int = logger.add(sys.stdout, colorize=True,
        format='<level>[{time:HH:mm:ss} {level}] {message}</level>', level=stdout_level, diagnose=False)
    file_handler: int = logger.add(output_dir / '{time:YYYY-MM-DD_HH-mm-ss}.log',
        format='[{time:HH:mm:ss}] {level}: {message}', level='DEBUG', mode='w', retention=5, diagnose=False)

    return stdout_handler, file_handler
