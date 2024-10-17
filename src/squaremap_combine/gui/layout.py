"""
Handles building the main GUI layout.
"""

import json
import webbrowser
from dataclasses import asdict
from math import floor
from pprint import pprint
from typing import Any, Callable, cast

import dearpygui.dearpygui as dpg

from squaremap_combine.combine_core import CombinerStyle, Coord2i, logger
from squaremap_combine.gui import actions
from squaremap_combine.gui.models import UserData
from squaremap_combine.helper import Color
from squaremap_combine.project import LOGS_DIR, PROJECT_DOCS_URL, PROJECT_VERSION, USER_DATA_DIR

PRIMARY_WINDOW_INIT_SIZE = 1000, 800
MODAL_DIALOG_MAX_SIZE = 8000, 400
CONSOLE_TEXT_WRAP = 780
SPACER_HEIGHT = 10
INDENT_WIDTH = 50

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

def main_window_center() -> Coord2i:
    """Returns the center coordinate of the main window."""
    return Coord2i(dpg.get_item_width('main-window') or 0, dpg.get_item_height('main-window') or 0) // 2

def build_combiner_style_editor():
    """Auto-generates a visual editor for the `CombinerStyle` class
    based on the types of its attributes.
    """
    input_mapping: dict[type, dict[str, Callable | str | dict[str, Any]]] = {
        # TODO: 'suffix' keys should be standardized in a dataclass or similar, and this should use that system instead (Issue #8)
        str   : {'call': dpg.add_input_text},
        bool  : {'call': dpg.add_checkbox},
        int   : {'call': dpg.add_input_int},
        Color : {'call': dpg.add_color_picker,
            'kwargs': {
                'width': 150, 'height': 150,
                'input_mode': dpg.mvColorEdit_input_rgb,
                'alpha_bar': True,
                'no_side_preview': True
            }
        }
    }

    with dpg.group(horizontal=True):
        dpg.add_text(default_value='For descriptions of each value, see the online docs:')
        dpg.add_button(label='Open docs in browser',
            callback=lambda: webbrowser.open(PROJECT_DOCS_URL + 'squaremap_combine/combine_core.html#CombinerStyle'))

    style_base = CombinerStyle()
    for attr, val in asdict(style_base).items():
        cls = type(val)
        dpg.add_text(default_value=attr.title().replace('_', ' '))
        with dpg.tooltip(parent=dpg.last_item()):
            dpg.add_text(default_value=attr)
        if cls not in input_mapping:
            item = dpg.add_input_text
            logger.warning(f'Type {cls!r} does not have an associated dearpygui input.')
        else:
            item = cast(Callable, input_mapping[cls]['call'])
        item_kwargs = cast(dict[str, Any], input_mapping[cls].get('kwargs', {}))
        # tag_suffix = input_mapping[cls].get('suffix', 'input')
        ElemGroup.add('combiner-style-settings', item(tag=f'{attr}-styleattr-input', **item_kwargs))

    with dpg.group(horizontal=True):
        dpg.add_button(label='Save to file...', callback=actions.file_save_dialog_callback,
            user_data=UserData(other={'initialfile': 'style.json'}, cb_forward_to=(actions.save_style_options, lambda *args: None)))
        dpg.add_button(label='Load from file...', callback=actions.file_open_dialog_callback,
            user_data=UserData(cb_forward_to=(actions.load_style_options, lambda *args: None)))
        dpg.add_button(label='Reset to default', callback=lambda: actions.set_style_options(json.loads(style_base.to_json())))

    # Load default
    actions.set_style_options(json.loads(style_base.to_json()))

