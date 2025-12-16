from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from squaremap_combine.const import IMAGE_SIZE_WARN_THRESH, SQMAP_TILE_NAME_REGEX, SQMAP_TILE_SIZE, SQMAP_ZOOM_BPP
from squaremap_combine.logging import logger
from squaremap_combine.util import Color, Coord2i, Grid, Rect


class GameCoord(Coord2i):
    """
    A coordinate as relative to a Minecraft world.
    Largely identical to :py:class:`~squaremap_combine.util.Coord2i`, but used mainly for typing to more effectively
    signal what kind of coordinate is expected for a given class or function.
    """
    def __repr__(self) -> str:
        return f'GameCoord(x={self.x}, y={self.y})'

    def to_image_coord(self, image: 'MapImage') -> Coord2i:
        """
        Converts this Minecraft coordinate to its position on the given :py:class:`~squaremap_combine.core.MapImage`.
        """
        return image.game_zero + (self // image.zoom)

class MapImageCoord(Coord2i):
    """
    A coordinate as relative to a :py:class:`~squaremap_combine.core.MapImage`.
    Largely identical to :py:class:`~squaremap_combine.util.Coord2i`, but used mainly for typing to more effectively
    signal what kind of coordinate is expected for a given class or function.
    """
    def __repr__(self) -> str:
        return f'MapImageCoord(x={self.x}, y={self.y})'

    def to_game_coord(self, image: 'MapImage') -> Coord2i:
        """Converts this image coordinate to its position in the Minecraft world it represents."""
        return (self - image.game_zero) * image.zoom

class MapImage:
    """
    A class to wrap :py:class:`~PIL.Image.Image` with Minecraft-map-specific functionality, like automatically
    recalculating the world's ``0, 0`` position in the image upon any crops or other changes.
    """
    def __init__(self, image: Image.Image, game_zero: 'MapImageCoord | Coord2i', *, zoom: int) -> None:
        """
        :param image: The ``Image`` to wrap.
        :param game_zero: At what coordinate in this image ``0, 0`` would be located in the Minecraft world it
            represents.
        :param zoom: The squaremap zoom/detail number for this map.
        """
        self.img = image
        self.game_zero = MapImageCoord(game_zero)
        self.zoom = zoom

    def __repr__(self) -> str:
        return f'MapImage(img={self.img!r}, game_zero={self.game_zero!r}, zoom={self.zoom!r})'

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
        """Returns a copy of this ``MapImage`` with only the internal ``Image`` object changed."""
        return MapImage(new_image, self.game_zero, zoom=self.zoom)

    def crop(self, box: tuple[int, int, int, int]) -> 'MapImage':
        """Returns a cropped portion of the original image with an accordingly updated ``game_zero`` attribute."""
        return MapImage(self.img.crop(box), MapImageCoord(*self.game_zero - box[0:2]), zoom=self.zoom)

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
        return MapImage(new_canvas, MapImageCoord(*self.game_zero + paste_area[0:2]), zoom=self.zoom)

@dataclass
class CombinerStyle:
    """Defines styling rules for :py:class:`~squaremap_combine.core.Combiner`-generated map images."""

    bg_color           : Color | None = None
    grid_line_color    : Color | None = None
    grid_line_size     : int   | None = None
    grid_text_color    : Color | None = None
    grid_coords_format : str   | None = None

    def __post_init__(self) -> None:
        self.bg_color = self.bg_color or Color.from_name('clear')
        self.grid_line_color = self.grid_line_color or Color.from_name('black')
        self.grid_text_color = self.grid_text_color or Color.from_name('black')

    def __json__(self) -> dict[str, Any]:
        return asdict(self)

DEFAULT_COMBINER_STYLE = CombinerStyle()

class Combiner:
    """Takes a squaremap ``tiles`` directory path and can export stitched map images."""

    tiles_dir: Path
    """The squaremap ``tiles`` directory to source tile images from."""
    grid_step: int | None
    """Interval of blocks to use for the grid overlay. Grid overlay is disabled if set to ``None`` or 0."""
    style: CombinerStyle
    confirm_fn: Callable[[str], bool]
    show_progress: bool

    def __init__(self,
            tiles_dir: str | Path,
            *,
            grid_step: int | None = None,
            style: CombinerStyle = DEFAULT_COMBINER_STYLE,
            confirm_fn: Callable[[str], bool] | None = None,
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
        :param style: :py:class:`~squaremap_combine.core.CombinerStyle` instance to define styling rules with.
        :param confirm_fn: A ``Callable`` to use in cases where any ``Combiner`` functions wish to ask for confirmation
            before continuing, which must return ``True`` to continue.
        :param show_progress: Whether to show a progress bar for any functions that support it.
        """
        if not (tiles_dir := Path(tiles_dir)).is_dir():
            raise NotADirectoryError(f'Not a directory: {tiles_dir}')
        self.tiles_dir     = tiles_dir
        self.grid_step     = grid_step
        self.style         = style
        self.confirm       = confirm_fn if confirm_fn else lambda _: True
        self.show_progress = show_progress

    def __repr__(self) -> str:
        return f'Combiner(tiles_dir={self.tiles_dir!r}, grid_step={self.grid_step!r})'

    @property
    def worlds(self) -> list[str]:
        return [p.stem for p in self.tiles_dir.glob('minecraft_*/')]

    def combine(self,
            world: str | Path,
            *,
            zoom: int,
            area: Rect | None = None,
            crop: tuple[int, int] | Literal['auto'] | None = None,
            tile_ext: str = '*',
        ) -> MapImage:
        """Combine the given world (dimension) tile images into one large map.

        :param world: Name of the world to use the tiles of, as a subdirectory of the instance's ``tiles_dir`` attribute.
            Alternatively, if given as a ``Path`` object, the path will be used as-is and will ignore ``tiles_dir`` for
            this run.
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

        :returns image: The final stitched image as a :py:class:`~squaremap_combine.core.MapImage`.

        :raises NotADirectoryError: Raised if ``world`` is not a directory or does not exist.
        """
        if not isinstance(world, Path):
            world = self.tiles_dir / world
        if not world.is_dir():
            raise NotADirectoryError(f'Not a directory or does not exist: {world}')

        logger.info(f'Using directory: {world.absolute() / str(zoom)}')
        logger.info('Looking for tiles...')

        tiles: dict[Coord2i, Path] = {
            Coord2i(*map(int, SQMAP_TILE_NAME_REGEX.findall(fp.stem)[0])):fp \
            for fp in (world / str(zoom)).glob(f'*.{tile_ext}') if fp.is_file()
        }
        # TODO: What happens when no tiles are found?
        logger.info(f'Found {len(tiles)} tile images')

        zoom_bpp: int = SQMAP_ZOOM_BPP[zoom]
        region_grid: Grid = Grid(area.map(lambda n: n // (512 * zoom_bpp)), step=1) if area \
            else Grid.from_steps(tiles.keys(), step=1)

        area = area or region_grid.rect.map(lambda n: n * (512 * zoom_bpp))
        area_image_size: tuple[int, int] = region_grid.rect \
            .translate_to_zero() \
            .map(lambda n: n * SQMAP_TILE_SIZE) \
            .resize(SQMAP_TILE_SIZE) \
            .size
        # Since the region coordinates refer to the top left of each region, one more tile's worth of space needs to be
        # added to the map image so it doesn't get cut off

        img: Image.Image = Image.new(
            'RGBA',
            (crop if isinstance(crop, tuple) else area_image_size),
            color=self.style.bg_color.as_rgba(),
        )

        if any(n >= IMAGE_SIZE_WARN_THRESH for n in img.size):
            logger.warning(f'Image dimensions exceed warning threshold of {IMAGE_SIZE_WARN_THRESH}: {img.size!r}')

        for coord in map(Coord2i, region_grid.iter_steps()):
            if not (tile_path := tiles.get(coord)):
                continue
            tile: Image.Image = Image.open(tile_path)

        raise NotImplementedError

        # rendered_world: Grid = Grid(
        #     Rect(*region_grid.rect.map(lambda n: (n * SQMAP_TILE_BLOCKS) * SQMAP_ZOOM_BPP[zoom])),
        #     step=self.grid_step or SQMAP_TILE_BLOCKS,
        # )
