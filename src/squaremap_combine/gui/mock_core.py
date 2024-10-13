"""
Made with the sole purpose of being able to test certain actions in the GUI app without actually
needing to use the real contents of the `combine_core` module. No functions in this module
should produce any actual output aside from returning a value - no saving of files to disk, for example.
"""

import time

from tqdm import tqdm
from tqdm.contrib.itertools import product

from squaremap_combine.combine_core import logger


def combine():
    logger.log('GUI_COMMAND', '/pbar set 0')
    for n in (pbar := tqdm(range(300))):
        logger.log('GUI_COMMAND', f'/pbar set {pbar.n / pbar.total}')
    logger.log('GUI_COMMAND', '/pbar set 1')
    for x, y in product(range(-3, 3), range(-3, 3)):
        logger.info(f'Rendering: {x}, {y}')
    return x, y
