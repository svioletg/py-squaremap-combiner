import argparse
import operator
import sys
import textwrap
import time
from datetime import datetime
from functools import wraps
from itertools import batched
from math import floor
from pathlib import Path
from typing import (Any, Callable, Concatenate, Iterator, Literal, Optional,
                    ParamSpec, TypeVar)

from loguru import logger
from PIL import Image, ImageDraw
from tqdm import tqdm
from tqdm.contrib.itertools import product as tqdm_product

logger.remove() # Don't output anything if this is just being imported

T = TypeVar('T')

Rectangle = tuple[int, int, int, int]

ColorRGB = tuple[int, int, int]
ColorRGBA = tuple[int, int, int, int]

DEFAULT_TIME_FORMAT = '?Y-?m-?d_?H-?M-?S'
DEFAULT_COORDS_FORMAT = '({x}, {y})'

DETAIL_SBPP: dict[int, int] = {0: 8, 1: 4, 2: 2, 3: 1}
"""Square-blocks-per-pixel for each detail level."""

yes_to_all = False # pylint: disable=invalid-name; not actually a constant!

def confirm_yn(message: str) -> bool:
    """Prompts the user for confirmation, only returning true if "Y" or "y" was entered."""
    return yes_to_all or (input(f'{message} (y/n) ').strip().lower() == 'y')

def filled_tuple(source_tuple: tuple[T] | tuple[T, T]) -> tuple[T, T]:
    """Takes a tuple of no more than two values, and returns the original tuple if two values are present,
    or a new tuple consisting of the first value having been doubled if only one value is present.
    """
    return source_tuple if len(source_tuple) == 2 else (source_tuple[0], source_tuple[0])

def snap_num(num: int | float, multiple: int, snap_method: Callable) -> int:
    """Snaps the given `num` to the smallest or largest (depending on the given `snap_method`) `multiple` it can reside in."""
    return multiple * (snap_method(num / multiple))

def snap_box(box: Rectangle, multiple: int) -> Rectangle:
    """Snaps the given four box coordinates to their lowest `multiple` they can reside in. See `snap_num`.
    Since regions are named based off of their "coordinate" as their top-left point, the lowest multiples are all that matter.
    """
    return tuple(map(lambda n: snap_num(n, multiple, floor), box)) # type: ignore

def draw_grid(image: Image.Image, interval: int | tuple[int, int], line_color: ColorRGB, origin: tuple[int, int]=(0, 0)) -> None:
    """Draws a grid onto an `Image` with the given intervals.

    :param interval: An interval of pixels at which lines should be drawn.
        Giving a single integer will use the same interval for X and Y, otherwise a tuple of two integers can be given
        to specify each.
    :param line_color: What color to draw the grid lines with.
    :param origin: Where to start drawing grid lines from on the image.
        Lines will be drawn from this position moving outwards in both directions until the edge of the image is reached.
    """
    if isinstance(interval, int):
        interval = interval, interval
    idraw = ImageDraw.Draw(image)
    x, y = origin
    while x <= image.width:
        idraw.line((x, 0, x, image.height), fill=line_color)
        x += interval[0]
    x, y = origin
    while x >= 0:
        idraw.line((x, 0, x, image.height), fill=line_color)
        x -= interval[0]

    x, y = origin
    while y <= image.height:
        idraw.line((0, y, image.width, y), fill=line_color)
        y += interval[1]
    x, y = origin
    while y >= 0:
        idraw.line((0, y, image.width, y), fill=line_color)
        y -= interval[1]

P = ParamSpec('P')

def copy_method_signature(source: Callable[Concatenate[Any, P], T]) -> Callable[[Callable[..., T]], Callable[Concatenate[Any, P], T]]:
    """Copies a method signature onto the decorated method.

    Taken from: https://github.com/python/typing/issues/270#issuecomment-1346124813
    """
    def wrapper(target: Callable[..., T]) -> Callable[Concatenate[Any, P], T]:
        @wraps(source)
        def wrapped(self: Any, /, *args: P.args, **kwargs: P.kwargs) -> T: # pylint: disable=no-member
            return target(self, *args, **kwargs)
        return wrapped
    return wrapper

