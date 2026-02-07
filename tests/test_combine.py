import shutil
from pathlib import Path
from typing import Literal

import pytest
from PIL import Image

from squaremap_combine.core import Combiner

TEST_DATA_DIR: Path = Path(__file__).absolute().parent / 'data'
TEST_TMP_DIR: Path = Path(__file__).absolute().parent / 'tmp'

if TEST_TMP_DIR.is_dir():
    shutil.rmtree(TEST_TMP_DIR)
TEST_TMP_DIR.mkdir(exist_ok=True)

@pytest.mark.parametrize(('world'),
    [
        'minecraft_overworld',
        'minecraft_the_end',
        'minecraft_the_nether',
    ],
)
@pytest.mark.parametrize(('zoom'), [3, 2, 1, 0])
@pytest.mark.parametrize(('area'),
    [
        (None),
        ((-600, -600, 600, 600)),
        ((-500, -500, 500, 500)),
        ((-600, -600, -100, -100)),
        ((100, 100, 600, 600)),
    ],
)
@pytest.mark.parametrize(('crop'),
    [
        None,
        'auto',
        ((500, 500)),
    ],
)
def test_combine_success(
        world: str,
        zoom: int,
        area: tuple[int, int, int, int] | None,
        crop: tuple[int, int] | Literal['auto'] | None,
    ) -> None:
    c: Combiner = Combiner(TEST_DATA_DIR / 'example-tiles/2000x2000')
    # Just a basic check to ensure no errors
    img: Image.Image = c.combine(world, zoom=zoom, area=area, crop=crop)
    assert isinstance(img, Image.Image), (world, zoom)

    dest: Path = TEST_TMP_DIR / 'out.png'
    img.save(dest)
    assert dest.is_file()
    assert dest.stat().st_size > 0

    dest.unlink()
