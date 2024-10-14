"""
Handles building the main GUI layout.
"""

from math import floor

import dearpygui.dearpygui as dpg

from squaremap_combine.combine_core import logger
from squaremap_combine.gui import actions
from squaremap_combine.gui.models import UserData
from squaremap_combine.project import PROJECT_VERSION

PRIMARY_WINDOW_INIT_SIZE = 1000, 800
MODAL_DIALOG_MAX_SIZE = floor(PRIMARY_WINDOW_INIT_SIZE[0] / 1.5), floor(PRIMARY_WINDOW_INIT_SIZE[1] / 1.5)
CONSOLE_TEXT_WRAP = 780
SPACER_HEIGHT = 10

MESSAGE_NO_DIR = 'None to display; choose a valid tiles directory above.'

def build_layout(debugging: bool=False):
    """Builds the basic GUI app layout.
    
    :param debugging: If `True`, this will enable the "Debug" tab, and set the `sys.stdout` log handler's level to "DEBUG".
    """
    #region LAYOUT
    # Modal notice box
    with dpg.window(tag='modal-notice', label='Notice', modal=True, show=False, no_resize=True, max_size=MODAL_DIALOG_MAX_SIZE):
        dpg.add_text(tag='modal-notice-message', wrap=MODAL_DIALOG_MAX_SIZE[0] - 50)
        dpg.add_spacer(height=SPACER_HEIGHT)
        dpg.add_button(tag='ok-button', label='OK', width=75, callback=actions.close_notice_dialog_callback)

    # Modal confirmation dialog
    with dpg.window(tag='modal-confirm', label='User confirmation needed', modal=True, show=False, no_resize=True,
        no_close=True, max_size=MODAL_DIALOG_MAX_SIZE):
        dpg.add_text(tag='modal-confirm-message', default_value='Continue?', wrap=MODAL_DIALOG_MAX_SIZE[0] - 50)
        dpg.add_spacer(height=SPACER_HEIGHT)
        with dpg.group(horizontal=True):
            dpg.add_button(tag='yes-button', label='Yes', width=75, callback=actions.close_confirm_dialog_callback)
            dpg.add_button(tag='no-button', label='No', width=75, callback=actions.close_confirm_dialog_callback)

    def primary_tab_content():
        # Tiles directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Tiles directory:')
            dpg.add_input_text(tag='tiles-dir-label', default_value='', width=700,
                callback=actions.validate_tiles_dir_callback, on_enter=True)
        dpg.add_button(tag='tiles-dir-button', label='Choose folder...', callback=actions.dir_dialog_callback,
            user_data=UserData(
                cb_display_with='tiles-dir-label',
                cb_forward_to=actions.validate_tiles_dir
            ))

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
            dpg.add_input_text(tag='out-dir-label', default_value='', width=700)
        dpg.add_button(tag='out-dir-button', label='Choose folder...', callback=actions.dir_dialog_callback,
            user_data=UserData(cb_display_with='out-dir-label'))

    def secondary_tab_content():
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Output format:')
            dpg.add_input_text(tag='output-ext-input', width=75, default_value='png')

        with dpg.group(horizontal=True):
            dpg.add_checkbox(tag='timestamp-checkbox',
                callback=lambda s,a,d: dpg.configure_item('timestamp-format-input', enabled=a))
            dpg.add_text(default_value='Add timestamp to filename?')

        with dpg.group(tag='timestamp-format-input-group', horizontal=True):
            dpg.add_text(default_value='Timestamp format:')
            dpg.add_input_text(tag='timestamp-format-input', width=300, enabled=False)

        with dpg.group(tag='timestamp-format-preview-group', horizontal=True):
            dpg.add_text(default_value='Timestamp Preview:')
            dpg.add_text(tag='timestamp-format-preview', default_value='')

        with dpg.group(horizontal=True):
            dpg.add_checkbox(tag='autotrim-checkbox')
            dpg.add_text(default_value='Trim empty areas of the map?')

    def debug_tab_content():
        dpg.add_button(label='Modal dialog, notice', callback=actions.open_notice_dialog_callback,
            user_data=UserData(other='Notice message body.'))
        dpg.add_button(label='Modal dialog, confirmation', callback=actions.open_confirm_dialog_callback,
            user_data=UserData(other='Confirmation message body.'))
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Last confirmation dialog response:')
            dpg.add_text(tag='debug-conf-response-text', default_value='')

    # Primary window
    with dpg.window(tag='main-window'):
        dpg.add_text(tag='title-text', default_value=f'squaremap_combine v{PROJECT_VERSION}')
        dpg.add_spacer(height=SPACER_HEIGHT)

        # Tabs
        with dpg.group(tag='tabs-group'):
            with dpg.tab_bar(tag='tabs'):
                with dpg.tab(tag='tab-primary', label='Basic'):
                    primary_tab_content()
                with dpg.tab(tag='tab-secondary', label='Additional Options'):
                    secondary_tab_content()
                if debugging:
                    with dpg.tab(tag='tab-debug', label='Debug'):
                        debug_tab_content()

        # End options
        dpg.add_spacer(height=SPACER_HEIGHT)
        dpg.add_separator()
        dpg.add_spacer(height=SPACER_HEIGHT)

        dpg.add_button(label='Start', callback=actions.create_image_callback)

        # Log ouptut window
        dpg.add_text('Combiner output:')
        with dpg.child_window(tag='console-output-window', height=200, user_data={'allow-output': False}):
            pass

        dpg.add_progress_bar(tag='progress-bar', width=-1, show=False)
    #endregion LAYOUT

    #region EVENT HANDLERS
    with dpg.handler_registry(tag='handler-reg'):
        dpg.add_key_press_handler(-1, callback=actions.timestamp_format_updated_callback)

    with dpg.item_handler_registry(tag='widget-handler'):
        dpg.add_item_resize_handler(callback=actions.center_in_window_callback,
            user_data=UserData(other=('modal-notice', 'main-window')))
        dpg.add_item_resize_handler(callback=actions.center_in_window_callback,
            user_data=UserData(other=('modal-confirm', 'main-window')))

    dpg.bind_item_handler_registry('modal-notice', 'widget-handler')
    dpg.bind_item_handler_registry('modal-confirm', 'widget-handler')
    #endregion EVENT HANDLERS
