"""
A basic CLI app for interacting with squaremap_combine.
"""

import re
import sys
from argparse import ArgumentParser
from argparse import HelpFormatter as BaseHelpFormatter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

from maybetype import Maybe
from PIL import Image
from rich.prompt import Confirm

from squaremap_combine.const import LOGS_DIR, console
from squaremap_combine.core import Combiner, CombinerStyle
from squaremap_combine.geo import Rect
from squaremap_combine.logging import LogLevel, enable_logging, logger
from squaremap_combine.util import Color


class HelpFormatter(BaseHelpFormatter):
    def _split_lines(self, text: str, width: int) -> list[str]:
        if '\n' in text:
            return re.sub(r"\n( +\^)", '\n', text).strip().splitlines()
        return super()._split_lines(text, width)

def abort(msg: str = 'Aborting.', *, code: int = 1) -> NoReturn:
    console.print(msg)
    raise SystemExit(code)

def arg_list(s: str, delim: str = ',') -> list[Any]:
    return [s.strip() for s in s.split(delim)]

def opt_rect(opt_name: str, delim: str = ',') -> Callable[[str], Rect]:
    def parse(s: str) -> Rect:
        coords: tuple[int, ...] = tuple(map(int, s.split(delim)))
        if len(coords) != 4:  # noqa: PLR2004
            abort(f'[err]Expected 4 integer values for option {opt_name}[/]')
        coords = cast(tuple[int, int, int, int], coords)
        return Rect(coords)
    return parse

def opt_crop(s: str, delim: str = ',') -> tuple[int, int] | Literal['auto'] | None:
    if delim in s:
        coords: tuple[int, ...] = tuple(map(int, s.split(delim)))
        if len(coords) != 2:  # noqa: PLR2004
            abort('[err]Expected 2 integer values for option -c/--crop[/]')
        return cast(tuple[int, int], coords)
    if s == 'auto':
        return 'auto'
    abort(f'[err]Expected 2 integers value or string "auto" for option -c/--crop: {s}[/]')

def opt_grid_lines(s: str) -> tuple[Color, int]:
    color_str, *size = s.split(' ')
    if len(size) > 1:
        abort(f'[err]Expected no more than 2 values for option --grid-lines: {s}[/]')
    size = Maybe(size).get(0, str).then(int) or 1
    color: Color = Color.from_str(color_str)
    return color, size

def opt_grid_font(s: str) -> tuple[str, int, Color]:
    split: list[str] = [sub.strip() for sub in s.split(',')]
    if not split:
        abort('[err]Expected at least 1 value for option --grid-font[/]')
    if len(split) > 3:  # noqa: PLR2004
        abort(f'[err]Expected no more than 3 values for option --grid-font: {s}[/]')
    font: str = split[0]
    font_pt: int = Maybe(split).get(1, str).then(int) or 32
    font_color: Color = Maybe(split).get(2, str).then(Color.from_str) or Color.from_name('white')
    return font, font_pt, font_color

