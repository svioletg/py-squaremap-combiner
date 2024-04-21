import os
import threading
import tkinter.filedialog
from pathlib import Path
from tkinter import Tk
from typing import Callable, Literal

import dearpygui.dearpygui as dpg

import sqmap

INVALID_WORLD_TEXT = 'No worlds found in selected tiles directory!'
MAX_STATUS_LINES = 7
FONT_FILE = 'font/bedstead.otf'
FONT_SIZE = 18

stitcher_params = {'tiles_dir': 'invalid', 'world': 'invalid', 'zoom_level': '0', 'final_resize_multiplier': 1.0, 'output_dir': Path('.')}
status_messages = []

class Confirmation:
    # confirmation_callbacks: dict[str, Callable] = {'yes': print, 'no': print}
    confirmation_choice: Literal['y', 'n'] | None = None
    positive_callback: Callable = print
    negative_callback: Callable = print

    @classmethod
    def prompt_confirmation(cls, message: str):
        update_status_text(message)
        dpg.show_item('continue_button')
        dpg.show_item('cancel_button')
        cls.confirmation_choice = None

    @classmethod
    def set_pair(cls, positive: Callable, negative: Callable):
        cls.positive_callback = positive
        cls.negative_callback = negative

    @classmethod
    def proceed(cls):
        dpg.hide_item('continue_button')
        dpg.hide_item('cancel_button')
        cls.confirmation_choice = 'y'
        cls.positive_callback()

    @classmethod
    def cancel(cls):
        dpg.hide_item('continue_button')
        dpg.hide_item('cancel_button')
        cls.confirmation_choice = 'n'
        cls.negative_callback()

def update_status_text(text: str):
    if text.startswith('<prog>'):
        text = text.lstrip('<prog>')
        status_messages[-1] = text
    else:
        status_messages.append(text)
    if len(status_messages) > MAX_STATUS_LINES:
        status_messages.pop(0)
    dpg.set_value('status', '\n'.join(status_messages))

def combine_callback():
    sqmap.run_mode = 'gui'
    status_messages.clear()
    if stitcher_params['tiles_dir'] == 'invalid':
        update_status_text('Selected tiles directory is invalid; no world folders found.')
        return
    try:
        stitcher = sqmap.Stitcher(
            stitcher_params['tiles_dir'],
            stitcher_params['world'],
            stitcher_params['zoom_level'],
            stitcher_params['final_resize_multiplier'],
            stitcher_params['output_dir'],
            update_status_text,
            Confirmation.prompt_confirmation,
            'gui'
            )
        
        filesize_estimate_kb: float = round(sqmap.image_filesize_estimate(stitcher.tiles_path), 2)
        filesize_estimate_string: str = f'{filesize_estimate_kb} KB' if filesize_estimate_kb < 1000 else f'{filesize_estimate_kb / 1000:.2f} MB'

        outliers, columns, rows = sqmap.calculate_columns_rows(stitcher.regions)[:3]
        image_size_estimate: tuple[int, int] = (len(columns) * stitcher.tile_image_size, len(rows) * stitcher.tile_image_size)
        update_status_text(f'Estimated filesize: {filesize_estimate_string} ({image_size_estimate[0]}px x {image_size_estimate[1]}px)')
        Confirmation.prompt_confirmation('Do you want to continue?')
        def yes():
            results = stitcher.prepare()
            def yes():
                stitcher.make_image(*results)
            # Any cancelling from this point can just use the already assigned no() function earlier
            Confirmation.positive_callback = yes
        def no():
            update_status_text('Cancelled.')
            return
        Confirmation.set_pair(yes, no)
    except Exception as e:
        update_status_text(f'Failed! {e}')
        raise e

