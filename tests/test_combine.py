from itertools import product
from pathlib import Path

import pytest

from squaremap_combine.core import Combiner

TEST_DATA_DIR: Path = Path(__file__).absolute().parent / 'data'

@pytest.mark.parametrize(('area'),
    [
        (None),
        ((-600, -600, 600, 600)),
        ((-500, -500, 500, 500)),
        ((-600, -600, -100, -100)),
        ((100, 100, 600, 600)),
    ],
)
def test_combine_success(area: tuple[int, int, int, int] | None) -> None:
    c: Combiner = Combiner(TEST_DATA_DIR / 'example-tiles/2000x2000')
    for world, zoom in product(
        ('minecraft_overworld', 'minecraft_the_end', 'minecraft_the_nether'),
        (3, 2, 1, 0),
    ):
        assert c.combine(world, zoom=zoom, area=area), (world, zoom)