def main() -> int:
    parser = ArgumentParser(formatter_class=HelpFormatter)
    parser.add_argument('action', type=str, choices=['run', 'logs'])

    parser.add_argument('--world', '-i', type=Path,
        help='Path to a world folder subdirectory under squaremap\'s "tiles" directory.'
            + ' e.g. <SERVER>/plugins/squaremap/web/tiles/minecraft_overworld')
    parser.add_argument('--zoom', '-z', type=int, choices=[0, 1, 2, 3], default=3,
        help='The zoom/detail level to use, from 0 (lowest detail) to 3 (highest detail).'
            + """
            ^    3 - 1 block per pixel
            ^    2 - 2x2 blocks per pixel
            ^    1 - 4x4 blocks per pixel
            ^    0 - 8x8 blocks per pixel
            """)

    parser.add_argument('--out', '-o', type=Path, default=Path('./world.png'),
        help='Where to save the resulting image. File format can be any that are supported by Pillow.')

    parser.add_argument('--overwrite', action='store_true',
        help='Allows the script to overwrite an existing file with the same target name if it already exists. By'
        + ' default, if an image with the same path already exists, a numbered suffix is added.')

    parser.add_argument('--rect', '-r', type=opt_rect('-r/--rect'),
        help='A rectangle area of the world to export an image of, separated by commas. Defaults to the full map.')

    parser.add_argument('--crop', '-c', type=opt_crop,
        help='Integer list(2) OR `auto`|`False`|A size in pixels to crop the final image to. If "auto", trims empty'
        + ' (fully transparent) space surrounding the completed image.')

    parser.add_argument('--grid', '-g', type=int, default=0,
        help='Defines the grid interval in blocks. Required to use any `--grid-*` options.')

    parser.add_argument('--grid-lines', type=opt_grid_lines, default='black 1',
        help='The color and thickness in pixels to use for grid lines, separated by space.')

    parser.add_argument('--grid-coords', type=str,
        help='The string format to use for overlaying grid coordinates, replacing `{x}` and `{z}` with the respective'
        + ' coordinate values, e.g. `"X: {x}, Z: {z}"`. By default, coordinates are not added to the image at all.'
        + ' Note that drawing coordinate text will make creating the image significantly slower, especially with large'
        + ' grids and/or small grid steps.')

    parser.add_argument('--grid-font', type=opt_grid_font,
        help='The file path to a font to use for grid coordinate text, as well as the "point" size to use,'
        + ' separated by comma. If left blank (default), Fira Code SemiBold, which is included in squaremap_combine\'s'
        + ' installation directory, is used at 32pt in white. Example values include: \'myfont.ttf, 64, white\', '
        + ' \'/usr/share/fonts/ubuntu/Ubuntu-B.ttf, 32, red\', \'C:\\Windows\\Fonts\\arial.ttf, 48, #ff00ff\'')

    parser.add_argument('--log-level', '-l', type=lambda s: LogLevel(s.upper()), default=LogLevel.INFO,
        help='Sets the logging level for this run.')

    args = parser.parse_args()
    action: Literal['run', 'logs'] = args.action

    if action == 'logs':
        console.print(f'{LOGS_DIR}')
        return 0

    log_level: LogLevel = args.log_level

    enable_logging(log_level.value)

    # Parse combine args
    world_dir: Path = Maybe(args.world).unwrap(lambda: abort('[err]Option -i/--world is required[/]')).absolute()
    zoom: Literal[0, 1, 2, 3] = Maybe(args.zoom).unwrap(lambda: abort('[err]Option -z/--zoom is required[/]'))
    dest: Path = args.out.absolute()

    overwrite   : bool                                     = args.overwrite
    area        : Rect | None                              = args.rect
    crop        : tuple[int, int] | Literal['auto'] | None = args.crop
    grid_step   : int                                      = args.grid
    grid_lines  : tuple[Color, int]                        = args.grid_lines
    grid_coords : str                                      = args.grid_coords
    grid_font   : tuple[str, int, Color]                   = args.grid_font

    if not world_dir.is_dir():
        raise NotADirectoryError(f'Not a directory or does not exist: {world_dir}')
    if not (world_dir / str(zoom)).is_dir():
        raise NotADirectoryError(f'Found no directory for zoom level {zoom} under: {world_dir}')

    style: CombinerStyle = CombinerStyle(
        grid_line_color     = Maybe(grid_lines).get(0, Color, default=None).val,
        grid_line_size      = Maybe(grid_lines).get(1, int, default=None).val,
        grid_text_font      = Maybe(grid_font).get(0, str, default=None).val,
        grid_text_pt        = Maybe(grid_font).get(1, int, default=None).val,
        grid_text_fill_color= Maybe(grid_font).get(2, Color, default=None).val,
        grid_coords_format  = grid_coords,
    )

    combiner: Combiner = Combiner(
        world_dir.parent,
        grid_step=grid_step,
        style=style,
        confirm_fn=lambda message: Confirm.ask(message),
        progress_bar=True,
    )

    logger.info('Starting...')
    image: Image.Image = combiner.combine(
        world_dir,
        zoom=zoom,
        area=area,
        crop=crop,
    )

    if (not overwrite) and dest.is_file():
        logger.info('Output file already exists and --overwrite flag was not used, appending number suffix')
        highest: int = max([
            int(re.search(r"\.(\d+)$", fp.stem).groups()[0]) \
            for fp in Path(dest.parent).glob(f'*{dest.suffix}') if re.search(r"\.(\d+)$", fp.stem)
        ] or [0])
        dest = dest.with_stem(f'{dest.stem}.{highest + 1}')
    logger.info(f'Saving to: {dest}')
    try:
        image.save(dest)
    except OSError as e:
        if 'cannot write mode RGBA' in str(e):
            image = image.convert('RGB')
            image.save(dest)
        else:
            raise

    return 0

if __name__ == '__main__':
    sys.exit(main())
