"""
Handles building the main GUI layout.
"""

from math import floor
from pprint import pprint
from typing import Any, Callable

import dearpygui.dearpygui as dpg

from squaremap_combine.gui import actions
from squaremap_combine.gui.models import UserData
from squaremap_combine.project import LOGS_DIR, PROJECT_VERSION, USER_DATA_DIR

PRIMARY_WINDOW_INIT_SIZE = 1000, 800
MODAL_DIALOG_MAX_SIZE = floor(PRIMARY_WINDOW_INIT_SIZE[0] / 1.5), floor(PRIMARY_WINDOW_INIT_SIZE[1] / 1.5)
CONSOLE_TEXT_WRAP = 780
SPACER_HEIGHT = 10

MESSAGE_NO_DIR = 'None to display; choose a valid tiles directory above.'

class ElemGroup:
    """Class that allows putting individual items into named groups, primarily for batch operations on multiple items.
    The class is not meant to be instanced; it holds one private `_groups` attribute can be accessed and modified with
    the provided class methods.
    """
    _groups: dict[str, list[int | str]] = {}

    @classmethod
    def add(cls, groups: str | list[str], item: int | str) -> int | str:
        """Adds a `dearpygui` item to the named group.

        :param groups: Group to add this item to. If it does not exist, it will be created.
            Can either be a single group name, or a list of multiple groups to add to.
        :param item: Item `int` or `str` identifier to add to the named group.
        :returns: The `item` originally passed to this method.
        :rtype: int | str
        """
        if isinstance(groups, str):
            groups = [groups]
        for g in groups:
            if g not in cls._groups:
                cls._groups[g] = []
            cls._groups[g].append(item)
        return item

    @classmethod
    def get(cls, group_name: str) -> list[int | str]:
        """Retrieves a list of items within the named group. An empty list is returned if the group does not exist."""
        return cls._groups.get(group_name, [])

    @classmethod
    def action(cls, group_name: str, func: Callable, *args: Any, **kwargs: Any):
        """Calls the given `func` for every item in the named group, using each item's identifier as the first argument.
        Additional arguments can be supplied after `func` and will be passed to it.

        :param group_name: Group to iterate through and call `func` on each member of.
        :param func: A `Callable` that will use the current item of the loop as its first argument.
        :param args: Additional positional arguments that will be passed to `func` after its initial item argument.
        :param kwargs: Keyword arguments that will be passed to `func` after its initial item argument.
        """
        for item in cls.get(group_name):
            func(item, *args, **kwargs)

    @classmethod
    def visibility(cls, group_name: str, value: bool):
        """Sets the `show` keyword of every item in the named group to the given `bool`."""
        cls.action(group_name, dpg.configure_item, show=value)

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
        dpg.add_spacer(height=SPACER_HEIGHT)

        # Tiles directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Tiles directory:')
            ElemGroup.add(['img-required', 'image-settings'], dpg.add_input_text(tag='tiles-dir-input', default_value='', width=700,
                callback=actions.validate_tiles_dir_callback, on_enter=True))
        dpg.add_button(tag='tiles-dir-button', label='Choose folder...', callback=actions.dir_dialog_callback,
            user_data=UserData(
                cb_display_with='tiles-dir-input',
                cb_forward_to=actions.validate_tiles_dir
            ))

        # World selection
        dpg.add_text('World:')
        dpg.add_text(tag='world-no-valid-dir', default_value=MESSAGE_NO_DIR)
        ElemGroup.add(['img-required', 'image-settings'], dpg.add_radio_button(tag='world-choices', items=[], show=False,
            callback=actions.update_detail_choices_callback))

        # Detail selection
        dpg.add_text('Map detail level:')
        dpg.add_text(tag='detail-invalid', default_value=MESSAGE_NO_DIR)
        ElemGroup.add(['img-required', 'image-settings'],
            dpg.add_radio_button(tag='detail-choices', items=[], show=False, horizontal=True))

        # Output directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Output directory:')
            ElemGroup.add(['img-required', 'image-settings'], dpg.add_input_text(tag='out-dir-input', default_value='', width=700))
        dpg.add_button(tag='out-dir-button', label='Choose folder...', callback=actions.dir_dialog_callback,
            user_data=UserData(cb_display_with='out-dir-input'))

    def secondary_tab_content():
        dpg.add_spacer(height=SPACER_HEIGHT)

        # Output extension
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Output format:')
            ElemGroup.add('image-settings', dpg.add_input_text(tag='output-ext-input', width=75, default_value='png'))

        # Timestamp format
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='timestamp-checkbox'))
            dpg.add_text(default_value='Add timestamp to filename')

        with dpg.group(tag='timestamp-format-input-group', horizontal=True):
            ElemGroup.add('timestamp-opts', dpg.add_text(default_value='Timestamp format:'))
            ElemGroup.add(['image-settings', 'timestamp-opts'],
                dpg.add_input_text(tag='timestamp-format-input', width=300))

        with dpg.group(tag='timestamp-format-preview-group', horizontal=True):
            ElemGroup.add('timestamp-opts', dpg.add_text(default_value='Timestamp Preview:'))
            ElemGroup.add('timestamp-opts', dpg.add_text(tag='timestamp-format-preview', default_value=''))

        # Autotrim
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='autotrim-checkbox', default_value=True))
            dpg.add_text(default_value='Trim empty areas of the map')

        # Area to render
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='area-checkbox'))
            dpg.add_text(default_value='Export a specific area of the world')
        ElemGroup.add('area-opts', dpg.add_text(default_value='Enter the top-left and bottom-right coordinates of the area you want:',
            show=False))
        ElemGroup.add(['image-settings', 'area-opts'], dpg.add_input_intx(tag='area-coord-input', size=4, width=300))

        # Force output size
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='force-size-checkbox'))
            dpg.add_text(default_value='Crop final image size')
        ElemGroup.add('force-size-opts', dpg.add_text(default_value='Enter the desired width and height:'))
        ElemGroup.add(['image-settings', 'force-size-opts'], dpg.add_input_intx(tag='force-size-input', size=2, width=150))

        # Grid overlay
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='grid-overlay-checkbox'))
            dpg.add_text(default_value='Add a grid overlay to the image')
        ElemGroup.add('grid-opts', dpg.add_text(default_value='Enter the X and Y coordinate intervals for the grid:'))
        ElemGroup.add(['image-settings', 'grid-opts'], dpg.add_input_intx(tag='grid-interval-input', size=2, width=150))

        with dpg.group(horizontal=True):
            ElemGroup.add(['image-settings', 'grid-opts'], dpg.add_checkbox(tag='grid-show-lines-checkbox'))
            ElemGroup.add('grid-opts', dpg.add_text(default_value='Show grid lines'))
        with dpg.group(horizontal=True):
            ElemGroup.add(['image-settings', 'grid-opts'], dpg.add_checkbox(tag='grid-show-coords-checkbox'))
            ElemGroup.add('grid-opts', dpg.add_text(default_value='Show grid coordinates'))
        with dpg.group(horizontal=True):
            ElemGroup.add(['grid-opts', 'grid-coord-opts'], dpg.add_text(default_value='Coordinates format:'))
            ElemGroup.add(['image-settings', 'grid-opts', 'grid-coord-opts'], dpg.add_input_text(
                tag='grid-coords-format-input', default_value='({x}, {y})'))

    def app_settings_tab_content():
        dpg.add_spacer(height=SPACER_HEIGHT)

        with dpg.group(horizontal=True):
            ElemGroup.add('app-settings', dpg.add_checkbox(tag='autosave-opts-checkbox', default_value=False))
            dpg.add_text(default_value='Store settings on exit, and load them on startup')
        dpg.add_spacer(height=SPACER_HEIGHT)
        dpg.add_button(label='Save Preferences', callback=actions.save_app_options)
        dpg.add_spacer(height=SPACER_HEIGHT)
        dpg.add_separator()
        dpg.add_spacer(height=SPACER_HEIGHT)
        with dpg.group(horizontal=True):
            dpg.add_button(label='Open logs folder', callback=lambda: actions.open_window_at_path(LOGS_DIR))
            dpg.add_button(label='Open user data folder', callback=lambda: actions.open_window_at_path(USER_DATA_DIR))

    def debug_tab_content():
        dpg.add_spacer(height=SPACER_HEIGHT)

        dpg.add_button(label='Open style editor', callback=dpg.show_style_editor)
        dpg.add_button(label='Modal dialog, notice', callback=actions.open_notice_dialog_callback,
            user_data=UserData(other='Notice message body.'))
        dpg.add_button(label='Modal dialog, confirmation', callback=actions.open_confirm_dialog_callback,
            user_data=UserData(other='Confirmation message body.'))
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Last confirmation dialog response:')
            dpg.add_text(tag='debug-conf-response-text', default_value='')
        dpg.add_button(label='Show progress bar', callback=lambda: dpg.configure_item('progress-bar', show=True))
        dpg.add_button(label='Hide progress bar', callback=lambda: dpg.configure_item('progress-bar', show=False))
        dpg.add_text(default_value='Progress bar value:')
        dpg.add_input_text(on_enter=True, callback=lambda s,a,d: dpg.configure_item('progress-bar', default_value=float(a)))
        dpg.add_button(label='Print element groups', callback=lambda: pprint(ElemGroup._groups)) # pylint: disable=protected-access
        dpg.add_button(label='Print image settings group',
            callback=lambda: pprint(ElemGroup._groups['image-settings'])) # pylint: disable=protected-access
        dpg.add_button(label='Print gathered image options',
            callback=lambda: pprint(actions.get_image_options()))

    # Primary window
    with dpg.window(tag='main-window'):
        dpg.add_text(tag='title-text', default_value=f'squaremap_combine v{PROJECT_VERSION}')
        dpg.add_spacer(height=SPACER_HEIGHT)

        # Tabs
        with dpg.group(tag='tabs-group'):
            with dpg.tab_bar(tag='tabs'):
                with dpg.tab(tag='tab-primary', label='Basics'):
                    primary_tab_content()
                with dpg.tab(tag='tab-secondary', label='Additional Options'):
                    secondary_tab_content()
                with dpg.tab(tag='tab-app-settings', label='App Preferences & Misc.'):
                    app_settings_tab_content()
                if debugging:
                    with dpg.tab(tag='tab-debug', label='Debug'):
                        debug_tab_content()

        # End options
        dpg.add_spacer(height=SPACER_HEIGHT)
        dpg.add_separator()
        dpg.add_spacer(height=SPACER_HEIGHT)

        dpg.add_button(label='Start', width=-1, callback=actions.create_image_callback)

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
