import pytest

from squaremap_combine.const import Rectangle
from squaremap_combine.util import Grid


@pytest.mark.parametrize(('rect', 'step_count_x', 'step_count_y'),
    [
        ((0, 0, 200, 200), 20, 20),
        ((0, 0, 150, 200), 15, 20),
        ((0, 0, 200, 150), 20, 15),
        ((-100, -100, 100, 100), 20, 20),
        ((-100, -100, 50, 100), 15, 20),
        ((-100, -100, 100, 50), 20, 15),
        ((-300, -300, -100, -100), 20, 20),
        ((-300, -300, -150, -100), 15, 20),
        ((-300, -300, -100, -150), 20, 15),
    ],
)
def test_grid_instance(rect: Rectangle, step_count_x: int, step_count_y: int) -> None:
    g = Grid(rect, step=10)
    assert (g.x1, g.y1, g.x2, g.y2) == g.rect == rect
    assert len(g.steps_x) == step_count_x
    assert len(g.steps_y) == step_count_y
    assert g.steps_count == (len(g.steps_x) * len(g.steps_y)) == (step_count_x * step_count_y)
    assert g.steps_count == len(list(g.iter_steps()))
