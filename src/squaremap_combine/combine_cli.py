"""
A basic CLI app for interacting with squaremap_combine.
"""

import argparse
import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from squaremap_combine.combine_core import (DEFAULT_COORDS_FORMAT, DEFAULT_OUTFILE_FORMAT,
                                            DEFAULT_TIME_FORMAT, Combiner, CombinerStyle, logger)
from squaremap_combine.helper import confirm_yn, filled_tuple
from squaremap_combine.logging import enable_logging
from squaremap_combine.project import LOGS_DIR, PROJECT_VERSION
from squaremap_combine.type_alias import Rectangle


def opt(*names: str) -> list[str]:
    """Short for "option". Returns the given argument names with underscore versions appended."""
    return [*names] + [('--' + n.lstrip('-').replace('-', '_')) for n in names if '-' in n.lstrip('-')]

def main(): # pylint: disable=missing-function-docstring
    stdout_handler, file_handler = enable_logging(logger) # pylint: disable=unused-variable

    if '--find-logs' in sys.argv:
        print(LOGS_DIR)
        return

    logger.info(f'squaremap_combine v{PROJECT_VERSION}')

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

    parser.add_argument(*opt('--grid-interval'), '-g', type=int, nargs='+', default=[0], metavar=('X_INTERVAL, Y_INTERVAL'),
        help='Defines the interval to be used for any grid-based options.\n' +
        'Providing only X_INTERVAL will use the same value for both X and Y intervals.')

    parser.add_argument(*opt('--coords-format'), '-gcf', type=str, metavar='FORMAT_STRING', default=DEFAULT_COORDS_FORMAT,
        help='A string to format how grid coordinates appear. Use "{x}" and "{y}" (curly-braces included)' +
        ' where you want the X and Y coordinates to appear, e.g. "X: {x} Y: {y}" could appear as "X: 100 Y: 200".')

    parser.add_argument(*opt('--style-file'), '-sf', type=Path, default=None, metavar=('JSON_FILEPATH'),
        help='A set of styling rules for the combiner, in the form of a path to a JSON file.\n' +
        'The values set in this JSON file will override that of the default styling settings, and can then be overridden themselves' +
        ' by any values present in the JSON given for the --style-override argument, if it is present.')

    parser.add_argument(*opt('--style-override'), '-so', type=str, default=None, metavar=('JSON_STRING'),
        help='A set of styling rules for the combiner, in the form of a JSON-formatted string.\n' +
        'These values take highest priority on overriding the already set rules.')

    parser.add_argument(*opt('--yes-to-all'), '-y', action='store_true',
        help='Automatically accepts any requests for user confirmation.')

    parser.add_argument(*opt('--find-logs'), action='store_true',
        help='Prints the path to where logs are being kept, and exits the script.')

    args = parser.parse_args()

    tiles_dir   : Path = args.tiles_dir
    world       : str  = args.world
    detail      : int  = args.detail
    output_dir  : Path = args.output_dir
    output_ext  : str  = args.output_ext
    time_format : str
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

    if len(args.grid_interval) > 2:
        raise ValueError('--use-grid argument can only take up to 2 integers')
    grid_interval: tuple[int, int] = filled_tuple(args.grid_interval)
    coords_format: str = args.coords_format

    style_file: Path | None = args.style_file
    if style_file and (not style_file.is_file()):
        raise ValueError(f'--style-file: No file could be found at path {style_file}')
    style_string: str | None = args.style_override
    if style_string and (not style_string.startswith('{')):
        raise ValueError(f'--style-override: Not a valid JSON string: {style_string}')
    elif style_string:
        style_string = style_string.replace("'", '"')

    yes_to_all: bool = args.yes_to_all

    find_logs: bool = args.find_logs

    if find_logs:
        print(LOGS_DIR)
        return

    #endregion ARGUMENTS
    logger.info(textwrap.dedent(f"""
        -- BASIC SETTINGS --
        Tiles directory: {tiles_dir}
        World: {world}
        Detail level: {detail}
        Output directory: {output_dir.absolute()}
        Output file extension: {output_ext}
        Grid interval: {grid_interval}
        Specified area: {area if area else 'None, will render the entire map'}

        -- ADDITIONAL OPTIONS --
        Add timestamp? {f'True, using format "{time_format}"' if time_format else 'False'}
        Allow overwriting images? {overwrite}
        Auto-trim? {autotrim}
        Force final size? {('True; ' + str(force_size)) if any(n > 0 for n in force_size) else 'False'}
        Skip confirmation prompts? {yes_to_all}
        Use a styling JSON file? {f'True, at {style_file}' if style_file else 'False'}
        Use a styling JSON string? {bool(style_file)}
    """))

    logger.debug(f'Style JSON filepath: {style_file}')
    logger.debug(f'Style JSON string: {style_string}')

    if not confirm_yn('Continue with these parameters?', yes_to_all):
        logger.info('Cancelling...')
        return None

    if world in Combiner.STANDARD_WORLDS:
        world = 'minecraft_' + world

    timestamp = (datetime.strftime(datetime.now(), time_format) + '_') if time_format else ''

    out_file: Path = output_dir / DEFAULT_OUTFILE_FORMAT.format(
        timestamp=timestamp,
        world=world,
        detail=detail,
        output_ext=output_ext
    )

    if out_file.exists() and (not overwrite):
        copies = [*output_dir.glob(f'{out_file.stem}*')]
        out_file = Path(out_file.stem + f'_{len(copies)}.' + output_ext)

    user_style_rules = {}

    if style_file:
        with open(style_file, 'r', encoding='utf-8') as f:
            user_style_rules.update(json.load(f))

    if style_string:
        user_style_rules.update(json.loads(style_string))

    combiner = Combiner(
        tiles_dir,
        use_tqdm=True,
        skip_confirmation=yes_to_all,
        grid_interval=grid_interval,
        grid_coords_format=coords_format,
        style=CombinerStyle(**user_style_rules)
    )

    image = combiner.combine(
        world,
        detail,
        autotrim=autotrim,
        area=area,
        force_size=force_size
    )

    if not image:
        logger.info('No image was created. Exiting...')
        return None

    logger.info(f'Saving to "{out_file}"...')
    image.save(out_file)

    logger.info('Done!')
