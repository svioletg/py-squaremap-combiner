import argparse
import sys
import time
from datetime import datetime
from math import ceil
from pathlib import Path
from typing import Optional

from loguru import logger
from PIL import Image
from tqdm import tqdm

logger.remove() # Don't output anything if this is just being imported

Rectangle = tuple[int, int, int, int]

default_time_format = '%Y-%m-%d_%H-%M-%S'

def sign(num: int | float) -> int:
    """Return the sign of a value."""
    return 1 if num > 0 else -1 if num < 0 else 0

def snap_num(num: int | float, multiple: int) -> int:
    """Snaps the given `num` to the largest `multiple` it can reside in.
    e.g. `snap_num(7, 10)` -> `10`, `snap_num(2, 10)` -> `10`, `snap_num(-7, 10)` -> `-10`, `snap_num(-2, 10)` -> `-10`
    """
    # Make it absolute so that the largest number is snapped to regardless, re-apply original sign after
    return sign(num) * multiple * (ceil(abs(num) / multiple))

def snap_box(box: Rectangle, multiple: int) -> Rectangle:
    """Snaps the given four box coordinates to the largest `multiple` they can reside in. See `snap_num`."""
    return tuple(map(lambda n: snap_num(n, multiple), box)) # type: ignore

class CombineError(Exception):
    """Raised when anything in the image combination process fails when
    no other type of exception would be applicable.
    """