def set_tiles_dir():
    Tk().withdraw()
    selection = Path(tkinter.filedialog.askdirectory())

    if not sqmap.is_valid_tiles_dir(selection):
        stitcher_params['world'] = 'invalid'
        dpg.configure_item('world_choice', items=[INVALID_WORLD_TEXT])
        return
    
    # Check if the selected path is itself a world or a zoom level, automatically choose it if so
    if sqmap.is_valid_world_name(selection.parts[-1]) or sqmap.is_valid_world_name(selection.parts[-2]):
        if selection.parts[-1] in ['0', '1', '2', '3']:
            stitcher_params['zoom_level'] = selection.parts[-1]
            set_zoom_level(0, stitcher_params['zoom_level'])
            world_name_index = -2
        else:
            world_name_index = -1
        stitcher_params['tiles_dir'] = Path(*selection.parts[:world_name_index])
        stitcher_params['world'] = selection.parts[world_name_index]
        set_world_choice(0, stitcher_params['world'])
    # If not, it must be the tiles directory itself
    else:
        stitcher_params['tiles_dir'] = selection
    
    available_worlds = [item for item in os.listdir(stitcher_params['tiles_dir']) if sqmap.is_valid_world_name(item)]
    if stitcher_params['world'] == 'invalid' and available_worlds:
        stitcher_params['world'] = available_worlds[0]
    dpg.configure_item('world_choice', items=available_worlds)
    
    dpg.set_value('tiles_dir_text', f'{stitcher_params['tiles_dir']}')

def set_world_choice(sender, data):
    if not sqmap.is_valid_world_name(data):
        stitcher_params['world'] = 'invalid'
    stitcher_params['world'] = data

    dpg.set_value('world_choice', data)

def set_zoom_level(sender, data):
    try:
        if int(data) not in range(0, 4):
            raise ValueError
    except ValueError:
        status_messages.clear()
        update_status_text(f'Invalid zoom level received: {data}')
        return
    stitcher_params['zoom_level'] = str(data)

    dpg.set_value('zoom_level_slider', int(data))

def set_output_dir():
    Tk().withdraw()
    selection = Path(tkinter.filedialog.askdirectory())
    stitcher_params['output_dir'] = selection

    dpg.set_value('output_dir_text', f'{selection}')

#region BUILD WINDOW

dpg.create_context()

with dpg.font_registry():
    default_font = dpg.add_font(FONT_FILE, FONT_SIZE)

def section_separator():
    dpg.add_spacer(height=FONT_SIZE // 2); dpg.add_separator(); dpg.add_spacer(height=FONT_SIZE // 2)

with dpg.window(tag='Primary Window'):
    dpg.add_text('SQUAREMAP TILE COMBINER')
    dpg.add_text('Please choose your output options.')

    section_separator()

    # Tiles directory selection
    with dpg.group(horizontal=True):
        dpg.add_text('Path to tiles folder:')
        dpg.add_text(f'{stitcher_params['tiles_dir'] if stitcher_params['tiles_dir'] != 'invalid' else 'No valid directory chosen.'}', 
            tag='tiles_dir_text', wrap=640)
    
    dpg.add_button(label='Choose tiles folder...', callback=set_tiles_dir)
    
    # World selection
    dpg.add_text('Select a map to use:')
    dpg.add_radio_button([INVALID_WORLD_TEXT], tag='world_choice', callback=set_world_choice)

    section_separator()
    
    with dpg.group(horizontal=True):
        dpg.add_text('Zoom level:')
        dpg.add_slider_int(default_value=0, min_value=0, max_value=3, tag='zoom_level_slider', width=200, callback=set_zoom_level)
    
    dpg.add_text('0 is the lowest quality and will create a small image.\n3 is the highest quality and will create a very large image.')

    section_separator()

    with dpg.group(horizontal=True):
        dpg.add_text('Output destination:')
        dpg.add_text('', tag='output_dir_text', wrap=640)
    
    dpg.add_button(label='Choose output folder...', callback=set_output_dir)

    section_separator()

    # Start combining
    dpg.add_button(label='Start', callback=combine_callback)
    with dpg.group(horizontal=True):
        dpg.add_text('STATUS: ')
        with dpg.child_window(height=200):
            dpg.add_text('Waiting.', tag='status', wrap=640)
    
    with dpg.group(horizontal=True):
        dpg.add_text('        ')
        dpg.add_button(label='Continue', tag='continue_button', show=False, callback=Confirmation.proceed)
        dpg.add_button(label='Cancel', tag='cancel_button', show=False, callback=Confirmation.cancel)
    
    dpg.add_button(label='test prompt', callback=lambda: Confirmation.prompt_confirmation('Do you want to continue?'))
    
    dpg.bind_font(default_font)

#endregion

# Create window, start program
dpg.create_viewport(title='Squaremap Tile Combiner', width=1024, height=800)
dpg.setup_dearpygui()

dpg.show_viewport()
dpg.set_primary_window('Primary Window', True)
dpg.start_dearpygui()
dpg.destroy_context()
