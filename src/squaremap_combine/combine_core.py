"""Core functionality for squaremap_combine, providing the `Combiner` class amongst others."""

import operator
import time
from pathlib import Path
from typing import Callable, Iterator, Literal, Optional, TypeVar

from loguru import logger
from PIL import Image, ImageDraw
from tqdm import tqdm
from tqdm.contrib.itertools import product as tqdm_product

from squaremap_combine.errors import AssertionMessage, CombineError
from squaremap_combine.helper import (confirm_yn, copy_method_signature,
                                      snap_box)
from squaremap_combine.type_alias import ColorRGB, ColorRGBA, Rectangle

logger.remove() # Don't output anything if this is just being imported

T = TypeVar('T')

DEFAULT_TIME_FORMAT = '?Y-?m-?d_?H-?M-?S'
DEFAULT_COORDS_FORMAT = '({x}, {y})'

DETAIL_SBPP: dict[int, int] = {0: 8, 1: 4, 2: 2, 3: 1}
"""Square-blocks-per-pixel for each detail level."""

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
        if direction == 'r':
            return Coord2i(math_op(other[0], self.x), math_op(other[1], self.y))
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

class GameCoord(Coord2i):
    """A coordinate as relative to a Minecraft world.
    Largely identical to `Coord2i`, but used mainly for typing to more effectively signal what kind of coordinate is expected
    for a given class or function.
    """
    def __repr__(self):
        return f'GameCoord(x={self.x}, y={self.y})'

    def to_image_coord(self, image: 'MapImage'):
        """Converts this Minecraft coordinate to its position on the given `MapImage`."""
        return image.game_zero + (self // image.detail_mul)

class MapImageCoord(Coord2i):
    """A coordinate as relative to a `MapImage`.
    Largely identical to `Coord2i`, but used mainly for typing to more effectively signal what kind of coordinate is expected
    for a given class or function.
    """
    def __repr__(self):
        return f'MapImageCoord(x={self.x}, y={self.y})'

    def to_game_coord(self, image: 'MapImage'):
        """Converts this image coordinate to its position on the Minecraft world it represents."""
        return (self - image.game_zero) * image.detail_mul

class MapImage:
    """A delegator class to extend `Image` with Minecraft-map-specific functionality,
    like automatically recalculating the world's 0, 0 position in the image upon any crops or other changes.
    """
    def __init__(self, image: Image.Image, game_zero: 'MapImageCoord', detail_mul: int):
        """
        :param image: The `Image` to convert.
        :param game_zero: At what coordinate on this image 0, 0 would be located in the Minecraft world it represents.
        :param detail_mul: The detail multiplier for this map.
        """
        self.img = image
        self.game_zero = game_zero
        self.detail_mul = detail_mul

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
        return MapImage(self.img.crop(box), MapImageCoord(*self.game_zero - box[0:2]), self.detail_mul)

    def resize_canvas(self, width: int, height: int, center_on: GameCoord=GameCoord(0, 0)) -> 'MapImage':
        """Returns this image centered within a new canvas of the given size,
        centered by a specified coordinate of the original image.

        :param center_on: What coordinate of the Minecraft world to center the image on. Defaults to 0,0.
        """
        origin_in_image = center_on.to_image_coord(self)
        center_distance = origin_in_image, MapImageCoord(*self.size) - origin_in_image
        paste_area: Rectangle = (
            (width // 2) - center_distance[0].x,
            (height // 2) - center_distance[0].y,
            (width // 2) + center_distance[1].x,
            (height // 2) + center_distance[1].y,
        )
        new_canvas = Image.new(mode=self.mode, size=(width, height))
        new_canvas.paste(self.img, paste_area)
        return MapImage(new_canvas, MapImageCoord(*self.game_zero + paste_area[0:2]), self.detail_mul)

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
            skip_confirmation: bool=False,
            grid_interval: Optional[tuple[int, int]]=None,
            grid_line_color: ColorRGB=(0, 0, 0),
            grid_text_color: ColorRGB=(0, 0, 0),
            grid_coords_format: str=DEFAULT_COORDS_FORMAT,
            bg_color: ColorRGBA=(0, 0, 0, 0)
        ):
        """
        :param tiles_dir: A path to a directory in the same format as what squaremap automatically generates.
            Example:

        .. code-block:: text
            tiles (<- what this path should point to)
            ├───minecraft_overworld
            |   ├───0
            |   ├───1
            |   ├───2
            |   └───3
            ├───minecraft_the_nether
            |   ├───0
            |   ├───1
            |   ├───2
            |   └───3
            └───minecraft_the_end
                ├───0
                ├───1
                ├───2
                └───3

        :param use_tqdm: Whether to show a `tqdm` progress bar for any functions that support it.
        :param skip_confirmation: Whether to skip any confirmation prompts. Setting to `True` allows any function
            in this class to run unattended to.
        :param grid_interval: An X and Y interval that should be used for things like drawing grid lines or coordinates onto \
            the finished image.
        :param grid_line_color: RGBA color to be used for drawing grid lines.
        :param grid_text_color: RGBA color to be used for drawing grid coordinates and other text.
        :param grid_coords_format: A format string to be used when drawing grid coordinates. \
            Valid formatting options are `{x}` and {y}`.
        :param bg_color: RGBA color to be used for the image's background, replacing any transparency.
        """
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir          = tiles_dir
        self.use_tqdm           = use_tqdm
        self.skip_confirmation  = skip_confirmation
        self.grid_interval      = grid_interval or (self.TILE_SIZE, self.TILE_SIZE)
        self.grid_line_color    = grid_line_color
        self.grid_text_color    = grid_text_color
        self.grid_coords_format = grid_coords_format
        self.bg_color           = bg_color

        self.mapped_worlds: list[str] = [p.stem for p in tiles_dir.glob('minecraft_*/')]
        """What valid world folders the given `tiles_dir` contains."""

    def draw_grid_lines(self, image: MapImage) -> None:
        """Draws grid lines onto a `MapImage` at the intervals defined for this `Combiner` instance.

        :param image: The `MapImage` to draw coordinates onto. Its `game_zero` attribute is used as the origin point.
        """
        idraw = ImageDraw.Draw(image.img)
        grid_origin = image.game_zero
        coord_axes: dict[str, set[int]] = {
            'h': set(
                [*range(grid_origin.x, image.width, self.grid_interval[0] // image.detail_mul)] +
                [*range(grid_origin.x, 0, -self.grid_interval[0] // image.detail_mul)]
                ),
            'v': set(
                [*range(grid_origin.y, image.height, self.grid_interval[1] // image.detail_mul)] +
                [*range(grid_origin.y, 0, -self.grid_interval[1] // image.detail_mul)]
                ),
        }

        for x in coord_axes['h']:
            idraw.line((x, 0, x, image.height), fill=self.grid_line_color)
        for y in coord_axes['v']:
            idraw.line((0, y, image.width, y), fill=self.grid_line_color)

    def draw_grid_coords_text(self, image: MapImage) -> None:
        """Draws coordinate text onto a `MapImage` at every interval as defined for this `Combiner` instance.

        :param image: The `MapImage` to draw coordinates onto. Its `game_zero` attribute is used as the origin point.
        """
        bbox_before_grid = image.getbbox()
        assert bbox_before_grid

        grid_origin = image.game_zero

        coord_axes: dict[str, set[int]] = {
            'h': set(
                [*range(grid_origin.x, image.width, self.grid_interval[0] // image.detail_mul)] +
                [*range(grid_origin.x, 0, -self.grid_interval[0] // image.detail_mul)]
                ),
            'v': set(
                [*range(grid_origin.y, image.height, self.grid_interval[1] // image.detail_mul)] +
                [*range(grid_origin.y, 0, -self.grid_interval[1] // image.detail_mul)]
                ),
        }

        interval_coords: list[MapImageCoord] = [MapImageCoord(x, y) for x in coord_axes['h'] for y in coord_axes['v']]
        total_intervals = len(interval_coords)

        if total_intervals > 50000:
            logger.warning('More than 50,000 grid intervals will be iterated over; this may take some time.')
            if not confirm_yn('More than 50,000 grid intervals will be iterated over, which can take a very long time.' +
                ' You can press Ctrl+C to cancel during this process if needed. Continue?'):
                logger.info('Cancelling...')
                return
        elif total_intervals > 5000:
            logger.info('More than 5000 grid intervals will be iterated over;' +
                ' the progress bar\'s description text will not update per iteration in order to save speed.')

        logger.info('Drawing coordinates...')
        idraw = ImageDraw.Draw(image.img)
        for img_coord in (pbar := tqdm(interval_coords, disable=not self.use_tqdm)):
            game_coord = img_coord.to_game_coord(image)
            coord_text = self.grid_coords_format.format(x=game_coord.x, y=game_coord.y)
            if self.use_tqdm and (total_intervals <= 5000):
                pbar.set_description(f'Drawing {coord_text} at {img_coord.as_tuple()}')
            idraw.text(xy=img_coord.as_tuple(), text=str(coord_text), fill=self.grid_text_color)

    def combine(self,
            world: str | Path,
            detail: int,
            autotrim: bool=False,
            area: Optional[Rectangle]=None,
            force_size: Optional[tuple[int, int]]=None,
            show_grid_lines: bool=False,
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
        :param show_grid_lines: Adds a grid of lines at every interval defined for this `Combiner` instance.
        :param show_grid_coords: Adds Minecraft coordinates to the top-left of every interval intersection on this image.

        :returns: Returns the created `MapImage` if successful, or `None` if the process failed or was cancelled at any point.
        :rtype: MapImage, None
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
        if not confirm_yn(f'Estimated image size: {size_estimate}\nContinue?', self.skip_confirmation):
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
                game_zero_in_image = Coord2i(x, y) - (Coord2i(c, r) * self.TILE_SIZE)
            image.paste((tile_img := Image.open(tile_path)), paste_area, mask=tile_img)

        assert game_zero_in_image, AssertionMessage.GAME_ZERO_IS_NONE
        image = MapImage(image, MapImageCoord(*game_zero_in_image), detail_mul)
        del game_zero_in_image

        # Crop if an area is specified
        if area:
            crop_area = (
                *GameCoord(area[0], area[1]).to_image_coord(image).as_tuple(),
                *GameCoord(area[2], area[3]).to_image_coord(image).as_tuple()
            )
            image = image.crop(crop_area)
            autotrim = False

        # Crop and resize if given an explicit size
        if force_size and all(n > 0 for n in force_size):
            logger.info(f'Resizing to {force_size[0]}x{force_size[1]}...')
            image = image.resize_canvas(*force_size)
            autotrim = False

        # Things like grid lines and coordinate text are likely to end up drawn outside of the image's original bounding box,
        # alterting what getbbox() would return. Get this bounding box *first*, and then use it to autotrim later.
        bbox = image.getbbox()
        assert bbox, AssertionMessage.BBOX_IS_NONE

        # Add grid and/or coordinates
        if show_grid_lines or show_grid_coords:
            if not self.grid_interval:
                raise CombineError('A grid interval must be set for this Combiner instance to add grid lines or grid coordinates')

            if show_grid_coords:
                self.draw_grid_coords_text(image)

            if show_grid_lines:
                logger.info('Drawing grid lines...')
                self.draw_grid_lines(image)

        # Trim transparent excess space
        if autotrim:
            logger.info(f'Trimming out blank space... ({image.width}x{image.height} -> {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]})')
            image = image.crop(bbox)

        # Apply desired background color, if any
        if self.bg_color != (0, 0, 0, 0):
            image_bg = Image.new('RGBA', size=image.size, color=self.bg_color)
            image_bg.alpha_composite(image.img)
            image = MapImage(image_bg, image.game_zero, image.detail_mul)

        # Done.
        tb = time.perf_counter()
        logger.info(f'Image creation finished in {tb - ta:04f}s')

        return image
