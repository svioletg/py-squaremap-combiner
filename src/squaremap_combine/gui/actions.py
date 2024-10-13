"""
Callables primarily for use in GUI callbacks.
"""

import re
import threading
from functools import wraps
from pathlib import Path
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from typing import Optional, cast

import dearpygui.dearpygui as dpg
from PIL import Image

from squaremap_combine.combine_core import DEFAULT_OUTFILE_FORMAT, Combiner, logger
from squaremap_combine.gui.layout import CONSOLE_TEXT_WRAP
from squaremap_combine.gui.models import CallbackArgs, UserData
from squaremap_combine.gui.themes import Themes

TILES_DIR_REGEX = r"^[\w-]+\\\w+\\[0-3]\\[-|]\d_[-|]\d"

EVENT = threading.Event()
"""General-purpose event re-used across multiple functions for waiting on certain responses."""

def dpg_callback(func):
    """Registers the wrapped function as a callback for `dearpygui` elements, consolidating its arguments
    into a `CallbackArgs` model and automatically handling some additional tasks after it's been called.

    The "Params" section for any `dpg_callback`-wrapped function will refer to the `UserData` fields
    it can make use of, not its actual arguments.
    """
    @wraps(func)
    def wrapper(sender: str | int, app_data, user_data: Optional[UserData]=None) -> None:
        user_data = user_data or UserData()
        result = func(CallbackArgs(sender=sender, app_data=app_data, user_data=user_data))
        if display := user_data.display:
            dpg.set_value(display, str(result))
        if forward := user_data.forward:
            forward(result)
        return result
    return wrapper

@dpg_callback
def dir_dialog(_args: CallbackArgs) -> Path:
    """Opens a dialog for choosing a directory."""
    return Path(askdirectory())

@dpg_callback
def file_open_dialog(_args: CallbackArgs) -> Path:
    """Opens a dialog for choosing a file."""
    return Path(askopenfilename())

@dpg_callback
def file_save_dialog(_args: CallbackArgs) -> Path:
    """Opens a dialog for saving a file."""
    return Path(asksaveasfilename())

@dpg_callback
def update_detail_choices_callback(args: CallbackArgs):
    """Callback form of `update_detail_choices` that passes `app_data` for its `world` parameter."""
    update_detail_choices(args.app_data)

def update_detail_choices(world: str):
    """Updates what radio buttons are available for map detail based on
    the contents of the selected world folder.
    """
    tiles_dir: str = dpg.get_value('tiles-dir-label')
    levels: list[str] = [p.stem for p in Path(tiles_dir, world).rglob('*/')]
    dpg.configure_item('detail-invalid', show=not bool(levels))
    dpg.configure_item('detail-choices', items=levels, show=bool(levels), default_value=levels[0])

@dpg_callback
def open_confirm_dialog_callback(args: CallbackArgs):
    """Callback form of `open_confirm_dialog` that passes `user_data.other` for its `message` parameter."""
    th = threading.Thread(target=open_confirm_dialog, args=(args.user_data.other,))
    th.start()

def open_confirm_dialog(message: str) -> bool:
    """Spawns a modal confirmation dialog, and returns the `bool` value associated with the clicked button.

    :param message: Dialog body text to display.

    .. warning::
        Must be run as a `threading.Thread` target, or else the call will never complete.
    """
    dpg.configure_item('modal-confirm', show=True, pos=(200, 200))
    dpg.configure_item('modal-confirm-message', default_value=message)
    EVENT.clear()
    EVENT.wait()
    result = dpg.get_value('modal-confirm-value')
    if result not in ['yes-button', 'no-button']:
        raise ValueError(f'open_confirm_dialog received an unexpected value: {result}')
    return result == 'yes-button'

@dpg_callback
def close_confirm_dialog(args: CallbackArgs):
    """Closes any currently open modal confirmation dialog and stores the sender of this callback."""
    EVENT.clear()
    EVENT.set()
    dpg.configure_item('modal-confirm', show=False)
    dpg.configure_item('modal-confirm-value', default_value=str(args.sender))

@dpg_callback
def create_image_callback(_args: CallbackArgs):
    """Callback form of `create_image`."""
    th = threading.Thread(target=create_image)
    th.start()

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

def create_image() -> Image.Image | None:
    """Prepares a `Combiner` instance with the selected options and creates the map image.
    
    .. warning::
        Must be run as a `threading.Thread` target, or else the call will never complete.
    """
    tiles_dir: str = dpg.get_value('tiles-dir-label')
    world: str = dpg.get_value('world-choices')
    level: str = dpg.get_value('detail-choices')
    output_dir: str = dpg.get_value('out-dir-label')

    combiner = Combiner(tiles_dir, use_tqdm=True, confirmation_callback=open_confirm_dialog)
    result = combiner.combine(world, int(level))

    out_file = Path(output_dir, DEFAULT_OUTFILE_FORMAT.format(
        timestamp='',
        world=world,
        detail=level,
        output_ext='png'
    ))

    if not result:
        logger.info('No image was created; process either failed or was cancelled.')
        return None

    result.img.save(out_file)
    logger.info(f'Image saved to: {out_file}')
    return result.img

def update_console(message: str):
    """Updates the "console" window in the GUI a new log message."""
    if not (level := re.findall(r"^(\w+): .*", message)):
        raise ValueError(f'update_console received a log message with an unexpected format: {message}')
    match level[0]:
        case 'GUI_COMMAND':
            # TODO: Create a class to handle GUI commands instead of branching like this
            command: list[str] = re.findall(r"^\w+: (.*)", message)[0].split()
            if command[0] == '/pbar':
                if command[1] == 'hide':
                    dpg.configure_item('progress-bar', show=False)
                if command[1] == 'set':
                    dpg.configure_item('progress-bar', default_value=float(command[2]), show=True)
            return
        case 'DEBUG':
            return

    new_log = dpg.add_text(default_value=message, parent='console-output-window', wrap=CONSOLE_TEXT_WRAP)
    match level[0]:
        case 'WARNING':
            dpg.bind_item_theme(new_log, Themes().console_warning)
        case 'ERROR':
            dpg.bind_item_theme(new_log, Themes().console_error)
    dpg.set_y_scroll('console-output-window', value=-1)

def validate_tiles_dir(source_dir: Path):
    """Check that the given directory contains a valid path to tiles, and update the choices."""
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
