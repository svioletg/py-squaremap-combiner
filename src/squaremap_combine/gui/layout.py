"""
Handles building the main GUI layout.
"""

from math import floor

import dearpygui.dearpygui as dpg

from squaremap_combine.gui import actions
from squaremap_combine.gui.models import UserData
from squaremap_combine.project import PROJECT_VERSION

PRIMARY_WINDOW_INIT_SIZE = 1000, 800
MODAL_DIALOG_MAX_SIZE = floor(PRIMARY_WINDOW_INIT_SIZE[0] / 1.5), floor(PRIMARY_WINDOW_INIT_SIZE[1] / 1.5)
CONSOLE_TEXT_WRAP = 780
SPACER_HEIGHT = 10

MESSAGE_NO_DIR = 'None to display; choose a valid tiles directory above.'

def build_layout():
    """Builds the basic GUI app layout."""
    #region INTERNAL USE / STORAGE
    with dpg.window(tag='script-storage', show=False):
        dpg.add_text(tag='modal-confirm-value', default_value='')
    #endregion INTERNAL USE / STORAGE

    #region LAYOUT
    # Modal confirmation dialog
    with dpg.window(tag='modal-confirm', label='User confirmation needed', modal=True, show=False,
        no_resize=True, pos=(200, 200), no_close=True, max_size=MODAL_DIALOG_MAX_SIZE):
        dpg.add_text(tag='modal-confirm-message', default_value='Continue?', wrap=MODAL_DIALOG_MAX_SIZE[0] - 50)

        dpg.add_spacer(height=SPACER_HEIGHT)

        with dpg.group(horizontal=True):
            dpg.add_button(tag='yes-button', label='Yes', width=75, callback=actions.close_confirm_dialog)
            dpg.add_button(tag='no-button', label='No', width=75, callback=actions.close_confirm_dialog)

    with dpg.item_handler_registry(tag='widget-handler'):
        dpg.add_item_resize_handler(callback=actions.center_in_window_callback, user_data=UserData(other=('modal-confirm', 'main-window')))
    dpg.bind_item_handler_registry('modal-confirm', 'widget-handler')

    # Primary window
    with dpg.window(tag='main-window'):
        dpg.add_text(default_value=f'squaremap_combine v{PROJECT_VERSION}')
        dpg.add_separator()

        # Tiles directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Tiles directory:')
            dpg.add_text(tag='tiles-dir-label', default_value='None chosen; click the button below to select one', wrap=640)
        dpg.add_button(tag='tiles-dir-button', label='Choose folder...', callback=actions.dir_dialog,
                        user_data=UserData(display='tiles-dir-label', forward=actions.validate_tiles_dir))

        # World selection
        dpg.add_text('World:')
        dpg.add_text(tag='world-no-valid-dir', default_value=MESSAGE_NO_DIR)
        dpg.add_radio_button(tag='world-choices', items=[], show=False, callback=actions.update_detail_choices_callback)

        # Detail selection
        dpg.add_text('Map detail level:')
        dpg.add_text(tag='detail-invalid', default_value=MESSAGE_NO_DIR)
        dpg.add_radio_button(tag='detail-choices', items=[], show=False, horizontal=True)

        # Output directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Output directory:')
            dpg.add_text(tag='out-dir-label', default_value='None chosen; click the button below to select one', wrap=640)
        dpg.add_button(tag='out-dir-button', label='Choose folder...', callback=actions.dir_dialog,
                        user_data=UserData(display='out-dir-label'))

        # End options
        dpg.add_button(label='Ask', callback=actions.open_confirm_dialog_callback, user_data=UserData(other='More than 50,000 grid intervals will be iterated over, which can take a very long time.' +
                ' Continue?'))
        dpg.add_button(label='Start', callback=actions.create_image_callback)

        dpg.add_spacer(height=SPACER_HEIGHT)
        dpg.add_separator()
        dpg.add_spacer(height=SPACER_HEIGHT)

        # Log ouptut window
        dpg.add_text('Combiner output:')
        with dpg.child_window(tag='console-output-window', height=200):
            dpg.add_text(tag='console-output-text', default_value='(Nothing has run.)', wrap=CONSOLE_TEXT_WRAP)

        dpg.add_progress_bar(tag='progress-bar', width=-1, show=False)
    #endregion LAYOUT
