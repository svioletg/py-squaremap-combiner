from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

from maybetype import Maybe
from PIL import Image, ImageDraw, ImageFont

from squaremap_combine.const import (
    DEFAULT_FONT_PATH,
    IMAGE_SIZE_WARN_THRESH,
    SQMAP_TILE_BLOCKS,
    SQMAP_TILE_NAME_REGEX,
    SQMAP_TILE_SIZE,
    SQMAP_ZOOM_BPP,
)
from squaremap_combine.errors import CombineError
from squaremap_combine.geo import Coord2i, Grid, Rect
from squaremap_combine.logging import logger
from squaremap_combine.util import Color


@dataclass
class CombinerStyle:
    """Defines styling rules for :py:class:`~squaremap_combine.core.Combiner`-generated map images."""
    bg_color: Color
    grid_line_color: Color
    grid_line_size: int
    grid_text_font: str | Path
    grid_text_pt: int
    grid_text_stroke_size: int
    grid_text_stroke_color: Color
    grid_text_fill_color: Color
    grid_coords_format: str

    def __init__(self,
            bg_color: Color | str | None = None,
            grid_line_color: Color | str | None = None,
            grid_line_size: int = 1,
            grid_text_font: str | Path = DEFAULT_FONT_PATH,
            grid_text_pt: int = 32,
            grid_text_stroke_size: int | None = None,
            grid_text_stroke_color: Color | str | None = None,
            grid_text_fill_color: Color | str | None = None,
            grid_coords_format: str = '',
        ) -> None:
        """
        :param bg_color: Background color to use for empty areas of the map.
            Default: ``#00000000`` (clear)
        :param grid_line_color: Color for grid overlay lines.
            Default: ``#000000ff`` (black)
        :param grid_line_size: Thickness of grid overlay lines.
        :param grid_text_font: Font to use for grid overlay coordinate text.
            Default: Fira Code (included with package)
        :param grid_text_pt: Point size to use for grid overlay coordinate text.
        :param grid_text_stroke_size: Stroke (outline) size to use for grid overlay coordinate text.
            Default: 20% (rounded down) of ``grid_text_pt``
        :param grid_text_stroke_color: Stroke (outline) color to use for grid overlay coordinate text.
            Default: ``#000000ff`` (black)
        :param grid_text_fill_color: Color to use for grid overlay coordinate text.
            Default: ``#ffffffff`` (white)
        :param grid_coords_format: String to use for coordinate text, which expects `{x}` and `{y}` specifiers to
            format.
        """
        self.bg_color = self._parse_color_arg(bg_color or 'clear')
        self.grid_line_color = self._parse_color_arg(grid_line_color or 'black')
        self.grid_line_size = grid_line_size
        self.grid_text_font = grid_text_font
        self.grid_text_pt = grid_text_pt
        self.grid_text_stroke_size = Maybe(grid_text_stroke_size).this_or(int(grid_text_pt * 0.2)).unwrap()
        self.grid_text_stroke_color = self._parse_color_arg(grid_text_stroke_color or 'black')
        self.grid_text_fill_color = self._parse_color_arg(grid_text_fill_color or 'white')
        self.grid_coords_format = grid_coords_format

        super().__init__()

    def __json__(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def _parse_color_arg(val: Color | str) -> Color:
        if isinstance(val, str):
            return Color.from_hex(val) if val.startswith('#') else Color.from_name(val)
        return val

DEFAULT_COMBINER_STYLE = CombinerStyle()

class Combiner:
    """Takes a squaremap ``tiles`` directory path and can export stitched map images."""

    tiles_dir: Path
    """The squaremap ``tiles`` directory to source tile images from."""
    grid_step: int
    """Interval of blocks to use for the grid overlay. Grid overlay is disabled if set to 0."""
    style: CombinerStyle
    confirm_fn: Callable[[str], bool]
    progress_bar: bool

    def __init__(self,
            tiles_dir: str | Path,
            *,
            grid_step: int | None = None,
            style: CombinerStyle = DEFAULT_COMBINER_STYLE,
            confirm_fn: Callable[[str], bool] | None = None,
            progress_bar: bool = False,
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
        :param style: :py:class:`~squaremap_combine.core.CombinerStyle` instance to define styling rules with.
        :param confirm_fn: A ``Callable`` to use in cases where any ``Combiner`` functions wish to ask for confirmation
            before continuing, which must return ``True`` to continue.
        :param progress_bar: Whether to show a progress bar for any functions that support it.
        """
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir     = tiles_dir
        self.grid_step     = grid_step or 0
        self.style         = style
        self.confirm       = confirm_fn if confirm_fn else lambda _: True
        self.progress_bar  = progress_bar

    def __repr__(self) -> str:
        return f'Combiner(tiles_dir={self.tiles_dir!r}, grid_step={self.grid_step!r})'

    @property
    def worlds(self) -> list[str]:
        return [p.stem for p in self.tiles_dir.glob('minecraft_*/')]

    @staticmethod
    def _draw_grid_overlay(
            map_img: Image.Image,
            world_grid: Grid,
            canvas_grid: Grid,
            style: CombinerStyle,
            progress_interval_secs: float,
        ) -> None:
        if world_grid.step:
            logger.info(f'Grid step: {world_grid.step}; {world_grid.steps_count} total steps to iterate')
            logger.info('Drawing grid overlay... 0%')
            draw = ImageDraw.Draw(map_img)
            font = ImageFont.truetype(style.grid_text_font, size=style.grid_text_pt)

            progress_update_timer: float = perf_counter()
            total: int = world_grid.steps_count

            ta: float = perf_counter()
            for n, world_coord in enumerate(world_grid.iter_steps()):
                if (progress_interval_secs > 0) \
                    and ((perf_counter() - progress_update_timer) >= progress_interval_secs):
                    progress_update_timer = perf_counter()
                    progress_perc: float = (n / total) * 100
                    logger.info(f'Drawing grid overlay... {progress_perc:.1f}%')

                canvas_coord: Coord2i = world_grid.project(world_coord, canvas_grid)

                # Draw grid lines
                if style.grid_line_color.alpha > 0:
                    draw.line(
                        (canvas_coord.x, 0, canvas_coord.x, map_img.height),
                        width=style.grid_line_size,
                        fill=style.grid_line_color.as_rgba(),
                    )
                    draw.line(
                        (0, canvas_coord.y, map_img.width, canvas_coord.y),
                        width=style.grid_line_size,
                        fill=style.grid_line_color.as_rgba(),
                    )
                # Draw coordinate text
                if style.grid_coords_format:
                    draw.text(
                        canvas_coord.as_tuple(),
                        style.grid_coords_format.format(x=world_coord.x, y=world_coord.y),
                        font=font,
                        fill=style.grid_text_fill_color.as_rgba(),
                        stroke_width=style.grid_text_stroke_size,
                        stroke_fill=style.grid_text_stroke_color.as_rgba(),
                    )
            tb: float = perf_counter()

            logger.info('Drawing grid overlay... 100%')
            logger.info(f'Finished drawing grid in {tb - ta:.04f}s')
            del ta, tb

    def combine(self,
            world: str | Path,
            *,
            zoom: int,
            area: Rect | tuple[int, int, int, int] | None = None,
            crop: tuple[int, int] | Literal['auto'] | None = None,
            tile_ext: str = '*',
            grid_step: int | None = None,
            style: CombinerStyle | dict[str, Any] | None = None,
            grid_progress_interval_secs: float = 1.0,
            draw_grid_fn: Callable[[Image.Image, Grid, Grid, CombinerStyle, float], None] = _draw_grid_overlay,
        ) -> Image.Image:
        """Combine the given world (dimension) tile images into one large map.

        :param world: Name of the world to use the tiles of, as a subdirectory of the instance's ``tiles_dir``
            attribute. Alternatively, if given as a ``Path`` object, the path will be used as-is and will ignore
            ``tiles_dir`` for this run.
        :param zoom: The zoom level to use, from 0 (lowest detail, 8x8 blocks per pixel) to 3 (highest detail 1 block
            per pixel).
        :param area: Specifies an area of the world to export. If ``None``, all tiles available are used.
        :param crop: A size to crop the final image to, centering on the center of ``area``; or, ``'auto'`` can
            be given to trim excess empty space around the map's borders, and crop it to the resulting visible area. In
            this case, the image is no longer guaranteed to be centered on ``area``.

            .. note::
                Only tiles within ``area`` will be used, regardless of this value—if ``crop`` is larger than the
                rendered area (and by extension, not ``'auto'``), blank space will be left surrounding the map.
        :param tile_ext: The file extension used for the tile images. By default, ``combine()`` will attempt to use
            all existing files under the relevant tiles directory that have any file suffix, and are not directories.
        :param grid_step: A grid step value to use instead of the ``Combiner`` instance's ``.step`` value,
            if not ``None``.
        :param style: A :py:class:`~squaremap_combine.core.CombinerStyle` instance to use instead of the ``Combiner``
            instance's ``style`` instance, if not ``None``. Can also be a ``dict`` of key-value pairs, in which case
            only the specified keys' values are overridden, and the ``Combiner`` instance's ``style`` is use as a
            fallback.
        :param grid_progress_interval_secs: At what interval to log grid overlay drawing updates. Set to ``0`` or lower
            to disable.
        :param draw_grid_fn: A function to call which will handle drawing the grid overlay on top of the map image
            being created. Will receive these arguments:
            - :py:class:`PIL.Image.Image`: The map image object to be drawn onto.
            - :py:class:`~squaremap_combine.geo.Grid`: The "world grid", representing the coordinates of the Minecraft
                world.
            - :py:class:`~squaremap_combine.geo.Grid`: The "canvas grid" for the image, a rectangle of ``0, 0`` to the
                size of the image.
            - :py:class:`~squaremap_combine.core.CombinerStyle`: The style object to use, that being this ``Combiner``
                instance's ``.style`` attribute after being updated with or replaced by the ``style`` parameter of the
                ``combine`` method.
            - ``float``: In the default drawing function
                (:py:meth:`~squaremap_combine.core.Combiner._draw_grid_overlay`), this is used as an interval of
                seconds at which to log updates on the drawing progress.

        :returns image: The final stitched image, a :py:class:`PIL.Image.Image` object.

        :raises NotADirectoryError: Raised if ``world`` is not a directory or does not exist.
        """
        if not isinstance(world, Path):
            world = self.tiles_dir / world
        if not world.is_dir():
            raise NotADirectoryError(f'Not a directory or does not exist: {world}')

        logger.info(f'Using zoom level {zoom} ({SQMAP_ZOOM_BPP[zoom]} block(s) per pixel)')

        if not area:
            logger.info('No area specified, using full map')

        grid_step = grid_step if grid_step is not None else self.grid_step

        if isinstance(style, dict):
            style = CombinerStyle(**(asdict(self.style) | style))
        style = style or self.style

        area = Maybe(area).then(Rect)
        zoom_bpp: int = SQMAP_ZOOM_BPP[zoom]

        logger.info(f'Using directory: {world.absolute() / str(zoom)}')
        logger.info('Looking for tiles...')

        combine_time_start: float = perf_counter()

        # Gather tile images, mapped to coordinates
        tiles: dict[Coord2i, Path] = {
            Coord2i(*map(int, SQMAP_TILE_NAME_REGEX.findall(fp.stem)[0])):fp \
            for fp in (world / str(zoom)).glob(f'*.{tile_ext}') if fp.is_file()
        }
        if not tiles:
            raise CombineError(f'No images found for: {world / str(zoom)}/*.{tile_ext}')
        logger.info(f'Found {len(tiles)} tile images')

        # Grid of tile coordinates
        tile_grid: Grid = Grid(area.map(lambda n: n // (SQMAP_TILE_BLOCKS * zoom_bpp)), step=1) if area \
            else Grid.from_steps(tiles.keys(), step=1)

        if tile_grid.rect.size == (0, 0):
            tile_grid.rect.x2 += 1
            tile_grid.rect.y2 += 1

        # Grid representing the Minecraft world
        world_grid: Grid = tile_grid \
            .map(lambda n: n * (SQMAP_TILE_BLOCKS * zoom_bpp)) \
            .resize(SQMAP_TILE_BLOCKS * zoom_bpp) \
            .copy(step=grid_step)

        # Grid representing the actual image, shifted so that the top-left corner is 0, 0
        canvas_grid: Grid = tile_grid \
            .translate_to((0, 0)) \
            .map(lambda n: n * SQMAP_TILE_SIZE) \
            .resize(SQMAP_TILE_SIZE) \
            .copy(step=SQMAP_TILE_SIZE) \

        # Since the region coordinates refer to the top left of each region, one more tile's worth of space needs to be
        # added to the map image so it doesn't get cut off

        map_img: Image.Image = Image.new(
            'RGBA',
            canvas_grid.rect.size,
            color=style.bg_color.as_rgba(),
        )

        if any(n >= IMAGE_SIZE_WARN_THRESH for n in map_img.size):
            logger.warning(f'Image dimensions exceed warning threshold of {IMAGE_SIZE_WARN_THRESH}: {map_img.size!r}')

        # Assemble image
        for region, img_coord in zip(
                tile_grid.iter_steps(),
                # Resize canvas grid down so the coordinates correlate correctly
                canvas_grid.resize(-SQMAP_TILE_SIZE).iter_steps(),
                strict=True,
            ):
            if not (tile_path := tiles.get(region)):
                continue
            logger.info(f'Tile {region}: {tile_path}')
            logger.debug(f'Placing tile {region} at image coordinate {img_coord}')
            tile: Image.Image = Image.open(tile_path)
            map_img.alpha_composite(tile, img_coord.as_tuple())

        # Draw grid overlay
        draw_grid_fn(
            map_img,
            world_grid,
            canvas_grid,
            style,
            grid_progress_interval_secs,
        )

        # Crop to world area if specified
        if area:
            logger.info('Cropping to specified world area...')
            offset: tuple[Coord2i, Coord2i] = (
                (area.corners[0] - world_grid.rect.corners[0]) // zoom_bpp,
                (area.corners[-1] - world_grid.rect.corners[-1]) // zoom_bpp,
            )
            map_img = map_img.crop(
                (*(canvas_grid.rect.corners[0] + offset[0]), *(canvas_grid.rect.corners[-1] + offset[1])), # type: ignore
            )

        # Crop to physical size if specified
        if crop:
            if not map_img.getbbox() and (crop == 'auto'):
                logger.warning('Crop set to "auto" but the image is blank, leaving it at its previous size')
            else:
                crop_box: tuple[int, int, int, int] = Maybe(map_img.getbbox()).unwrap() \
                    if crop == 'auto' \
                    else Rect.from_size(crop, center=Coord2i(map_img.size) // 2).as_tuple()
                logger.info(f'Cropping image to {Rect(crop_box).size}...')
                map_img = map_img.crop(crop_box)

        combine_time_end: float = perf_counter()

        logger.info(
            f'Image creation finished in {combine_time_end - combine_time_start:.4f}, final size is {map_img.size}',
        )
        return map_img