class CombineError(Exception):
    """Raised when anything in the image combination process fails when
    no other type of exception would be applicable.
    """

class Coord2i:
    """Represents a 2D integer coordinate pair."""
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self):
        return f'Coord2i(x={self.x}, y={self.y})'

    def __str__(self):
        return f'({self.x}, {self.y})'

    def __iter__(self) -> Iterator[int]:
        for i in [self.x, self.y]:
            yield i

    def as_tuple(self) -> tuple[int, int]:
        """Returns the coordinate as a tuple."""
        return (self.x, self.y)

    def _math(self, math_op: Callable, other: 'int | tuple[int, int] | Coord2i', direction: Literal['l', 'r']='l') -> 'Coord2i':
        if isinstance(other, int):
            other = (other, other)
        elif isinstance(other, Coord2i):
            other = (other.x, other.y)

        if direction == 'l':
            return Coord2i(math_op(self.x, other[0]), math_op(self.y, other[1]))
        elif direction == 'r':
            return Coord2i(math_op(other[0], self.x), math_op(other[1], self.y))
        else:
            raise ValueError(f'_math direction must be "l" or "r"; got {direction!r}')

    def __add__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.add, other)
    def __radd__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.add, other, 'r')

    def __sub__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.sub, other)
    def __rsub__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.sub, other, 'r')

    def __mul__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.mul, other)
    def __rmul__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.mul, other, 'r')

    def __floordiv__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.floordiv, other)
    def __rfloordiv__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.floordiv, other, 'r')

    def __pow__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.pow, other)
    def __rpow__(self, other: 'int | tuple[int, int] | Coord2i') -> 'Coord2i':
        return self._math(operator.pow, other, 'r')

