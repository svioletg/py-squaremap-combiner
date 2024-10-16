"""
Callables primarily for use in GUI callbacks.
"""

import json
import re
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from typing import Any, Optional, cast

import dearpygui.dearpygui as dpg
from PIL import Image

from squaremap_combine.combine_core import DEFAULT_OUTFILE_FORMAT, Combiner, CombinerStyle, logger
from squaremap_combine.gui.layout import CONSOLE_TEXT_WRAP, ElemGroup
from squaremap_combine.gui.models import CallbackArgs, UserData
from squaremap_combine.gui.styling import Themes
from squaremap_combine.project import APP_SETTINGS_PATH

TILES_DIR_REGEX = re.compile(r"^[\w-]+\\\w+\\[0-3]\\[-|]\d_[-|]\d")

EVENT = threading.Event()
"""General-purpose event re-used across multiple functions for waiting on certain responses."""

#region WRAPPERS
def dpg_callback(func):
    """Registers the wrapped function as a callback for `dearpygui` elements, consolidating its arguments
    into a `CallbackArgs` model and automatically handling some additional tasks after it's been called.

    The "Params" section for any `dpg_callback`-wrapped function will refer to the `UserData` fields
    it can make use of, not its actual arguments.
    """
    @wraps(func)
    def wrapper(sender: str | int, app_data, user_data: Optional[UserData | dict[str, Any]]=None) -> None:
        if isinstance(user_data, dict):
            user_data = UserData(other=user_data)
        user_data = user_data or UserData()
        result = func(CallbackArgs(sender=sender, app_data=app_data, user_data=user_data))
        if display_with := user_data.cb_display_with:
            # Setting something like a text field to 'None' would then count as a non-None input if it were to be checked later
            dpg.set_value(display_with, str(result if result is not None else ''))
        if store_in := user_data.cb_store_in:
            dpg.set_item_user_data(store_in, result)
        if forward_to := user_data.cb_forward_to:
            if isinstance(forward_to, tuple):
                (forward_to[0] if result is not None else forward_to[1])(result)
        return result
    return wrapper

def notice_on_exception(func, exceptions: Optional[tuple[type[Exception], ...]]=None):
    """Spawns a modal dialog if an exception is raised in the wrapped function. It also logs the error.
    
    :param exceptions: A tuple of exceptions this wrapper will intercept and display.
    """
    exceptions = exceptions or (Exception,)
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            logger.error(''.join(traceback.format_exception(e)))
            open_notice_dialog('An error has occurred:\n' +
                ''.join(traceback.format_exception_only(e)).replace('\n', ' ') +
                '\nYour most recent log file will have more detailed information.'
            )
            return None
    return wrapper
#endregion WRAPPERS

#region GUI CALLBACKS
# Image creation functions go up top as they're the most crucial
@dpg_callback
def create_image_callback(_args: CallbackArgs):
    """Callback form of `create_image`."""
    th = threading.Thread(target=create_image)
    th.start()

