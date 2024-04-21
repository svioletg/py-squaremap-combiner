import itertools
import math
import os
from argparse import ArgumentParser
from pathlib import Path
from typing import Callable

from PIL import Image

TILE_SIZE: int = 512

valid_worlds: list[str] = ['minecraft_overworld', 'minecraft_the_nether', 'minecraft_the_end']

def is_valid_tiles_dir(tiles_path: Path) -> bool:
    contents: list[str] = os.listdir(tiles_path)
    return any(item in valid_worlds for item in tiles_path.parts)\
        or any(item in valid_worlds for item in contents)

def is_valid_world_name(world: str) -> bool:
    return world in valid_worlds

def trim_transparency(original_image: Image.Image) -> Image.Image:
    binary = Image.new('1', original_image.size)
    binary.paste(1, mask=original_image.split()[3])
    bbox = binary.getbbox()
    trimmed_image = original_image.crop(bbox)
    return trimmed_image

def image_filesize_estimate(tiles_or_path: Path|int) -> float:
    """
    Estimate the size of the final combined image in kilobytes
    """
    if isinstance(tiles_or_path, Path):
        tiles = len(os.listdir(tiles_or_path))
    else:
        tiles = tiles_or_path
    
    single_tile_area: int = TILE_SIZE * TILE_SIZE
    total_area: int = tiles * single_tile_area
    # 20% of the raw estimate - 80% compressed - seems to be a generally safe estimate
    return (((total_area * 32) // 8) // 5) / 1000

def calculate_columns_rows(tiles: list[str]) -> tuple[list[int], list[int], int, int, int, int]:
    regions = [Path(tile).stem.split('_') for tile in tiles]

    min_column = min([int(r[0]) for r in regions])
    max_column = max([int(r[0]) for r in regions])
    min_row    = min([int(r[1]) for r in regions])
    max_row    = max([int(r[1]) for r in regions])

    columns = list(range(min_column, max_column+1))
    rows    = list(range(min_row, max_row+1))

    return columns, rows, min_column, min_row, max_column, max_row

def combine(tiles_path: Path, world: str='minecraft_overworld', zoom_level: str='0', final_size_multiplier: float=1.0, output_dir: Path | str=Path('.'), status_callback: Callable = print):
    # Find images and get the size and extension
    images_dir = Path(tiles_path, world, zoom_level)
    status_callback('Searching for tile images...')
    tiles = os.listdir(images_dir)
    img_ext = Path(tiles[0]).suffix
    with Image.open(Path(images_dir, tiles[0])) as img:
        img_size = img.size[0]

    # Figure out the number of columns and rows present
    status_callback('Calculating columns and rows...')
    columns, rows, min_column, min_row, max_column, max_row = calculate_columns_rows(tiles)

    # Start creating the new image
    status_callback('Making the combined image...')
    final_width = len(columns) * img_size
    final_height = len(rows) * img_size
    map_image = Image.new('RGBA', (final_width, final_height), (0,0,0,0))

    x_offset = abs(min_column) if min_column < 0 else 0
    y_offset = abs(min_row) if min_row < 0 else 0
    row_column_iterations = list(itertools.product(rows, columns))
    total_iterations = len(list(row_column_iterations))
    progress = 0

    for r, c in row_column_iterations:
        progress += 1
        try:
            status_callback(f'Stitching: {progress}/{total_iterations} ({int((progress / total_iterations) * 100)}%)')
            img = Image.open(Path(images_dir, f'{c}_{r}{img_ext}'))
        except FileNotFoundError:
            continue
        map_image.paste(img, (img_size * (c + x_offset), img_size * (r + y_offset)))

    grid_w, grid_h = map_image.size

    status_callback(f'Full image created. Resizing by {final_size_multiplier}: from {grid_w, grid_h} to {int(grid_w * final_size_multiplier), int(grid_h * final_size_multiplier)}...')
    map_image = map_image.resize((int(grid_w * final_size_multiplier), int(grid_h * final_size_multiplier)))

    status_callback('Trimming any empty space...')
    map_image = trim_transparency(map_image)

    status_callback('Saving... (this may take a while for a large image, e.g over 5,000 x 5,000)')
    output_file = f'{world}-level{zoom_level}.png'
    map_image.save(Path(output_dir, output_file))

    status_callback(f'Final image saved to "{Path(output_dir, output_file)}" ({map_image.size[0]} x {map_image.size[1]})')
    status_callback('Done.')

def main():
    parser = ArgumentParser()
    parser.add_argument('-i', '--interactive', action='store_true')
    parser.add_argument('-t', '--tilespath', 
        help='Path to your "tiles" directory. Must be an absolute path if it is not within the folder this script is running from.')
    parser.add_argument('-w', '--world', 
        help="Name of the world to create an image from - defaults available are minecraft_overworld, minecraft_the_nether, and minecraft_the_end.")
    parser.add_argument('-z', '--zoom', 
        help="Zoom level to use images from. 0 is the lowest detail and smallest size, 3 is the highest detail and largest size.")
    parser.add_argument('-r', '--resize',
        help="Multiplier to resize the final image by. 0.5 is half as large, 1 is original size, 2 is twice as large, etc.")
    args = parser.parse_args()

    for arg in vars(args):
        if args.interactive:
            break
        if vars(args)[arg] is None:
            print(f'Missing argument "--{arg}"; use "-i" or "--interactive" to have the script walk you through each step; use "--help" to see all arguments.')
            raise SystemExit(0)

    if not args.interactive:
        TILES_DIR = Path(args.tilespath)
        WORLD = str(args.world)
        ZOOM = int(args.zoom)
        RESIZE_BY = float(args.resize)
        pass
    else:
        # Take user input
        TILES_DIR = Path(input('Enter the path to your "tiles" folder: ').strip())
        if not TILES_DIR.exists():
            print(f'The path "{TILES_DIR}" does not exist; exiting...')
            raise SystemExit(0)

        WORLDS = [d for d in os.listdir(TILES_DIR) if Path(TILES_DIR, d).is_dir()]
        WORLD = WORLDS[int(input('\n'+'\n'.join(f'{n}: {world}' for n, world in enumerate(WORLDS))+'\n\nSelect a map to use (number): '))]

        ZOOM_LEVELS = [d for d in os.listdir(Path(TILES_DIR, WORLD)) if Path(TILES_DIR, WORLD, d).is_dir()]

        for level in ZOOM_LEVELS:
            files  = os.listdir(Path(TILES_DIR, WORLD, level))
            amount = len(files)
            with Image.open(Path(TILES_DIR, WORLD, level, files[0])) as img:
                size = img.size[0]
            flavortext = {0: "(lowest detail)", 3: "(highest detail)"}.get(int(level), "")
            print(f'{level} {flavortext} | {amount} images were found, estimated combined size is {int(math.sqrt(amount*(size*size)))}px')
            del files, amount, size

        ZOOM = input('\nSelect a zoom level to use (number): ')

        RESIZE_BY = float(input('Enter a multiplier to resize the final image by;\n1 for no resizing; 0.5 is half as large, 2 is twice as large, etc.: ').strip())

        if input('Continue with the chosen settings? (y/n) ').strip().lower() != 'y':
            print('Cancelling...')
            raise SystemExit(0)

    combine(TILES_DIR, WORLD, str(ZOOM), RESIZE_BY)

if __name__ == '__main__':
    main()