class MapImage:
    """A delegator class to extend `Image` with Minecraft-map-specific functionality,
    like automatically recalculating the world's 0, 0 position in the image upon any crops or other changes.
    """
    def __init__(self, image: Image.Image, game_zero: Coord2i, detail_mul: int):
        """
        :param image: The `Image` to convert.
        :param game_zero: At what coordinate on this image 0, 0 would be located in the Minecraft world it represents.
        :param detail_mul: The detail multiplier for this map.
        """
        self.img = image
        self.game_zero = game_zero
        self.detail_mul = detail_mul

    def __getattr__(self, key):
        if key == 'img':
            raise AttributeError
        return getattr(self.img, key)

    @property
    def mode(self): # pylint: disable=missing-function-docstring
        return self.img.mode
    @property
    def size(self): # pylint: disable=missing-function-docstring
        return self.img.size
    @property
    def width(self): # pylint: disable=missing-function-docstring
        return self.img.width
    @property
    def height(self): # pylint: disable=missing-function-docstring
        return self.img.height

    def with_image(self, new_image: Image.Image) -> 'MapImage':
        """Returns a copy of this `MapImage` with only the internal `Image` object changed."""
        return MapImage(new_image, self.game_zero, self.detail_mul)

    def game_coord_in_image(self, coordinate_in_game: Coord2i) -> Coord2i:
        """Takes a coordinate within the Minecraft world this image represents,
        and returns the location of that coordinate's location within the image.
        """
        return self.game_zero + (coordinate_in_game // self.detail_mul)

    def image_coord_in_game(self, coordinate_in_image: Coord2i) -> Coord2i:
        """Takes a coordinate within the image, and returns the corresponding coordinate within the Minecraft world
        this image represents.
        """
        return (coordinate_in_image - self.game_zero) * self.detail_mul

    # Copy signatures for intellisense
    @copy_method_signature(Image.Image.getbbox)
    def getbbox(self): # pylint: disable=missing-function-docstring
        return self.img.getbbox()
    @copy_method_signature(Image.Image.paste)
    def paste(self, *args, **kwargs): # pylint: disable=missing-function-docstring
        self.img.paste(*args, **kwargs)
    @copy_method_signature(Image.Image.save)
    def save(self, *args, **kwargs): # pylint: disable=missing-function-docstring
        self.img.save(*args, **kwargs)

    def crop(self, box: Rectangle) -> 'MapImage':
        """Returns a cropped portion of the original image, along with an accordingly updated `game_zero` property."""
        return MapImage(self.img.crop(box), self.game_zero - Coord2i(*box[0:2]), self.detail_mul)

    def resize_canvas(self, width: int, height: int, center_on: Coord2i=Coord2i(0, 0)) -> 'MapImage':
        """Returns this image centered within a new canvas of the given size,
        centered by a specified coordinate of the original image.

        :param center_on: What coordinate of the Minecraft world to center the image on. Defaults to 0,0.
        """
        center_on = self.game_coord_in_image(center_on)
        center_distance = center_on, Coord2i(*self.img.size) - center_on
        paste_area: Rectangle = *((width // 2) - center_distance[0]).as_tuple(), *((width // 2) + center_distance[1]).as_tuple()
        new_canvas = Image.new(mode=self.img.mode, size=(width, height))
        new_canvas.paste(self.img, paste_area)
        return MapImage(new_canvas, self.game_zero + Coord2i(*paste_area[0:2]), self.detail_mul)

class Combiner:
    """Takes a squaremap `tiles` directory path, handles calculating rows/columns,
    and is able to export full map images.
    """
    TILE_SIZE: int = 512
    """The size of each tile image in pixels.
    Only made a constant in case squaremap happens to change its image sizes in the future.
    """
    STANDARD_WORLDS: list[str] = ['overworld', 'the_nether', 'the_end']
    def __init__(self,
            tiles_dir: str | Path,
            use_tqdm=False,
            interactive: bool=False,
            grid_interval: Optional[tuple[int, int]]=None,
            grid_color: ColorRGB=(0, 0, 0),
            grid_coords_format: str=DEFAULT_COORDS_FORMAT,
            bg_color: ColorRGBA=(0, 0, 0, 0)
        ):
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir = tiles_dir
        self.mapped_worlds: list[str] = [p.stem for p in tiles_dir.glob('minecraft_*/')]
        self.use_tqdm = use_tqdm
        self.interactive = interactive
        self.grid_interval = grid_interval
        self.grid_color = grid_color
        self.grid_coords_format = grid_coords_format
        self.bg_color = bg_color

    def _add_grid_to_image(self,
            image: MapImage,
            show_grid_lines: bool,
            show_grid_coords: bool,
            coords_format_string: str=DEFAULT_COORDS_FORMAT
        ) -> tuple[MapImage, Rectangle] | None:
        if not self.grid_interval:
            raise CombineError('A grid interval must be set for this Combiner instance to add grid lines or grid coordinates')
        # grid_origin starts out the same as the game's origin coord, which is used as a basic orientation point
        # before moving by intervals from 0, 0 until the point is within the image
        # (otherwise the grid calculations later won't work)
        grid_origin = image.game_zero

        # Make sure the grid origin is within the image, or else this won't work
        while grid_origin.x > image.width:
            grid_origin.x -= self.grid_interval[0] // image.detail_mul
        while grid_origin.y > image.height:
            grid_origin.y -= self.grid_interval[1] // image.detail_mul

        if show_grid_coords:
            coord_axes = {'h': set(), 'v': set()}

            # Remove large empty areas, but still keep things in easily workable dimensions
            bbox_before_grid = image.getbbox()
            assert(bbox_before_grid)

            x, y = grid_origin
            while x <= image.width:
                coord_axes['h'].add(x)
                x += self.grid_interval[0] // image.detail_mul
            x = grid_origin.x
            while x >= 0:
                coord_axes['h'].add(x)
                x -= self.grid_interval[0] // image.detail_mul

            while y <= image.height:
                coord_axes['v'].add(y)
                y += self.grid_interval[1] // image.detail_mul
            y = grid_origin.y
            while y >= 0:
                coord_axes['v'].add(y)
                y -= self.grid_interval[1] // image.detail_mul
            del x, y

            interval_coords: list[Coord2i] = [Coord2i(x, y) for x in coord_axes['h'] for y in coord_axes['v']]
            total_intervals = len(interval_coords)

            if total_intervals > 50000:
                logger.warning('More than 50,000 grid intervals will be iterated over; this may take some time.')
                if not confirm_yn('More than 50,000 grid intervals will be iterated over, which can take a very long time.' +
                    ' You can press Ctrl+C to cancel during this process if needed. Continue?'):
                    logger.info('Cancelling...')
                    return None
            elif total_intervals > 5000:
                logger.info('More than 5000 grid intervals will be iterated over;' +
                    ' the progress bar\'s description text will not update per iteration in order to save speed.')

            logger.info('Drawing coordinates...')
            idraw = ImageDraw.Draw(image.img)
            for img_coord in (pbar := tqdm(interval_coords, disable=not self.use_tqdm)):
                game_coord = image.image_coord_in_game(img_coord)
                coord_text = coords_format_string.format(x=game_coord.x, y=game_coord.y)
                if self.use_tqdm and (total_intervals <= 5000):
                    pbar.set_description(f'Drawing {coord_text} at {img_coord.as_tuple()}')
                idraw.text(xy=img_coord.as_tuple(), text=str(coord_text), fill=self.grid_color)

        if show_grid_lines:
            logger.info('Drawing grid lines...')
            draw_grid(
                image.img,
                (self.grid_interval[0] // image.detail_mul, self.grid_interval[1] // image.detail_mul),
                self.grid_color,
                (grid_origin.x, grid_origin.y)
            )
        return image, bbox_before_grid

    def combine(self,
            world: str | Path,
            detail: int,
            autotrim: bool=False,
            area: Optional[Rectangle]=None,
            force_size: Optional[tuple[int, int]]=None,
            use_grid: bool=False,
            show_grid_coords: bool=False
        ) -> MapImage | None:
        """Combine the given world (dimension) tile images into one large map.

        :param world: Name of the world to combine images of.\
            Should be the name of a subdirectory located in this instance's `tiles_dir`.
        :param detail: The level of detail, 0 up through 3, to use for this map.\
            Will correspond to which numbered subdirectory within the given world to use images from.
        :param area: Specifies an area of the world to export rather than rendering the full map.\
            Takes coordinates as they would appear in Minecraft. Using this will disable `autotrim` implicitly.
        :param force_size: Centers the final image in a new image of this size.\
            Using this will disable `autotrim` implicitly.
        :param use_grid: Draws a grid onto this image.\
            Uses this `Combiner` instance's `grid_interval` and `grid_color` properties.
        :param show_grid_coords: Adds Minecraft coordinates to the top-left of every `grid_interval` intersection on this image.\
            This can be used on its own without `use_grid` to draw only the coordinate text.
        """
        if world not in self.mapped_worlds:
            raise ValueError(f'No world directory of name "{world}" exists in "{self.tiles_dir}"')
        if not (0 <= detail <= 3):
            raise ValueError(f'Detail level must be between 0 and 3; given {detail}')
        source_dir: Path = self.tiles_dir / world / str(detail)

        detail_mul = DETAIL_SBPP[detail]

        # Sort out what regions we're going to stitch
        columns: set[int] = set()
        rows: set[int] = set()
        regions: dict[int, dict[int, Path]] = {}
        logger.info('Finding region images...')
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
            area = Rectangle([n // detail_mul for n in area])
            area_regions = Rectangle([n // self.TILE_SIZE for n in snap_box(area, self.TILE_SIZE)])
            column_range = range(area_regions[0], area_regions[2] + 1)
            row_range = range(area_regions[1], area_regions[3] + 1)

        size_estimate = f'{self.TILE_SIZE * len(column_range)}x{self.TILE_SIZE * len(row_range)}'
        if self.interactive:
            if not confirm_yn(f'Estimated image size: {size_estimate}\nContinue?'):
                logger.info('Cancelling...')
                return None

        # Start stitching
        image = Image.new(
            mode='RGBA',
            size=(self.TILE_SIZE * len(column_range), self.TILE_SIZE * len(row_range))
        )
        logger.info('Constructing image...')

        ta = time.perf_counter()
        # Represents where 0, 0 in our Minecraft world is, in relation to the image's coordinates
        game_zero_in_image: Coord2i | None = None
        for c, r in tqdm_product(column_range, row_range, disable=not self.use_tqdm, desc='Columns'):
            if (c not in regions) or (r not in regions[c]):
                continue
            # The pasting coordinates are determined based on what current column and row the for loops
            # are on, so they'll increase by a tile regardless of whether an image has actually been pasted
            x, y = self.TILE_SIZE * (c - min(column_range)), self.TILE_SIZE * (r - min(row_range))
            tile_path = regions[c][r]
            if self.use_tqdm:
                tqdm.write(f'Pasting image: {tile_path}')
            paste_area = Rectangle([x, y, x + self.TILE_SIZE, y + self.TILE_SIZE])
            if not game_zero_in_image:
                game_zero_in_image = (Coord2i(x, y) - (Coord2i(c, r) * self.TILE_SIZE)) // detail_mul
            image.paste((tile_img := Image.open(tile_path)), paste_area, mask=tile_img)

        assert(game_zero_in_image)
        image = MapImage(image, game_zero_in_image, detail_mul)

        # If a specific area of the Minecraft world is desired, we need to find out where 0,0 would be
        # in relation to the image that's been created (its coordinates aren't helpful, as the top left will always be 0,0)
        # Tiles are always the same size, and the top left coordinate of the 0,0 region is also 0,0
        # So by seeing how far away the top left region used in the image is from that, we have our in-game coordinates
        top_left_region: tuple[int, int] = column_range[0], row_range[0]
        top_left_game_coord = Coord2i(*top_left_region) * detail_mul * self.TILE_SIZE

        # Crop if an area is specified
        if area:
            crop_area = (
                *image.game_coord_in_image(Coord2i(area[0], area[1])).as_tuple(),
                *image.game_coord_in_image(Coord2i(area[2], area[3])).as_tuple()
            )
            image = image.crop(crop_area)
            autotrim = False

        # Once the image has been cropped, this is no longer useful
        del top_left_game_coord

        # Crop and resize if given an explicit size
        if force_size and all(n > 0 for n in force_size):
            logger.info(f'Resizing to {force_size[0]}x{force_size[1]}...')
            image = image.resize_canvas(*force_size)
            autotrim = False

        # Add grid and/or coordinates
        if use_grid or show_grid_coords:
            if result := self._add_grid_to_image(image, show_grid_coords, use_grid, coords_format_string=self.grid_coords_format):
                image, bbox_before_grid = result
            else:
                return None

        # Trim excess
        if autotrim:
            if use_grid or show_grid_coords:
                bbox = bbox_before_grid
            else:
                bbox = image.getbbox()
            if not bbox:
                raise CombineError('getbbox() failed! This is likely a bug with the script;' +
                    ' please open an issue at https://github.com/svioletg/py-squaremap-combiner/issues and provide the above traceback')
            logger.info(f'Trimming out blank space... ({image.width}x{image.height} -> {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]})')
            image = image.crop(bbox)

        # Apply desired background color, if any
        if self.bg_color != (0, 0, 0, 0):
            image_bg = Image.new('RGBA', size=image.size, color=self.bg_color)
            image_bg.alpha_composite(image.img)
            image = MapImage(image_bg, image.game_zero, image.detail_mul)

        tb = time.perf_counter()

        logger.info(f'Finished in {tb - ta:04f}s')
        return image

def opt(*names: str) -> list[str]:
    """Short for "option". Returns the given argument names with underscore versions appended."""
    return [*names] + [('--' + n.lstrip('-').replace('-', '_')) for n in names if '-' in n.lstrip('-')]

@logger.catch
def main(): # pylint: disable=missing-function-docstring
    global yes_to_all # pylint: disable=global-statement

    logger.level('WARNING', color='<yellow>')
    logger.level('ERROR', color='<red>')
    logger.add(sys.stdout, colorize=True, format="<level>{level}: {message}</level>", level='INFO')

    #region ARGUMENTS

    # if anyone has suggestions for a less cumbersome way to do this than argparse i'm all ears
    parser = argparse.ArgumentParser()
    parser.add_argument('tiles_dir', type=Path, help='A tiles directory generated by squaremap.')
    parser.add_argument('world', type=str, help='Which world (dimension) you want to render a map of.')
    parser.add_argument('detail', type=int,
        help='What detail level to source images from.\n' +
        'Level 3 is 1 block per pixel, 2 is 2x2 per pixel, 1 is 4x4 per pixel, and 0 is 8x8 per pixel.')

    parser.add_argument(*opt('--output-dir'), '-o', type=Path, default=Path('.'), metavar='PATH',
        help='Directory to save the completed image to.\n' +
        'Defaults to the directory in which this script was run.')

    parser.add_argument(*opt('--output-ext'), '-ext', type=str, default='png', metavar='EXTENSION',
        help='The output file extension (format) to use for the created image. Supports anything Pillow does. (e.g. "png", "jpg", "webp")')

    parser.add_argument(*opt('--timestamp'), '-t', type=str, nargs='*', default='', metavar='FORMAT_STRING',
        help='Adds a timestamp of the given format to the beginning of the image file name.\n ' +
        'Default format "?Y-?m-?d_?H-?M-?S" will be used if no format is specified after this argument.\n' +
        'See: https://docs.python.org/3/library/datetime.html#format-codes\n' +
        'NOTE: Due to a quirk with the argparse library, you must use a question mark (?) instead of a percent symbol for' +
        ' any format strings.')

    parser.add_argument(*opt('--overwrite'), '-ow', action='store_true',
        help='Using this flag will allow the script to overwrite an existing file with the same target name if it already' +
        ' exists. By default, if an image with the same path already exists, a numbered suffix is added.')

    parser.add_argument(*opt('--area'), '-a', type=int, nargs=4, default=None, metavar=('X1', 'Y1', 'X2', 'Y2'),
        help='A rectangle area of the world (top, left, bottom, right) to export an image from.\n' +
        'This can save time when using a very large world map, as this will only combine the minimum amount of regions' +
        ' needed to cover this area, before finally cropping it down to only the given area.\n' +
        'These values should be the coordinates of the area as they would be in the actual Minecraft world.')

    parser.add_argument(*opt('--no-autotrim'), action='store_false',
        help='By default, excess empty space is trimmed off of the final image. Using this argument with disable that behavior.')

    parser.add_argument(*opt('--force-size'), '-fs', type=int, nargs='+', default=[0], metavar=('WIDTH', 'HEIGHT'),
        help='Centers the assembled map inside an image of this size.\n' +
        'Can be used to make images a consistent size if you\'re using them for a timelapse, for example.\n' +
        'Only specifying one integer for this argument will use the same value for both width and height.')

    parser.add_argument(*opt('--use-grid'), '-g', type=int, nargs='+', default=[0], metavar=('X_INTERVAL, Y_INTERVAL'),
        help='Adds a grid onto the final image in the given X and Y intervals.\n' +
        'If only X_INTERVAL is given, the same interval will be used for both X and Y grid lines.\n' +
        'The resulting grid will be based on the coordinates as they would be in Minecraft, not of the image itself.')

    parser.add_argument(*opt('--show-coords'), '-gc', action='store_true',
        help='Adds coordinate text to every grid interval intersection. Requires the use of the --use-grid option.')

    parser.add_argument(*opt('--coords-format'), '-gcf', type=str, metavar='FORMAT_STRING', default=DEFAULT_COORDS_FORMAT,
        help='A string to format how grid coordinates appear. Use "{x}" and "{y}" (curly-braces included)' +
        ' where you want the X and Y coordinates to appear, e.g. "X: {x} Y: {y}" could appear as "X: 100 Y: 200".')

    parser.add_argument(*opt('--background'), '-bg', nargs='+', default=(0, 0, 0, 0), metavar=('HEXCODE or RGBA'),
        help='Specify an RGBA color to use for the background of the image. Empty space is fully transparent by default.\n' +
        'A hexcode (e.g. FF0000) can be used as well, and an 8-character hex code can be used to specify alpha with the last byte.\n' +
        'If only RED, GREEN, and BLUE are given, the alpha is set to 255 (fully opaque) automatically.')

    parser.add_argument(*opt('--yes-to-all'), '-y', action='store_true',
        help='Automatically accepts any requests for user confirmation.')

    args = parser.parse_args()

    tiles_dir   : Path = args.tiles_dir
    world       : str  = args.world
    detail      : int  = args.detail
    output_dir  : Path = args.output_dir
    output_ext  : str  = args.output_ext
    time_format: str
    if isinstance(args.timestamp, list):
        if len(args.timestamp) == 0:
            time_format = DEFAULT_TIME_FORMAT
        elif len(args.timestamp) == 1:
            time_format = args.timestamp[0]
        else:
            raise ValueError('Too many arguments given for --timestamp')
    else:
        time_format = args.timestamp
    time_format = time_format.replace('?', '%')

    overwrite   : bool             = args.overwrite
    area        : Rectangle | None = args.area
    autotrim    : bool             = args.no_autotrim
    if len(args.force_size) > 2:
        raise ValueError('--force-size argument can only take up to 2 integers')
    force_size: tuple[int, int] = filled_tuple(args.force_size)

    if len(args.use_grid) > 2:
        raise ValueError('--use-grid argument can only take up to 2 integers')
    grid_interval: tuple[int, int] = filled_tuple(args.use_grid)
    use_grid: bool = all(n > 0 for n in grid_interval)
    show_grid_coords: bool = args.show_coords
    coords_format: str = args.coords_format

    if len(args.background) == 1:
        hex_color: str = args.background[0]
        if len(hex_color) == 3:
            hex_color *= 2
        elif (len(hex_color) != 6) and (len(hex_color) != 8):
            raise ValueError('Given hex color code must be 3, 6, or 8 characters in length')
        rgba = []
        for chunk in batched(hex_color, 2):
            rgba.append(int(''.join(chunk), 16))
        if len(rgba) == 3:
            rgba.append(255)
    elif len(args.background) == 3:
        rgba = args.background + [255]
    elif len(args.background) == 4:
        rgba = args.background
    else:
        raise ValueError('3 or 4 values are required for RGB / RGBA color argument')
    background: ColorRGBA = tuple(map(int, rgba)) # type: ignore

    yes_to_all = args.yes_to_all

    #endregion ARGUMENTS
    logger.info(textwrap.dedent(f"""
        -- BASIC SETTINGS --
        Tiles directory: {tiles_dir}
        World: {world}
        Detail level: {detail}
        Output directory: {output_dir.absolute()}
        Output file extension: {output_ext}
        Specified area: {area if area else 'None, will render the entire map'}
        Background color: {background}

        -- ADDITIONAL OPTIONS --
        Add timestamp? {f'True, using format "{time_format}"' if time_format else 'False'}
        Allow overwriting images? {overwrite}
        Auto-trim? {autotrim}
        Force final size? {('True; ' + str(force_size)) if any(n > 0 for n in force_size) else 'False'}
        Show grid on map? {(f'True; X interval: {grid_interval[0]}, Y interval: {grid_interval[1]}') if use_grid else 'False'}
        Show grid coordinates on map? {show_grid_coords}
        Auto-confirm? {yes_to_all}
    """))

    if not confirm_yn('Continue with these parameters?'):
        logger.info('Cancelling...')
        return None

    if world in Combiner.STANDARD_WORLDS:
        world = 'minecraft_' + world

    timestamp = (datetime.strftime(datetime.now(), time_format) + '_') if time_format else ''

    out_file: Path = output_dir / f'{timestamp}{world}-{detail}.{output_ext}'
    if out_file.exists() and (not overwrite):
        copies = [*output_dir.glob(f'{out_file.stem}*')]
        out_file = Path(out_file.stem + f'_{len(copies)}.' + output_ext)

    combiner = Combiner(
        tiles_dir,
        use_tqdm=True,
        interactive=True,
        grid_interval=grid_interval if use_grid else None,
        grid_coords_format=coords_format,
        bg_color=background
    )

    image = combiner.combine(
        world,
        detail,
        autotrim=autotrim,
        area=area,
        force_size=force_size,
        use_grid=use_grid,
        show_grid_coords=show_grid_coords
    )

    if not image:
        logger.info('No image was created. Exiting...')
        return None

    logger.info(f'Saving to "{out_file}"...')
    image.save(out_file)

    logger.info('Done!')

if __name__ == '__main__':
    main()
