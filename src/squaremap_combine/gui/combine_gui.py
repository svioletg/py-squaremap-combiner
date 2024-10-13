"""
Main GUI entrypoint which will open the app.
"""

import dearpygui.dearpygui as dpg

from squaremap_combine.combine_core import logger
from squaremap_combine.gui import actions, layout, styling
from squaremap_combine.helper import enable_logging
from squaremap_combine.project import GUI_ASSETS, PROJECT_VERSION


def main(): # pylint: disable=missing-function-docstring
    stdout_handler, file_handler = enable_logging(logger) # pylint: disable=unused-variable

    logger.info(f'squaremap_combine v{PROJECT_VERSION}')

    logger.info('Preparing GUI...')

    window_size = 1000, 800

    dpg.create_context()
    dpg.create_viewport(title='squaremap_combine GUI',
        width=window_size[0],
        height=window_size[1],
        x_pos=100,
        y_pos=100
    )
    dpg.setup_dearpygui()

    logger.info('Building layout...')
    layout.build_layout()

    logger.info('Building themes...')
    styling.apply_themes()

    logger.info('Adding fonts...')
    styling.apply_fonts()

    # dpg.show_style_editor()

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
