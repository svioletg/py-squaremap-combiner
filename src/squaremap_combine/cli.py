"""
A basic CLI app for interacting with squaremap_combine.
"""

import re
import sys
from argparse import ArgumentParser
from argparse import HelpFormatter as BaseHelpFormatter
from pathlib import Path
from typing import Literal, NoReturn

from maybetype import Maybe
from PIL import Image
from rich.prompt import Confirm

from squaremap_combine.const import LOGS_DIR, console
from squaremap_combine.core import Combiner, CombinerStyle
from squaremap_combine.logging import LogLevel, enable_logging, logger


class HelpFormatter(BaseHelpFormatter):
    def _split_lines(self, text: str, width: int) -> list[str]:
        if '\n' in text:
            return re.sub(r"\n( +\^)", '\n', text).strip().splitlines()
        return super()._split_lines(text, width)

def abort(msg: str = 'Aborting.', *, code: int = 1) -> NoReturn:
    console.print(msg)
    raise SystemExit(code)

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
    parser.add_argument('--log-level', '-L', type=lambda s: LogLevel(s.upper()), default=LogLevel.INFO,
        help='Sets the logging level for this run.')

    args = parser.parse_args()
    action: Literal['run', 'logs'] = args.action

    if action == 'logs':
        console.print(f'{LOGS_DIR}')
        return 0

    log_level: LogLevel = args.log_level

    enable_logging(log_level.value)

    # Parse combine args
    world_dir: Path = Maybe(args.world).unwrap(lambda: abort('[err]Option --world/-i is required[/]')).absolute()
    zoom: Literal[0, 1, 2, 3] = Maybe(args.zoom).unwrap(lambda: abort('[err]Option --zoom/-z is required[/]'))
    dest: Path = args.out.absolute()

    if not world_dir.is_dir():
        raise NotADirectoryError(f'Not a directory or does not exist: {world_dir}')
    if not (world_dir / str(zoom)).is_dir():
        raise NotADirectoryError(f'Found no directory for zoom level {zoom} under: {world_dir}')

    style: CombinerStyle = CombinerStyle()

    combiner: Combiner = Combiner(
        world_dir.parent,
        style=style,
        confirm_fn=lambda message: Confirm.ask(message),
        show_progress=True,
    )

    logger.info('Starting...')
    image: Image.Image = combiner.combine(
        world_dir,
        zoom=zoom,
    )

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
