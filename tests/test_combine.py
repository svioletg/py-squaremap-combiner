from pathlib import Path
from typing import Literal

import pytest

from squaremap_combine.core import Combiner

TEST_DATA_DIR: Path = Path(__file__).absolute().parent / 'data'

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
    assert c.combine(world, zoom=zoom, area=area, crop=crop), (world, zoom)
