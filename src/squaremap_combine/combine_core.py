"""
Core functionality for squaremap_combine, providing the `Combiner` class amongst others.
"""

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from itertools import product
from pathlib import Path
from typing import Any

from maybetype import Maybe
from PIL import Image, ImageDraw, ImageFont
from tqdm import tqdm

from squaremap_combine.const import SQMAP_DETAIL, SQMAP_DETAIL_LEVELS, SQMAP_TILE_AREA
from squaremap_combine.errors import CombineError, ErrMsg
from squaremap_combine.logging import logger
from squaremap_combine.util import Color, Coord2i, snap_box


class GameCoord(Coord2i):
    """
    A coordinate as relative to a Minecraft world.
    Largely identical to `Coord2i`, but used mainly for typing to more effectively signal what kind of coordinate is
    expected for a given class or function.
    """
    def __repr__(self) -> str:
        return f'GameCoord(x={self.x}, y={self.y})'

    def to_image_coord(self, image: 'MapImage') -> Coord2i:
        """Converts this Minecraft coordinate to its position on the given `MapImage`."""
        return image.game_zero + (self // image.zoom)

class MapImageCoord(Coord2i):
    """
    A coordinate as relative to a `MapImage`.
    Largely identical to `Coord2i`, but used mainly for typing to more effectively signal what kind of coordinate is
    expected for a given class or function.
    """
    def __repr__(self) -> str:
        return f'MapImageCoord(x={self.x}, y={self.y})'

    def to_game_coord(self, image: 'MapImage') -> Coord2i:
        """Converts this image coordinate to its position in the Minecraft world it represents."""
        return (self - image.game_zero) * image.zoom

class MapImage:
    """
    A class to wrap `Image` with Minecraft-map-specific functionality, like automatically recalculating the world's
    `0, 0` position in the image upon any crops or other changes.
    """
    def __init__(self, image: Image.Image, game_zero: 'MapImageCoord', zoom: int) -> None:
        """
        :param image: The `Image` to wrap.
        :param game_zero: At what coordinate in this image `0, 0` would be located in the Minecraft world it represents.
        :param zoom: The squaremap zoom/detail number for this map.
        """
        self.img = image
        self.game_zero = game_zero
        self.zoom = zoom

    @property
    def mode(self) -> str:
        return self.img.mode

    @property
    def size(self) -> tuple[int, int]:
        return self.img.size

    @property
    def width(self) -> int:
        return self.img.width

    @property
    def height(self) -> int:
        return self.img.height

    def with_image(self, new_image: Image.Image) -> 'MapImage':
        """Returns a copy of this `MapImage` with only the internal `Image` object changed."""
        return MapImage(new_image, self.game_zero, self.zoom)

    def crop(self, box: tuple[int, int, int, int]) -> 'MapImage':
        """Returns a cropped portion of the original image with an accordingly updated `game_zero` attribute."""
        return MapImage(self.img.crop(box), MapImageCoord(*self.game_zero - box[0:2]), self.zoom)

    def resize_canvas(self, width: int, height: int) -> 'MapImage':
        """Returns this image centered within a new canvas of the given size."""
        origin_in_image = MapImageCoord(*self.size) // 2
        center_distance = origin_in_image, MapImageCoord(*self.size) - origin_in_image
        paste_area: tuple[int, int, int, int] = (
            (width // 2) - center_distance[0].x,
            (height // 2) - center_distance[0].y,
            (width // 2) + center_distance[1].x,
            (height // 2) + center_distance[1].y,
        )
        new_canvas = Image.new(mode=self.mode, size=(width, height))
        new_canvas.paste(self.img, paste_area)
        return MapImage(new_canvas, MapImageCoord(*self.game_zero + paste_area[0:2]), self.zoom)

@dataclass
class CombinerStyle:
    """Defines styling rules for `Combiner`-generated map images."""

    bg_color           : Color | None = None
    grid_line_color    : Color | None = None
    grid_line_size     : int   | None = None
    grid_text_color    : Color | None = None
    grid_coords_format : str          = ''

    def __post_init__(self) -> None:
        self.bg_color = self.bg_color or Color.from_name('clear')
        self.grid_line_color = self.grid_line_color or Color.from_name('black')
        self.grid_text_color = self.grid_text_color or Color.from_name('black')

    def __json__(self) -> dict[str, Any]:
        return asdict(self)

DEFAULT_COMBINER_STYLE = CombinerStyle()

class Combiner:
    """Takes a squaremap `tiles` directory path and can export stitched map images."""
    STANDARD_WORLDS: tuple[str, ...] = ('overworld', 'the_nether', 'the_end')
    def __init__(self,
            tiles_dir: str | Path,
            *,
            grid_step: int = SQMAP_TILE_AREA,
            style: CombinerStyle = DEFAULT_COMBINER_STYLE,
            confirm: Callable[[str], bool] | None = None,
            show_progress: bool = False,
        ) -> None:
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

        :param grid_step: The interval that should be used for things like drawing grid lines or coordinates onto the
            finished image. Will be treated as an interval of blocks, not pixels on the image.
        :param style: `CombinerStyle` instance to define styling rules with.
        :param confirm: A `Callable` to use in cases where any `Combiner` functions wish to ask for confirmation before
            continuing, which must return `True` to continue.
        :param show_progress: Whether to show a progress bar for any functions that support it.
        """
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir     = tiles_dir
        self.grid_step     = grid_step
        self.style         = style
        self.confirm       = confirm if confirm else lambda _: True
        self.show_progress = show_progress

        self.mapped_worlds: list[str] = [p.stem for p in tiles_dir.glob('minecraft_*/')]
        """What valid world folders the given `tiles_dir` contains."""

    # TODO: Replace grid functions with grid property and methods on it

    def draw_grid_lines(self, image: MapImage) -> None:
        """Draws grid lines onto a `MapImage` at the intervals defined for this `Combiner` instance.

        :param image: The `MapImage` to draw coordinates onto. Its `game_zero` attribute is used as the origin point.
        """
        draw = ImageDraw.Draw(image.img)
        grid_origin = image.game_zero
        coord_axes: dict[str, set[int]] = {
            'h': set(
                *range(grid_origin.x, image.width, self.grid_interval[0] // image.zoom),
                *range(grid_origin.x, 0, -self.grid_interval[0] // image.zoom),
            ),
            'v': set(
                *range(grid_origin.y, image.height, self.grid_interval[1] // image.zoom),
                *range(grid_origin.y, 0, -self.grid_interval[1] // image.zoom),
            ),
        }

        for x in coord_axes['h']:
            draw.line((x, 0, x, image.height), fill=self.style.grid_line_color.as_rgba())
        for y in coord_axes['v']:
            draw.line((0, y, image.width, y), fill=self.style.grid_line_color.as_rgba())

    def draw_grid_coords_text(self, image: MapImage) -> None:
        """
        Draws coordinate text onto a `MapImage` at every interval as defined for this `Combiner` instance.

        :param image: The `MapImage` to draw coordinates onto. Its `game_zero` attribute is used as the origin point.
        """
        # TODO: Not accessed. What was this used for?
        bbox_before_grid: Rectangle = Maybe(image.img.getbbox()).unwrap(ValueError(ErrMsg.BBOX_IS_NONE))

        grid_origin: MapImageCoord = image.game_zero

        coord_axes: dict[str, set[int]] = {
            'h': set(
                *range(grid_origin.x, image.width, self.grid_interval[0] // image.zoom),
                *range(grid_origin.x, -1, -self.grid_interval[0] // image.zoom),
                ),
            'v': set(
                *range(grid_origin.y, image.height, self.grid_interval[1] // image.zoom),
                *range(grid_origin.y, -1, -self.grid_interval[1] // image.zoom),
                ),
        }

        interval_coords: list[MapImageCoord] = [
            MapImageCoord(x, y) for x, y in product(coord_axes['h'], coord_axes['v'])
        ]
        total_intervals = len(interval_coords)

        if total_intervals > 50000:
            logger.warning('More than 50,000 grid intervals will be iterated over; this may take some time.')
            if not self.confirm('More than 50,000 grid intervals will be iterated over, which can take a very long time.' +
                ' Continue?'):
                logger.info('Skipping coordinates...')
                return
        elif total_intervals > 5000:
            logger.info('More than 5000 grid intervals will be iterated over;' +
                ' the progress bar\'s description text will not update per iteration in order to save speed.')

        logger.info('Drawing coordinates...')
        draw = ImageDraw.Draw(image.img)
        font = ImageFont.truetype(self.style.grid_text_font, size=self.style.grid_text_size)

        for img_coord in (pbar := tqdm(interval_coords, disable=not self.show_progress)):
            logger.log('GUI_COMMAND', f'/pbar set {pbar.n / total_intervals}')
            game_coord = img_coord.to_game_coord(image)
            coord_text = self.grid_coords_format.format(x=game_coord.x, y=game_coord.y)
            if self.show_progress and (total_intervals <= 5000):
                pbar.set_description(f'Drawing {coord_text} at {img_coord.as_tuple()}')
            draw.text(xy=img_coord.as_tuple(), text=str(coord_text), fill=self.style.grid_text_color.as_rgba(),
                font=font)
        logger.log('GUI_COMMAND', '/pbar hide')

    def combine(self,
            *,
            world: str | Path,
            detail: int,
            autotrim: bool = False,
            area: Rectangle | None = None,
            force_size: tuple[int, int] | None = None,
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

        :returns: Returns the created `MapImage` if successful, or `None` if the process failed or was cancelled at any
            point.
        :rtype: MapImage | None
        """
        if world not in self.mapped_worlds:
            raise ValueError(f'No world directory with name "{world}" exists at {self.tiles_dir}')
        if detail not in SQMAP_DETAIL_LEVELS:
            raise ValueError(f'Invalid detail level {detail}, expected one of:'
                + f' {', '.join(map(str, SQMAP_DETAIL_LEVELS.keys()))}')
        source_dir: Path = self.tiles_dir / world / str(detail)

        detail_mul = SQMAP_DETAIL[detail]

        # Sort out what regions we're going to stitch
        columns: set[int] = set()
        rows: set[int] = set()
        regions: dict[int, dict[int, Path]] = {}
        logger.info('Finding region images...')
        for img in tqdm(source_dir.glob('*_*.png'), disable=not self.show_progress):
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
            area_regions: Rectangle = tuple(
                n // self.TILE_SIZE \
                for n in snap_box(tuple(n // detail_mul for n in area), self.TILE_SIZE)
            )
            column_range = range(area_regions[0], area_regions[2] + 1)
            row_range = range(area_regions[1], area_regions[3] + 1)

        size_estimate = f'{self.TILE_SIZE * len(column_range)}x{self.TILE_SIZE * len(row_range)}'
        if not self.confirm(f'Estimated image size before trimming: {size_estimate}\nContinue?'):
            logger.info('Cancelling...')
            return None

        # Start stitching
        image = Image.new(
            mode='RGBA',
            size=(self.TILE_SIZE * len(column_range), self.TILE_SIZE * len(row_range)),
        )
        logger.info('Constructing image...')

        ta = time.perf_counter()
        # Represents where 0, 0 in our Minecraft world is, in relation to the image's coordinates
        game_zero_in_image: Coord2i | None = None
        regions_iter: list[tuple[int, int]] = list(product(column_range, row_range))
        for c, r in (pbar := tqdm(regions_iter, disable=not self.show_progress)):
            pbar.set_description(f'Region: {c}, {r}')
            logger.log('GUI_COMMAND', f'/pbar set {pbar.n / len(regions_iter)}')

            if (c not in regions) or (r not in regions[c]):
                continue

            # The pasting coordinates are determined based on what current column and row the for loops
            # are on, so they'll increase by a tile regardless of whether an image has actually been pasted
            tile_path = regions[c][r]
            if self.show_progress:
                tqdm.write(f'Pasting image: {tile_path}')

            x, y = self.TILE_SIZE * (c - min(column_range)), self.TILE_SIZE * (r - min(row_range))
            paste_area = Rectangle([x, y, x + self.TILE_SIZE, y + self.TILE_SIZE])
            if not game_zero_in_image:
                game_zero_in_image = Coord2i(x, y) - (Coord2i(c, r) * self.TILE_SIZE)
            image.paste((tile_img := Image.open(tile_path)), paste_area, mask=tile_img)

        logger.log('GUI_COMMAND', '/pbar hide')

        if not game_zero_in_image:
            raise CombineError(ErrMsg.GAME_ZERO_IS_NONE)
        image = MapImage(image, MapImageCoord(*game_zero_in_image), detail_mul)
        del game_zero_in_image

        # Crop if an area is specified
        if area:
            crop_area = (
                *GameCoord(area[0], area[1]).to_image_coord(image).as_tuple(),
                *GameCoord(area[2], area[3]).to_image_coord(image).as_tuple(),
            )
            image = image.crop(crop_area)
            autotrim = False

        # Things like grid lines and coordinate text are likely to end up drawn outside of the image's original bounding
        # box, altering what getbbox() would return. Get this bounding box *first*, and then use it to autotrim later.
        bbox: Rectangle = Maybe(image.img.getbbox()).unwrap(CombineError(ErrMsg.BBOX_IS_NONE))

        # Add grid and/or coordinates
        if all(n > 0 for n in self.grid_interval):
            if self.style.show_grid_text:
                self.draw_grid_coords_text(image)

            if self.style.show_grid_lines:
                logger.info('Drawing grid lines...')
                self.draw_grid_lines(image)

        # Crop and resize if given an explicit size
        if force_size and all(n > 0 for n in force_size):
            logger.info(f'Resizing to {force_size[0]}x{force_size[1]}...')
            image = image.resize_canvas(*force_size)
            autotrim = False

        # Trim transparent excess space
        if autotrim:
            logger.info(f'Trimming out blank space... ({image.width}x{image.height} ->'
                + f' {bbox[2] - bbox[0]}x{bbox[3] - bbox[1]})')
            image = image.crop(bbox)

        # Apply desired background color, if any
        if self.style.background_color != (0, 0, 0, 0):
            image_bg = Image.new('RGBA', size=image.size, color=self.style.background_color.to_rgba())
            image_bg.alpha_composite(image.img)
            image = MapImage(image_bg, image.game_zero, image.zoom)

        # Done.
        tb = time.perf_counter()
        logger.info(f'Image creation finished in {tb - ta:04f}s')

        return image
