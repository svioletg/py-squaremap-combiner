"""
Main GUI entrypoint which will open the app.
"""

import sys

import dearpygui.dearpygui as dpg

from squaremap_combine.combine_core import logger
from squaremap_combine.gui import actions, layout, styling
from squaremap_combine.helper import enable_logging
from squaremap_combine.project import GUI_ASSETS, PROJECT_VERSION


def main(): # pylint: disable=missing-function-docstring
    DEBUG_MODE = 'debug' in sys.argv # pylint: disable=invalid-name

    stdout_handler, file_handler = enable_logging(logger, 'DEBUG' if DEBUG_MODE else 'INFO') # pylint: disable=unused-variable

    if DEBUG_MODE:
        logger.info('DEBUG_MODE is enabled.')

    logger.info(f'squaremap_combine v{PROJECT_VERSION}')

    logger.info('Preparing GUI...')

    window_size = 1000, 800

    dpg.create_context()
    dpg.create_viewport(title='squaremap_combine GUI',
        width=window_size[0],
        height=window_size[1],
        x_pos=300,
        y_pos=100
    )
    dpg.setup_dearpygui()

    logger.info('Building layout...')
    layout.build_layout(DEBUG_MODE)

    logger.info('Applying themes...')
    styling.apply_themes()

    logger.info('Configuring fonts...')
    styling.configure_fonts()

    logger.info('Setting icon...')
    dpg.set_viewport_small_icon(str(GUI_ASSETS / 'icon.ico'))
    dpg.set_viewport_large_icon(str(GUI_ASSETS / 'icon.ico'))

    logger.info('Starting dearpygui...')
    dpg.show_viewport()
    dpg.set_primary_window('main-window', True)

    logger.add(actions.update_console, format='<level>{level}: {message}</level>', level='GUI_COMMAND')
    dpg.start_dearpygui()

    logger.info('Window closed; exiting...')
    dpg.destroy_context()
