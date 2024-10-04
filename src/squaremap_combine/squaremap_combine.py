import argparse
import sys
import time
from datetime import datetime
from math import floor
from pathlib import Path
from typing import Callable, Optional

from loguru import logger
from PIL import Image
from tqdm import tqdm

logger.remove() # Don't output anything if this is just being imported

Rectangle = tuple[int, int, int, int]

DEFAULT_TIME_FORMAT = '$Y-$m-$d_$H-$M-$S'

yes_to_all = False

def confirm_yn(message: str) -> bool:
    return yes_to_all or (input(f'{message} (y/n) ').strip().lower() == 'y')

def snap_num(num: int | float, multiple: int, snap_method: Callable) -> int:
    """Snaps the given `num` to the smallest or largest (depending on the given `snap_method`) `multiple` it can reside in."""
    return multiple * (snap_method(num / multiple))

def snap_box(box: Rectangle, multiple: int) -> Rectangle:
    """Snaps the given four box coordinates to their lowest `multiple` they can reside in. See `snap_num`.
    Since regions are named based off of their "coordinate" as their top-left point, the lowest multiples are all that matter.
    """
    return tuple(map(lambda n: snap_num(n, multiple, floor), box)) # type: ignore

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
    DETAIL_SBPP: dict[int, int] = {0: 8, 1: 4, 2: 2, 3: 1}
    """Square-blocks-per-pixel for each detail level."""
    def __init__(self, tiles_dir: str | Path, use_tqdm=False, interactive: bool=False):
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir = tiles_dir
        self.mapped_worlds: list[str] = [p.stem for p in tiles_dir.glob('minecraft_*/')]
        self.use_tqdm = use_tqdm
        self.interactive = interactive

    def combine(self, world: str | Path, detail: int, autotrim: bool=False, area: Optional[Rectangle]=None) -> Image.Image | None:
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

        # Deep-sort columns + rows
        regions = {k:{v:regions[k][v] for v in sorted(regions[k].keys())} for k in sorted(regions.keys())}

        column_range = range(min(columns), max(columns) + 1)
        row_range = range(min(rows), max(rows) + 1)

        if area:
            area = Rectangle([n // self.DETAIL_SBPP[detail] for n in area])
            area_regions = Rectangle([n // self.TILE_SIZE for n in snap_box(area, self.TILE_SIZE)])
            column_range = range(area_regions[0], area_regions[2] + 1)
            row_range = range(area_regions[1], area_regions[3] + 1)

        size_estimate = f'{self.TILE_SIZE * len(column_range)}x{self.TILE_SIZE * len(row_range)}'
        if self.interactive:
            if not confirm_yn(f'Estimated image size: {size_estimate}\nContinue?'):
                logger.info('Cancelling...')
                return

        # Start stitching
        out = Image.new(mode='RGBA', size=(self.TILE_SIZE * len(column_range), self.TILE_SIZE * len(row_range)))
        logger.info('Constructing image...')

        status_callback: Callable = tqdm.write if self.use_tqdm else lambda s: None

        ta = time.perf_counter()
        top_left_region: tuple[int, int] | None = None
        for c in tqdm(regions, disable=not self.use_tqdm, desc='Columns'):
            if c not in column_range:
                continue
            for r in tqdm(regions[c], disable=not self.use_tqdm, leave=False, desc='Rows'):
                if r not in row_range:
                    continue
                if not top_left_region:
                    top_left_region = (c, r)
                x, y = self.TILE_SIZE * (c - min(column_range)), self.TILE_SIZE * (r - min(row_range))
                if self.use_tqdm:
                    status_callback(f'Pasting image: {regions[c][r]}')
                paste_area = Rectangle([
                    x,
                    y,
                    (x + self.TILE_SIZE),
                    (y + self.TILE_SIZE)
                ])
                out.paste(Image.open(regions[c][r]), paste_area)

        assert(top_left_region)

        diff_from_origin = (0 - (self.TILE_SIZE * top_left_region[0]), 0 - (self.TILE_SIZE * top_left_region[1]))

        # Crop if an area is specified
        if area:
            crop_area = (
                area[0] + diff_from_origin[0],
                area[1] + diff_from_origin[1],
                area[2] + diff_from_origin[0],
                area[3] + diff_from_origin[1]
            )
            out = out.crop(crop_area)

        # Trim excess
        if autotrim:
            bbox = out.getbbox()
            if not bbox:
                raise CombineError('getbbox() failed')
            logger.info(f'Trimming out blank space... ({out.width}x{out.height} -> {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]})')
            out = out.crop(bbox)

        tb = time.perf_counter()

        logger.info(f'Finished in {tb - ta:04f}s')
        return out

@logger.catch
def main():
    global yes_to_all # pylint: disable=global-statement

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

    parser.add_argument('--timestamp', type=str, default='',
        help='Adds a timestamp of the given format to the beginning of the image file name.\n ' +
        'Default format "$Y-$m-$d_$H-$M-$S" will be used if "default" is given for this argument.\n' +
        'See: https://docs.python.org/3/library/datetime.html#format-codes\n' +
        'NOTE: Due to a quirk with the argparse library, you must use a dollar sign ($) instead of a percent symbol for' +
        ' any format strings.')

    parser.add_argument('--overwrite', action='store_true',
        help='Using this flag will allow the script to overwrite an existing file with the same target name if it already' +
        ' exists. By default, if an image with the same path already exists, a numbered suffix is added.')

    parser.add_argument('--area', type=int, nargs=4, default=None, metavar=('X1', 'Y1', 'X2', 'Y2'),
        help='A rectangle area of the world (top, left, bottom, right) to export an image from.\n' +
        'This can save time when using a very large world map, as this will only combine the minimum amount of regions' +
        ' needed to cover this area, before finally cropping it down to only the given area.\n' +
        'These values should be the coordinates of the area as they would be in the actual Minecraft world.')

    parser.add_argument('--no-autotrim', action='store_false',
        help='By default, excess empty space is trimmed off of the final image. Using this argument with disable that behavior.')

    parser.add_argument('--force_size', type=int, nargs='+', default=[0], metavar=('WIDTH', 'HEIGHT'),
        help='Centers the assembled map inside an image of this size.\n' +
        'Can be used to make images a consistent size if you\'re using them for a timelapse, for example.\n' +
        'Only specifying one integer for this argument will use the same value for both width and height.')

    parser.add_argument('-y', '--yes-to-all', action='store_true',
        help='Automatically accepts any requests for user confirmation.')

    args = parser.parse_args()

    tiles_dir   : Path = args.tiles_dir
    world       : str  = args.world
    detail      : int  = args.detail
    output_dir  : Path = args.output_dir
    output_ext  : str  = args.output_ext
    time_format : str  = args.timestamp
    if time_format == 'default':
        time_format = DEFAULT_TIME_FORMAT
    time_format = time_format.replace('$', '%')

    overwrite   : bool             = args.overwrite
    area        : Rectangle | None = args.area
    autotrim    : bool             = args.no_autotrim
    if len(args.force_size) > 2:
        raise ValueError('--force_size argument can only take up to 2 integers')
    force_size: tuple[int, int] = tuple(args.force_size) if len(args.force_size) == 2 else (args.force_size[0], args.force_size[0])
    yes_to_all = args.yes_to_all

    #endregion ARGUMENTS

    logger.info(f"""
Tiles directory: {tiles_dir}
World: {world}
Detail level: {detail}
Output directory: {output_dir.absolute()}
Output file extension: {output_ext}
Add timestamp? {f'True, using format "{time_format}"' if time_format else 'False'}
Allow overwriting images? {overwrite}
Specified area: {area if area else 'None, will render the entire map'}
Auto-trim? {autotrim}
Force final size? {('True: ' + str(force_size)) if any(n > 0 for n in force_size) else 'False'}
    """)

    if not confirm_yn('Continue with these parameters?'):
        logger.info('Cancelling...')
        return

    if world in Combiner.STANDARD_WORLDS:
        world = 'minecraft_' + world

    timestamp = (datetime.strftime(datetime.now(), time_format) + '_') if time_format else ''

    out_file: Path = output_dir / f'{timestamp}{world}-{detail}.{output_ext}'
    if out_file.exists() and (not overwrite):
        copies = [*output_dir.glob(f'{out_file.stem}*')]
        out_file = Path(out_file.stem + f'_{len(copies)}.' + output_ext)

    combiner = Combiner(tiles_dir, use_tqdm=True, interactive=True)
    image = combiner.combine(world, detail, autotrim=autotrim, area=area)

    if not image:
        logger.info('No image was created, either due to failure or user cancellation. Exiting...')
        return

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