@notice_on_exception
def create_image() -> Image.Image | None:
    """Prepares a `Combiner` instance with the selected options and creates the map image.

    .. warning::
        Must be run in a `threading.Thread`, or else the call will never complete.
    """
    if not all(dpg.get_value(e) for e in ElemGroup.get('img-required')):
        open_notice_dialog('One or more required options have not been set. Check that you\'ve set:\n' +
            '- A valid tiles directory\n' +
            '- World to render\n' +
            '- Detail level\n' +
            '- Output directory')
        return None

    opts = get_image_options()

    if not Path(opts['out-dir-input']).is_dir():
        open_notice_dialog('Could not find a directory at the specified path:\n' +
            str(Path(opts['out-dir-input']).absolute()))
        return None

    dpg.set_item_user_data('console-output-window', {'allow-output': True})

    style = CombinerStyle(**get_style_options())
    combiner = Combiner(
        opts['tiles-dir-input'],
        use_tqdm=True,
        confirmation_callback=open_confirm_dialog,
        style=style,
        grid_interval=tuple(opts['grid-interval-input'][0:2]) if opts['grid-overlay-checkbox'] else (0, 0),
        grid_coords_format=opts['grid-coords-format-input'].strip()
    )
    result = combiner.combine(
        opts['world-choices'],
        int(opts['detail-choices']),
        autotrim=opts['autotrim-checkbox'],
        area=tuple(opts['area-coord-input']) if opts['area-checkbox'] else None,
        force_size=tuple(opts['force-size-input'][0:2]) if opts['force-size-checkbox'] else None
    )

    if not result:
        logger.info('No image was created; process either failed or was cancelled.')
        return None

    out_file = Path(opts['out-dir-input'], DEFAULT_OUTFILE_FORMAT.format(
        timestamp=(datetime.now().strftime(opts['timestamp-format-input']) + '_') if opts['timestamp-checkbox'] else '',
        world=opts['world-choices'],
        detail=opts['detail-choices'],
        output_ext=opts['output-ext-input']
    ))

    if out_file.is_file():
        copies = [*out_file.parent.glob(f'{out_file.stem}*')]
        new_out_file = Path(out_file.stem + f'_{len(copies)}.' + 'png')
        if not open_confirm_dialog(f'A file at the path "{out_file}" already exists.\n' +
            f'Do you want to overwrite it? If you choose no, the file will be saved to "{new_out_file.stem}" instead.'):
            out_file = new_out_file

    result.img.save(out_file)
    logger.info(f'Image saved to: {out_file.absolute()}')

    logger.info('Image creation complete!')
    open_notice_dialog('Image creation complete!\n' +
        f'Saved to: {out_file.absolute()}')
    dpg.set_item_user_data('console-output-window', {'allow-output': False})
    return result.img

@dpg_callback
def dir_dialog_callback(_args: CallbackArgs) -> Path | None:
    """Opens a dialog for choosing a directory."""
    result = Path(askdirectory())
    return result if result != Path('.') else None

@dpg_callback
def file_open_dialog_callback(_args: CallbackArgs) -> Path | None:
    """Opens a dialog for choosing a file."""
    result = Path(askopenfilename())
    return result if result != Path('.') else None

@dpg_callback
def file_save_dialog_callback(args: CallbackArgs) -> Path | None:
    """Opens a dialog for saving a file."""
    initialfile: str | None = args.user_data.other.get('initialfile')
    result = Path(asksaveasfilename(initialfile=initialfile))
    return result if result != Path('.') else None

@dpg_callback
def update_detail_choices_callback(args: CallbackArgs):
    """Callback form of `update_detail_choices` that passes `app_data` for its `world` parameter."""
    update_detail_choices(args.app_data)

def update_detail_choices(world: str):
    """Updates what radio buttons are available for map detail based on
    the contents of the selected world folder.
    """
    tiles_dir: str = dpg.get_value('tiles-dir-input') or ''
    levels: list[str] = [p.stem for p in Path(tiles_dir, world).rglob('*/')]
    dpg.configure_item('detail-invalid', show=not bool(levels))
    dpg.configure_item('detail-choices', items=levels, show=bool(levels), default_value=levels[0])

@dpg_callback
def open_notice_dialog_callback(args: CallbackArgs):
    """Callback form of `open_notice_dialog`. `user_data.other` is used as the message."""
    open_notice_dialog(args.user_data.other)

def open_notice_dialog(message: str):
    """Spawns a modal notice box with an OK button and the given `message` as its text body."""
    dpg.configure_item('modal-notice', show=True)
    dpg.configure_item('modal-notice-message', default_value=message)

@dpg_callback
def close_notice_dialog_callback(_args: CallbackArgs):
    """Closes any present modal notice box."""
    dpg.configure_item('modal-notice', show=False)

@dpg_callback
def open_confirm_dialog_callback(args: CallbackArgs):
    """Callback form of `open_confirm_dialog` that passes `user_data.other` for its `message` parameter."""
    th = threading.Thread(target=open_confirm_dialog, args=(args.user_data.other,))
    th.start()

