import operator
import os
import tkinter.filedialog
from functools import reduce
from pathlib import Path
from tkinter import Tk
from typing import Callable

import dearpygui.dearpygui as dpg

import sqmap

INVALID_WORLD_TEXT = 'No worlds found in selected tiles directory!'
MAX_STATUS_LINES = 7
FONT_FILE = 'font/bedstead.otf'
FONT_SIZE = 18

combine_options = {'tiles_dir': 'invalid', 'world': 'invalid', 'zoom_level': '0', 'final_resize_multiplier': 1.0, 'output_dir': Path('.')}
status_messages = []

# Defaults so we don't get typing errors
confirmation_callbacks: dict[str, Callable] = {'yes': print, 'no': print}

def update_status_text(text: str):
    if text.startswith('Stitching:'):
        status_messages[-1] = text
    else:
        status_messages.append(text)
    if len(status_messages) > MAX_STATUS_LINES:
        status_messages.pop(0)
    dpg.set_value('status', '\n'.join(status_messages))

def show_confirmation_buttons():
    dpg.show_item('continue_button')
    dpg.show_item('cancel_button')

def continue_button_callback():
    dpg.hide_item('continue_button')
    dpg.hide_item('cancel_button')
    confirmation_callbacks['yes']()

def cancel_button_callback():
    dpg.hide_item('continue_button')
    dpg.hide_item('cancel_button')
    confirmation_callbacks['no']()

def combine_callback():
    status_messages.clear()
    if combine_options['tiles_dir'] == 'invalid':
        update_status_text('Selected tiles directory is invalid; no world folders found.')
        return
    try:
        filesize_estimate_kb: float = round(sqmap.image_filesize_estimate(Path(combine_options['tiles_dir'], combine_options['world'], combine_options['zoom_level'])), 2)
        filesize_estimate_string: str = f'{filesize_estimate_kb} KB' if filesize_estimate_kb < 1000 else f'{filesize_estimate_kb / 1000:.2f} MB'
        tiles = os.listdir(Path(combine_options['tiles_dir'], combine_options['world'], combine_options['zoom_level']))
        columns, rows = sqmap.calculate_columns_rows(tiles)[:2]
        image_size_estimate: tuple[int, int] = (len(columns) * sqmap.TILE_SIZE, len(rows) * sqmap.TILE_SIZE)
        update_status_text(f'Estimated filesize: {filesize_estimate_string} ({image_size_estimate[0]}px x {image_size_estimate[1]}px)')
        update_status_text('Do you want to continue?')
        show_confirmation_buttons()
        def yes():
            sqmap.combine(
                combine_options['tiles_dir'], 
                combine_options['world'], 
                combine_options['zoom_level'], 
                combine_options['final_resize_multiplier'],
                combine_options['output_dir'],
                update_status_text
                )
        def no():
            update_status_text('Cancelled.')
            return
        confirmation_callbacks['yes'] = yes; confirmation_callbacks['no'] = no
    except Exception as e:
        update_status_text(f'Failed! {e}')
        raise e

def set_tiles_dir():
    Tk().withdraw()
    selection = Path(tkinter.filedialog.askdirectory())

    if not sqmap.is_valid_tiles_dir(selection):
        combine_options['world'] = 'invalid'
        dpg.configure_item('world_choice', items=[INVALID_WORLD_TEXT])
        return
    
    # Check if the selected path is itself a world or a zoom level, automatically choose it if so
    if sqmap.is_valid_world_name(selection.parts[-1]) or sqmap.is_valid_world_name(selection.parts[-2]):
        if selection.parts[-1] in ['0', '1', '2', '3']:
            combine_options['zoom_level'] = selection.parts[-1]
            set_zoom_level(0, combine_options['zoom_level'])
            world_name_index = -2
        else:
            world_name_index = -1
        combine_options['tiles_dir'] = Path(*selection.parts[:world_name_index])
        combine_options['world'] = selection.parts[world_name_index]
        set_world_choice(0, combine_options['world'])
    # If not, it must be the tiles directory itself
    else:
        combine_options['tiles_dir'] = selection
    
    available_worlds = [item for item in os.listdir(combine_options['tiles_dir']) if sqmap.is_valid_world_name(item)]
    dpg.configure_item('world_choice', items=available_worlds)
    
    dpg.set_value('tiles_dir_text', f'{combine_options['tiles_dir']}')

def set_world_choice(sender, data):
    if not sqmap.is_valid_world_name(data):
        combine_options['world'] = 'invalid'
    combine_options['world'] = data

    dpg.set_value('world_choice', data)

def set_zoom_level(sender, data):
    try:
        if int(data) not in range(0, 4):
            raise ValueError
    except ValueError:
        status_messages.clear()
        update_status_text(f'Invalid zoom level received: {data}')
        return
    combine_options['zoom_level'] = str(data)

    dpg.set_value('zoom_level_slider', int(data))

def set_output_dir():
    Tk().withdraw()
    selection = Path(tkinter.filedialog.askdirectory())
    combine_options['output_dir'] = selection

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
        dpg.add_text(f'{combine_options['tiles_dir'] if combine_options['tiles_dir'] != 'invalid' else 'No valid directory chosen.'}', 
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
        dpg.add_button(label='Continue', tag='continue_button', show=False, callback=continue_button_callback)
        dpg.add_button(label='Cancel', tag='cancel_button', show=False, callback=cancel_button_callback)
    
    dpg.bind_font(default_font)

#endregion

# Create window, start program
dpg.create_viewport(title='Squaremap Tile Combiner', width=1024, height=800)
dpg.setup_dearpygui()

dpg.show_viewport()
dpg.set_primary_window('Primary Window', True)
dpg.start_dearpygui()
dpg.destroy_context()
