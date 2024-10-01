import itertools
import math
import os
from argparse import ArgumentParser
from pathlib import Path

import numpy
from PIL import Image

TILE_SIZE: int = 512

valid_worlds: list[str] = ['minecraft_overworld', 'minecraft_the_nether', 'minecraft_the_end']

def is_valid_tiles_dir(tiles_path: Path) -> bool:
    contents: list[str] = os.listdir(tiles_path)
    return any(item in valid_worlds for item in tiles_path.parts)\
        or any(item in valid_worlds for item in contents)

def is_valid_world_name(world: str) -> bool:
    return world in valid_worlds

def find_region_outliers(regions: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    regions_array = numpy.array(regions, dtype=int)

    mean = numpy.mean(regions_array, axis=0)
    deviation = numpy.std(regions_array, axis=0)
    zscores = numpy.abs((regions_array - mean) / deviation)
    outliers: list[list[int]] = regions_array[(zscores > 2).any(axis=1)].tolist()
    outlier_tuples: list[tuple[str, ...]] = [tuple(map(str, item)) for item in outliers]

    return outlier_tuples

def image_filesize_estimate(tiles_path: Path, world: str='minecraft_overworld', zoom_level: str='0') -> float:
    """Estimate the size of the final combined image, in kilobytes."""
    tiles: list[str] = os.listdir(Path(tiles_path, world, zoom_level))
    size: int = 0
    for tile in tiles:
        size += os.stat(Path(tiles_path, world, zoom_level, tile)).st_size

    return size / 1000

def calculate_columns_rows(regions: list[tuple[str, ...]]) -> tuple[list[tuple[str, ...]], list[int], list[int], int, int, int, int]:
    outliers = find_region_outliers(regions)
    filtered_regions = list(set(regions) - set(outliers))

    min_column = min(int(r[0]) for r in filtered_regions)
    max_column = max(int(r[0]) for r in filtered_regions)
    min_row    = min(int(r[1]) for r in filtered_regions)
    max_row    = max(int(r[1]) for r in filtered_regions)

    columns = list(range(min_column, max_column+1))
    rows    = list(range(min_row, max_row+1))

    return outliers, columns, rows, min_column, min_row, max_column, max_row

def trim_transparency(original_image: Image.Image) -> Image.Image:
    binary = Image.new('1', original_image.size)
    binary.paste(1, mask=original_image.split()[3])
    bbox = binary.getbbox()
    trimmed_image = original_image.crop(bbox)
    return trimmed_image

class Stitcher:
    def __init__(self,
            tiles_dir: Path,
            world: str='minecraft_overworld',
            zoom_level: str='0',
            final_size_multiplier: float=1.0,
            output_dir: Path | str=Path('.')
            ):
        self.tiles_path = tiles_dir
        self.world = world
        self.zoom_level = zoom_level
        self.final_size_multiplier = final_size_multiplier
        self.output_dir = output_dir

        # Find images and get the size and extension
        print('Searching for tile images...')
        self.tile_images_dir = Path(self.tiles_path, self.world, self.zoom_level)
        self.tiles = os.listdir(self.tile_images_dir)
        self.regions: list[tuple[str, ...]] = []
        progress: int = 0
        for tile in self.tiles:
            progress += 1
            if len(Path(tile).stem.split('_')) != 2:
                print(f'Invalid tile name: "{tile}"; skipping...')
                continue
            self.regions.append(tuple(Path(tile).stem.split('_')))
            print(f'<prog>Found: "{tile}" {progress}/{len(self.tiles)} ({int(progress / len(self.tiles) * 100)}%)')
        with Image.open(Path(self.tile_images_dir, self.tiles[0])) as tile_image:
            self.tile_image_size = tile_image.size[0]
        self.img_ext = Path(self.tiles[0]).suffix

    def prepare(self):
        # Figure out the number of columns and rows present
        print('Calculating columns and rows...')
        outliers, columns, rows, min_column, min_row, max_column, max_row = calculate_columns_rows(self.regions)

        if len(outliers) > 0:
            outliers_formatted = []
            for item in outliers:
                outliers_formatted.append(f'{item[0]}_{item[1]}{self.img_ext}')
            print('The following outlier regions were found, and will be omitted:')
            print(', '.join(outliers_formatted))

        response = input(f'Found {len(columns)} columns and {len(rows)} rows.\nContinue? (y/n) ')
        return_pack = (outliers, columns, rows, min_column, min_row, max_column, max_row, self.tile_image_size)

        if response.lower() == 'y':
            self.make_image(*return_pack)
            return
        else:
            print('Cancelled.')
            return

    def make_image(self, outliers, columns, rows, min_column, min_row, max_column, max_row, tile_image_size) -> None:
        # Start creating the new image
        print('Making the combined image...')
        final_width = len(columns) * tile_image_size
        final_height = len(rows) * tile_image_size
        map_image = Image.new('RGBA', (final_width, final_height), (0,0,0,0))

        x_offset = abs(min_column) if min_column < 0 else 0
        y_offset = abs(min_row) if min_row < 0 else 0
        row_column_iterations = list(itertools.product(rows, columns))
        total_iterations = len(list(row_column_iterations))
        progress = 0

        for r, c in row_column_iterations:
            progress += 1
            try:
                print(f'<prog>Stitching: {progress}/{total_iterations} ({int((progress / total_iterations) * 100)}%)')
                with Image.open(Path(self.tile_images_dir, f'{c}_{r}{self.img_ext}')) as tile_image:
                    map_image.paste(tile_image, (tile_image_size * (c + x_offset), tile_image_size * (r + y_offset)))
            except FileNotFoundError:
                continue

        # print(f'Full image created. Resizing by {self.final_size_multiplier}: from {grid_w, grid_h} to {int(grid_w * self.final_size_multiplier), int(grid_h * self.final_size_multiplier)}...')
        # map_image = map_image.resize((int(grid_w * self.final_size_multiplier), int(grid_h * self.final_size_multiplier)))

        print('Trimming any empty space...')
        map_image = trim_transparency(map_image)

        print('Saving... (this may take a while for a large image, e.g over 5,000px x 5,000px)')
        output_file = f'{self.world}-level{self.zoom_level}.png'
        map_image.save(Path(self.output_dir, output_file))

        print(f'Final image saved to "{Path(self.output_dir, output_file)}" ({map_image.size[0]}px x {map_image.size[1]}px)')
        print('Done.')

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

    # combine(TILES_DIR, WORLD, str(ZOOM), RESIZE_BY)

if __name__ == '__main__':
    main()