def open_confirm_dialog(message: str) -> bool:
    """Spawns a modal confirmation dialog, and returns the `bool` value associated with the clicked button.

    :param message: Dialog body text to display.

    .. warning::
        Must be run in a `threading.Thread`, or else the call will never complete.
    """
    dpg.configure_item('modal-confirm', show=True, pos=(200, 200))
    dpg.configure_item('modal-confirm-message', default_value=message)
    EVENT.clear()
    EVENT.wait()
    result = dpg.get_item_user_data('modal-confirm')
    if result not in ['yes-button', 'no-button']:
        raise ValueError(f'open_confirm_dialog received an unexpected value: {result}')
    return result == 'yes-button'

@dpg_callback
def close_confirm_dialog_callback(args: CallbackArgs):
    """Closes any currently open modal confirmation dialog and stores the sender of this callback."""
    EVENT.clear()
    EVENT.set()
    dpg.configure_item('modal-confirm', show=False)
    dpg.set_item_user_data('modal-confirm', args.sender)
    dpg.set_value('debug-conf-response-text', args.sender)

@dpg_callback
def center_in_window_callback(args: CallbackArgs):
    """Callback form of `center_in_window`. `user_data` is unpacked and passed to the function."""
    center_in_window(*args.user_data.other)

def center_in_window(target: str | int, parent: str | int):
    """Centers an item inside of the given parent item. If either item's size is `None`, or <= 0,
    this function will return and nothing will be affected.

    :param target: Item to center the position of.
    :param parent: Item to use as reference for centering `target`.
    """
    target_size = dpg.get_item_width(target), dpg.get_item_height(target)
    parent_size = dpg.get_item_width(parent), dpg.get_item_height(parent)
    if not all(n and (n > 0) for n in target_size + parent_size):
        return
    target_size = cast(tuple[int, int], target_size)
    parent_size = cast(tuple[int, int], parent_size)
    dpg.configure_item(target,
        pos=((parent_size[0] // 2) - (target_size[0] // 2), (parent_size[1] // 2) - (target_size[1] // 2)))

@dpg_callback
def timestamp_format_updated_callback(_args: CallbackArgs):
    """Runs when the timestamp format input field is updated, and updates the preview text accordingly."""
    try:
        timestamp = datetime(2023, 6, 16, 9, 48, 2).strftime(dpg.get_value('timestamp-format-input'))
    except ValueError:
        timestamp = dpg.get_value('timestamp-format-input')
    dpg.set_value('timestamp-format-preview', timestamp)

def update_console(message: str):
    """Processes the received log message. An associated action will be performed if the log
    is of level "GUI_COMMAND", "DEBUG" logs are ignored, and anything else is printed to the
    on-screen "console" window.
    """
    if not (level := re.findall(r"^(\w+): .*", message)):
        raise ValueError(f'update_console received a log message with an unexpected format: {message}')
    match level[0]:
        case 'GUI_COMMAND':
            command: list[str] = re.findall(r"^\w+: (.*)", message)[0].split()
            if command[0] == '/pbar':
                if command[1] == 'hide':
                    dpg.configure_item('progress-bar', show=False)
                if command[1] == 'set':
                    dpg.configure_item('progress-bar', default_value=float(command[2]), show=True)
            return
        case 'DEBUG':
            return

    if (user_data := dpg.get_item_user_data('console-output-window')) and not user_data['allow-output']:
        return

    new_log = dpg.add_text(default_value=message, parent='console-output-window', wrap=CONSOLE_TEXT_WRAP)
    match level[0]:
        case 'WARNING':
            dpg.bind_item_theme(new_log, Themes().console_warning)
        case 'ERROR':
            dpg.bind_item_theme(new_log, Themes().console_error)
    dpg.set_y_scroll('console-output-window', value=-1)

@dpg_callback
def validate_tiles_dir_callback(args: CallbackArgs):
    """Callback form of `validate_tiles_dir`. Passes `app_data` as `source_dir`."""
    validate_tiles_dir(args.app_data)

def validate_tiles_dir(source_dir: Path):
    """Check that the given directory contains a valid path to tiles, and update the choices."""
    if source_dir is None:
        return

    dpg.configure_item('world-no-valid-dir', default_value='Searching...')
    source_dir = Path(source_dir)
    world_paths: set[Path] = set()

    logger.info(f'Checking if "{source_dir}" is a valid tiles path...')
    levels = len(source_dir.parent.parts)
    for path, dirs, files in Path(source_dir).walk():
        if (len(path.parts) - levels) >= 4:
            dirs.clear()
            continue
        if files and re.match(TILES_DIR_REGEX, str(path.relative_to(source_dir.parent) / files[0])):
            world_paths.add(path.parent)

    if world_paths:
        logger.info(f'Valid path; found {len(world_paths)} world(s).')
        choices: list[str] = [p.stem for p in world_paths]
        dpg.configure_item('world-choices', items=choices, show=True, default_value=choices[0])
        dpg.configure_item('world-no-valid-dir', show=False)
        update_detail_choices(choices[0])
    else:
        logger.info('Path does not appear to be valid.')
        dpg.configure_item('world-no-valid-dir', default_value='No valid worlds found in this directory.', show=True)
        dpg.configure_item('detail-invalid', show=True)
        dpg.configure_item('detail-choices', show=False)
#endregion GUI CALLBACKS

#region MISC FUNCS
def get_image_options() -> dict[str, Any]:
    """Gets the value of every option input relating to creating an image, and returns them in a dictionary."""
    opt_dict = {e:dpg.get_value(e) for e in ElemGroup.get('image-settings') if not isinstance(e, int)}
    return opt_dict

def set_image_options(opt_dict: dict[str, Any]):
    """Sets the value of every option input relating to creating an image from a dictionary consisting of item tag
    keys, and values appropriate for that input type."""
    for item, value in opt_dict.items():
        try:
            dpg.set_value(item, value)
        except SystemError as e:
            logger.warning(f'SystemError encountered trying to set value for item "{item}": {e}')

def save_image_options(filename: Path):
    """Saves the currently set image settings to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(get_image_options(), f, indent=4)

def load_image_options(filename: Path):
    """Loads the image settings stored in a given JSON file into the relevant `dearpygui` items."""
    with open(filename, 'r', encoding='utf-8') as f:
        set_image_options(json.load(f))

def get_app_options() -> dict[str, Any]:
    """Gets the value of every option input relating to the GUI app, and returns them in a dictionary."""
    opt_dict = {e:dpg.get_value(e) for e in ElemGroup.get('app-settings') if not isinstance(e, int)}
    return opt_dict

def set_app_options(opt_dict: dict[str, Any]):
    """Sets the value of every option input relating to the GUI app from a dictionary consisting of item tag
    keys, and values appropriate for that input type."""
    for item, value in opt_dict.items():
        dpg.set_value(item, value)

def save_app_options():
    """Saves the currently set app preferences to a JSON file in the user's data directory, as determined by `platformdirs`."""
    with open(APP_SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(get_app_options(), f, indent=4)

def get_style_options() -> dict[str, Any]:
    """Gets the value of every option input relating to combiner styling, and returns them in a dictionary."""
    opt_dict = {e.split('-styleattr')[0]:dpg.get_value(e) for e in ElemGroup.get('combiner-style-settings') if not isinstance(e, int)}
    return opt_dict

def set_style_options(opt_dict: dict[str, Any]):
    """Sets the value of every option input relating to combiner styling from a dictionary consisting of item tag
    keys, and values appropriate for that input type."""
    for item, value in opt_dict.items():
        dpg.set_value(item + '-styleattr-input', value)

def save_style_options(filename: Path):
    """Saves the currently set combiner styling rules to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(get_style_options(), f, indent=4)

def load_style_options(filename: Path):
    """Loads the styling rules stored in a given JSON file into the relevant `dearpygui` items."""
    with open(filename, 'r', encoding='utf-8') as f:
        set_style_options(json.load(f))

def open_window_at_path(target: Path):
    """Opens the file explorer window for the current OS at the given path."""
    if sys.platform == 'darwin':
        subprocess.Popen(['open', '--', target])
    elif sys.platform == 'linux':
        subprocess.Popen(['xdg-open', '--', target])
    elif sys.platform == 'win32':
        subprocess.Popen(['explorer', target])
#endregion MISC FUNCS