def build_layout(debugging: bool=False):
    """Builds the basic GUI app layout.

    :param debugging: If `True`, this will enable the "Debug" tab, and set the `sys.stdout` log handler's level to "DEBUG".
    """
    #region LAYOUT
    # Modal notice box
    with dpg.window(tag='blocking-modal', modal=True, show=False, no_resize=True, no_move=True, no_close=True):
        dpg.add_text(default_value='Waiting for external response...')

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

    # Combiner style editor window
    with dpg.window(tag='combiner-style-editor', label='Edit combiner styling', width=800, height=600, show=False):
        build_combiner_style_editor()

    def primary_tab_content():
        dpg.add_spacer(height=SPACER_HEIGHT)

        # Tiles directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Tiles directory:')
            ElemGroup.add(['img-required', 'image-settings'], dpg.add_input_text(tag='tiles-dir-input', default_value='', width=700,
                callback=actions.validate_tiles_dir_callback, on_enter=True))
        dpg.add_button(tag='tiles-dir-button', label='Choose folder...', callback=actions.dir_dialog_callback,
            user_data=UserData(
                cb_display_with=('tiles-dir-input', None),
                cb_forward_to=(actions.validate_tiles_dir, lambda *args: None)
            ))

        # World selection
        dpg.add_text('World:')
        dpg.add_text(tag='world-no-valid-dir', default_value=MESSAGE_NO_DIR)
        ElemGroup.add(['img-required', 'image-settings'], dpg.add_radio_button(tag='world-choices', items=[], show=False,
            callback=actions.update_detail_choices_callback))

        # Detail selection
        dpg.add_text('Map detail level:')
        with dpg.tooltip(parent=dpg.last_item()):
            dpg.add_text(default_value='Higher number indicates higher detail, and thus a larger final image.\n' +
                '3 represents one block per pixel, so an exact block-by-block view of the world.\n' +
                '2 stores a 2x2 block square area per pixel. 1 is 4x4 blocks per pixel, and 0 is 8x8 blocks per pixel.'
            )
        dpg.add_text(tag='detail-invalid', default_value=MESSAGE_NO_DIR)
        ElemGroup.add(['img-required', 'image-settings'],
            dpg.add_radio_button(tag='detail-choices', items=[], show=False, horizontal=True))

        # Output directory
        with dpg.group(horizontal=True):
            dpg.add_text(default_value='Output directory:')
            ElemGroup.add(['img-required', 'image-settings'], dpg.add_input_text(tag='out-dir-input', default_value='', width=700))
        dpg.add_button(tag='out-dir-button', label='Choose folder...', callback=actions.dir_dialog_callback,
            user_data=UserData(cb_display_with=('out-dir-input', None)))

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

        with dpg.group(tag='timestamp-format-input-group', horizontal=True, indent=1 * INDENT_WIDTH):
            ElemGroup.add('timestamp-opts', dpg.add_text(default_value='Timestamp format:'))
            ElemGroup.add(['image-settings', 'timestamp-opts'],
                dpg.add_input_text(tag='timestamp-format-input', width=300))

        with dpg.group(tag='timestamp-format-preview-group', horizontal=True, indent=1 * INDENT_WIDTH):
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
            show=False, indent=1 * INDENT_WIDTH))
        with dpg.tooltip(parent=dpg.last_item()):
            dpg.add_text(default_value='Area coordinates should be the coordinates of an area as they would be in Minecraft,' +
                ' regardless of the selected detail level.\n'
            )
        ElemGroup.add(['image-settings', 'area-opts'],
            dpg.add_input_intx(tag='area-coord-input', size=4, width=300, indent=1 * INDENT_WIDTH))

        # Force output size
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='force-size-checkbox'))
            dpg.add_text(default_value='Crop final image size')
        ElemGroup.add('force-size-opts', dpg.add_text(default_value='Enter the desired width and height:', indent=1 * INDENT_WIDTH))
        ElemGroup.add(['image-settings', 'force-size-opts'],
            dpg.add_input_intx(tag='force-size-input', size=2, width=150, indent=1 * INDENT_WIDTH))

        # Grid overlay
        with dpg.group(horizontal=True):
            ElemGroup.add('image-settings', dpg.add_checkbox(tag='grid-overlay-checkbox'))
            dpg.add_text(default_value='Add a grid overlay to the image')
        ElemGroup.add('grid-opts', dpg.add_text(default_value='Enter the X and Y coordinate intervals for the grid:', indent=1 * INDENT_WIDTH))
        ElemGroup.add(['image-settings', 'grid-opts'],
            dpg.add_input_intx(tag='grid-interval-input', size=2, width=150, indent=1 * INDENT_WIDTH))

        with dpg.group(indent=1 * INDENT_WIDTH):
            ElemGroup.add('grid-opts', dpg.add_text(
                default_value='(See style options at the bottom to toggle grid lines and/or coordinates text)'))
        with dpg.group(horizontal=True, indent=1 * INDENT_WIDTH):
            ElemGroup.add(['grid-opts', 'grid-coord-opts'], dpg.add_text(default_value='Coordinates format:'))
            ElemGroup.add(['image-settings', 'grid-opts', 'grid-coord-opts'], dpg.add_input_text(
                tag='grid-coords-format-input', default_value='({x}, {y})', width=500))

        dpg.add_button(label='Edit colors & other styling rules',
            callback=lambda: dpg.configure_item('combiner-style-editor', show=True))

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

        dpg.add_button(label='Open dearpygui style editor', callback=dpg.show_style_editor)
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
        dpg.add_button(label='Print style settings group',
            callback=lambda: pprint(ElemGroup._groups['combiner-style-settings'])) # pylint: disable=protected-access
        dpg.add_button(label='Print gathered style options',
            callback=lambda: pprint(actions.get_style_options()))

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
