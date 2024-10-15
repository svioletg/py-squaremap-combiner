"""
Main GUI entrypoint which will open the app.
"""

import json
import sys
from pathlib import Path

import dearpygui.dearpygui as dpg

from squaremap_combine.combine_core import logger
from squaremap_combine.gui import actions, layout, styling
from squaremap_combine.helper import enable_logging
from squaremap_combine.project import (APP_SETTINGS_PATH, GUI_ASSET_DIR, OPT_AUTOSAVE_PATH, PROJECT_VERSION,
                                       USER_DATA_DIR)


def main(): # pylint: disable=missing-function-docstring
    DEBUG_MODE = 'debug' in sys.argv # pylint: disable=invalid-name

    stdout_handler, file_handler = enable_logging(logger, 'DEBUG' if DEBUG_MODE else 'INFO') # pylint: disable=unused-variable

    if DEBUG_MODE:
        logger.info('DEBUG_MODE is enabled.')

    logger.info('Ensuring data user directory exists...')
    Path.mkdir(USER_DATA_DIR, parents=True, exist_ok=True)

    logger.info(f'squaremap_combine v{PROJECT_VERSION}')

    logger.info('Preparing GUI...')

    window_size = layout.PRIMARY_WINDOW_INIT_SIZE

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

    if APP_SETTINGS_PATH.is_file():
        logger.info('Loading app preferences...')
        with open(APP_SETTINGS_PATH, 'r', encoding='utf-8') as f:
            actions.set_app_options(json.load(f))

    allow_autosave: bool = dpg.get_value('autosave-opts-checkbox')
    if allow_autosave and OPT_AUTOSAVE_PATH.is_file():
        logger.info('Loading autosaved image settings...')
        with open(OPT_AUTOSAVE_PATH, 'r', encoding='utf-8') as f:
            actions.set_image_options(json.load(f))

    logger.info('Applying themes...')
    styling.apply_themes()

    logger.info('Configuring fonts...')
    styling.configure_fonts()

    logger.info('Setting icon...')
    dpg.set_viewport_small_icon(str(GUI_ASSET_DIR / 'icon.ico'))
    dpg.set_viewport_large_icon(str(GUI_ASSET_DIR / 'icon.ico'))

    logger.info('Starting dearpygui...')
    dpg.show_viewport()
    dpg.set_primary_window('main-window', True)

    logger.add(actions.update_console, format='<level>{level}: {message}</level>', level='GUI_COMMAND')
    dpg.start_dearpygui()

    logger.info('Window closed.')

    if allow_autosave:
        logger.info(f'Saving currently set options to: {OPT_AUTOSAVE_PATH}')
        opt_dict = actions.get_image_options()
        with open(OPT_AUTOSAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(opt_dict, f)

    logger.info('Exiting...')
    dpg.destroy_context()
