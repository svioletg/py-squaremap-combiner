"""
Main GUI entrypoint which will open the app.
"""

import dearpygui.dearpygui as dpg

from squaremap_combine.combine_core import logger
from squaremap_combine.gui import actions, layout
from squaremap_combine.gui.themes import Themes
from squaremap_combine.helper import enable_logging
from squaremap_combine.project import MODULE_DIR, PROJECT_VERSION

ASSETS = MODULE_DIR / 'gui/asset'

def main(): # pylint: disable=missing-function-docstring
    stdout_handler, file_handler = enable_logging(logger) # pylint: disable=unused-variable

    logger.info(f'squaremap_combine v{PROJECT_VERSION}')

    logger.info('Preparing GUI...')

    # Tkinter is only used to get the screen size and center the window
    # root = Tk()
    # root.withdraw()

    # screen_center = root.winfo_screenwidth() // 2, root.winfo_screenheight() // 2
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
    themes = Themes()
    dpg.bind_theme(themes.base)
    dpg.bind_item_theme('console-output-window', themes.console)

    logger.info('Adding fonts...')
    with dpg.font_registry():
        BASE_FONT = dpg.add_font(str(ASSETS / 'PTSans-Regular.ttf'), 22) # pylint: disable=invalid-name
        MONO_FONT = dpg.add_font(str(ASSETS / 'SourceCodePro-SemiBold.ttf'), 20) # pylint: disable=invalid-name

    dpg.bind_font(BASE_FONT)
    dpg.bind_item_font('console-output-window', MONO_FONT)

    # dpg.show_style_editor()

    logger.info('Setting icon...')
    dpg.set_viewport_small_icon(str(ASSETS / 'icon.ico'))
    dpg.set_viewport_large_icon(str(ASSETS / 'icon.ico'))

    logger.info('Starting dearpygui...')
    dpg.show_viewport()
    dpg.set_primary_window('main-window', True)

    logger.add(actions.update_console, format='<level>{level}: {message}</level>', level='GUI_COMMAND')
    dpg.start_dearpygui()

    logger.info('Window closed; exiting...')
    dpg.destroy_context()
