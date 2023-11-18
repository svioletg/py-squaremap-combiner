import math
import os
from pathlib import Path

from PIL import Image
from tqdm.contrib import itertools
from argparse import ArgumentParser

def combine(tiles_path: Path, world: str, zoom_level: str, resize_mult: float):
    # Find images and get the size and extension
    images_dir = Path(tiles_path, world, zoom_level)
    print('Finding images...')
    files = os.listdir(images_dir)
    img_ext = Path(files[0]).suffix
    with Image.open(Path(images_dir, files[0])) as img:
        img_size = img.size[0]

    # Figure out the number of columns and rows present
    print('Calculating columns and rows...')
    regions = [Path(file).stem.split('_') for file in files]

    min_column = min([int(r[0]) for r in regions])
    max_column = max([int(r[0]) for r in regions])
    min_row    = min([int(r[1]) for r in regions])
    max_row    = max([int(r[1]) for r in regions])

    columns = list(range(min_column, max_column+1))
    rows    = list(range(min_row, max_row+1))

    # Start creating the new image
    print('Making the combined image...')
    final_width = len(columns)*img_size
    final_height = len(rows)*img_size
    canvas = Image.new('RGBA', (final_width, final_height), (0,0,0,0))

    x_offset = abs(min_column) if min_column < 0 else 0
    y_offset = abs(min_row) if min_row < 0 else 0

    for r, c in itertools.product(rows, columns):
        try:
            img = Image.open(Path(images_dir, f'{c}_{r}{img_ext}'))
        except FileNotFoundError:
            continue
        canvas.paste(img, (img_size*(c+x_offset), img_size*(r+y_offset)))

    grid_w, grid_h = canvas.size
    print(f'Done; resizing from {grid_w, grid_h} to {int(grid_w*resize_mult), int(grid_h*resize_mult)}...')
    canvas = canvas.resize((int(grid_w*resize_mult), int(grid_h*resize_mult)))
    print('Saving... (this may take a while for a large image, e.g over 5,000 x 5,000)')
    canvas.save(f'{world}-level{zoom_level}.png')
    print(f'Final image saved to "{world}-level{zoom_level}.png"')

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
            exit()

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
            exit()

        WORLDS = [d for d in os.listdir(TILES_DIR) if Path(TILES_DIR, d).is_dir()]
        WORLD = WORLDS[int(input('\n'+'\n'.join(f'{n}: {world}' for n, world in enumerate(WORLDS))+'\n\nSelect a map to use (number): '))]

        ZOOM_LEVELS = [d for d in os.listdir(Path(TILES_DIR, WORLD)) if Path(TILES_DIR, WORLD, d).is_dir()]

        for level in ZOOM_LEVELS:
            files  = os.listdir(Path(TILES_DIR, WORLD, level))
            amount = len(files)
            with Image.open(Path(TILES_DIR, WORLD, level, files[0])) as img:
                size = img.size[0]
            # TODO: see what these levels actually are
            flavortext = {0: "(lowest detail)", 3: "(highest detail)"}.get(int(level), "")
            print(f'{level} {flavortext} | {amount} images were found, estimated combined size is {int(math.sqrt(amount*(size*size)))}px')
            del files, amount, size

        ZOOM = input('\nSelect a zoom level to use (number): ')

        RESIZE_BY = float(input('Enter a multiplier to resize the final image by;\n1 for no resizing; 0.5 is half as large, 2 is twice as large, etc.: ').strip())

        if input('Continue with the chosen settings? (y/n) ').strip().lower() != 'y':
            print('Cancelling...')
            exit()

    combine(TILES_DIR, WORLD, str(ZOOM), RESIZE_BY)

if __name__ == '__main__':
    main()