class Combiner:
    """Takes a squaremap `tiles` directory path, handles calculating rows/columns,
    and is able to export full map images.
    """
    TILE_SIZE: int = 512
    """The size of each tile image in pixels.
    Only made a constant in case squaremap happens to change its image sizes in the future.
    """
    STANDARD_WORLDS: list[str] = ['overworld', 'the_nether', 'the_end']
    def __init__(self, tiles_dir: str | Path, use_tqdm = False):
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir = tiles_dir
        self.mapped_worlds: list[str] = [p.stem for p in tiles_dir.glob('minecraft_*/')]
        self.use_tqdm = use_tqdm

    def combine(self, world: str | Path, detail: int, autotrim: bool=False, area: Optional[Rectangle]=None) -> Image.Image:
        """Combine the given world (dimension) tile images into one large map.
        @param world: Name of the world to combine images of.
            Should be the name of a subdirectory located in this instance's `tiles_dir`.
        @param detail: The level of detail, 0 up through 3, to use for this map.
            Will correspond to which numbered subdirectory within the given world to use images from.
        """
        if world not in self.mapped_worlds:
            raise ValueError(f'No world directory of name "{world}" exists in "{self.tiles_dir}"')
        if not (0 <= detail <= 3):
            raise ValueError(f'Detail level must be between 0 and 3; given {detail}')
        source_dir: Path = self.tiles_dir / world / str(detail)

        # Sort out what regions we're going to stitch
        columns: set[int] = set()
        rows: set[int] = set()
        regions: dict[int, dict[int, Path]] = {}
        logger.info('Sorting through tile images...')
        for img in tqdm(source_dir.glob('*_*.png'), disable=not self.use_tqdm):
            col, row = map(int, img.stem.split('_'))
            if col not in regions:
                columns.add(col)
                regions[col] = {}
            if row not in regions[col]:
                rows.add(row)
                regions[col][row] = img

        column_range = range(min(columns), max(columns) + 1)
        row_range = range(min(rows), max(rows) + 1)

        if area:
            area_regions = Rectangle([n // self.TILE_SIZE for n in snap_box(area, self.TILE_SIZE)])
            column_range = range(area_regions[0], area_regions[2] + 1)
            row_range = range(area_regions[1], area_regions[3] + 1)

        # Start stitching
        out = Image.new(mode='RGBA', size=(self.TILE_SIZE * len(columns), self.TILE_SIZE * len(rows)))
        logger.info('Constructing image...')

        ta = time.perf_counter()
        for c in tqdm(regions, disable=not self.use_tqdm):
            if c not in column_range:
                continue
            for r in tqdm(regions[c], disable=not self.use_tqdm, leave=False):
                if r not in row_range:
                    continue
                x, y = self.TILE_SIZE * (c - min(columns)), self.TILE_SIZE * (r - min(rows))
                out.paste(Image.open(regions[c][r]), (x, y, x + self.TILE_SIZE, y + self.TILE_SIZE))

        # Trim excess
        if autotrim:
            box = out.getbbox()
            if not box:
                raise CombineError('getbbox() failed')
            logger.info(f'Trimming out blank space to leave an image of {box[2] - box[0]}x{box[3] - box[1]}...')
            out = out.crop(box)

        # Crop if an area is specified
        if area:
            crop_area = (area[0] + (out.width // 2), area[1] + (out.height // 2), area[2] + (out.width // 2), area[3] + (out.height // 2))
            out = out.crop(crop_area)
        tb = time.perf_counter()

        logger.info(f'Finished in {tb - ta:04f}s')
        return out

@logger.catch
def main():
    logger.add(sys.stdout, format="{level}: {message}", level='INFO')

    #region ARGUMENTS

    # if anyone has suggestions for a less cumbersome way to do this than argparse i'm all ears
    parser = argparse.ArgumentParser()
    parser.add_argument('tiles_dir', type=Path, help='A tiles directory generated by squaremap.')
    parser.add_argument('world', type=str, help='Which world (dimension) you want to render a map of.')
    parser.add_argument('detail', type=int,
        help='What detail level to source images from.\n' +
        'Level 3 is 1 block per pixel, 2 is 2x2 per pixel, 1 is 4x4 per pixel, and 0 is 8x8 per pixel.')

    parser.add_argument('--output_dir', type=Path, default=Path('.'),
        help='Directory to save the completed image to.\n' +
        'Defaults to the directory in which this script was run.')

    parser.add_argument('--output_ext', type=str, default='png',
        help='The output file extension (format) to use for the created image. Supports anything Pillow does. (e.g. "png", "jpg", "webp")')

    parser.add_argument('--timestamp', type=str, default=None,
        help='Adds a timestamp of the given format to the beginning of the image file name.\n ' +
        'Default format "%Y-%m-%%d_%H-%M-%S" will be used if "default" is given for this argument.' +
        'See: https://docs.python.org/3/library/datetime.html#format-codes')

    parser.add_argument('--area', type=int, nargs=4, default=None,
        help='A rectangle area of the world (top, left, bottom, right) to export an image from.\n' +
        'This can save time when using a very large world map, as this will only combine the minimum amount of regions' +
        ' needed to cover this area, before finally cropping it down to only the given area.\n' +
        'These values should be the coordinates of the area as they would be in the actual Minecraft world.')

    parser.add_argument('--no-autotrim', action='store_false',
        help='By default, excess empty space is trimmed off of the final image. Using this argument with disable that behavior.')

    parser.add_argument('--force_size', type=int, nargs='+', default=[0],
        help='Centers the assembled map inside an image of this size.\n' +
        'Can be used to make images a consistent size if you\'re using them for a timelapse, for example.\n' +
        'Only specifying one integer for this argument will use the same value for both width and height.')

    args = parser.parse_args()
    tiles_dir   : Path             = args.tiles_dir
    world       : str              = args.world
    detail      : int              = args.detail
    output_dir  : Path             = args.output_dir
    output_ext  : str              = args.output_ext
    time_format : str | None       = args.timestamp
    if time_format == 'default':
        time_format = default_time_format
    area        : Rectangle | None = args.area
    autotrim    : bool             = args.no_autotrim
    if len(args.force_size) > 2:
        raise ValueError('--force_size argument can only take up to 2 integers')
    force_size : tuple[int, int] = tuple(args.force_size) if len(args.force_size) == 2 else (args.force_size[0], args.force_size[0])

    #endregion ARGUMENTS

    print(f"""
Tiles directory: {tiles_dir}
World: {world}
Detail level: {detail}
Output directory: {output_dir.absolute()}
Output file extension: {output_ext}
Add timestamp? {f'True, using format "{time_format}"' if time_format else 'False'}
Specified area: {area if area else 'None, will render the entire map'}
Auto-trim? {autotrim}
Force final size? {('True: ' + str(force_size)) if any(n > 0 for n in force_size) else 'False'}
    """)

    if world in Combiner.STANDARD_WORLDS:
        world = 'minecraft_' + world

    timestamp = (datetime.strftime(datetime.now(), time_format) + '_') if time_format else ''

    out_file: Path = output_dir / f'{timestamp}{world}-{detail}.{output_ext}'
    combiner = Combiner(tiles_dir, use_tqdm=True)
    image = combiner.combine(world, detail, autotrim=autotrim, area=area)

    if all(n > 0 for n in force_size):
        resized = Image.new(mode='RGBA', size=force_size)
        logger.info(f'Resizing canvas to {resized.size[0]}x{resized.size[1]}...')
        center = resized.size[0] // 2, resized.size[1] // 2

        x1, y1 = center[0] - (image.size[0] // 2), center[1] - (image.size[1] // 2)
        x2, y2 = x1 + image.size[0], y1 + image.size[1]

        resized.paste(image, (x1, y1, x2, y2))
        image = resized

    logger.info(f'Saving to "{out_file}"...')
    image.save(out_file)
    logger.info('Done!')

if __name__ == '__main__':
    main()
