import pytest

from squaremap_combine.util import Coord2i, Grid, Rect


@pytest.mark.parametrize(('coords'),
    [
        ((0, 0, 200, 200)),
        ((0, 0, 150, 200)),
        ((0, 0, 200, 150)),
        ((-100, -100, 100, 100)),
        ((-100, -100, 50, 100)),
        ((-100, -100, 100, 50)),
        ((-300, -300, -100, -100)),
        ((-300, -300, -150, -100)),
        ((-300, -300, -100, -150)),
    ],
)
def test_rect_instance(coords: tuple[int, int, int, int]) -> None:
    r: Rect = Rect(*coords)
    assert (r.x1, r.y1, r.x2, r.y2) == r.as_tuple() == coords
    assert (Coord2i(r.x1, r.y1), Coord2i(r.x2, r.y2)) \
        == (Coord2i(coords[0], coords[1]), Coord2i(coords[2], coords[3])) \
        == r.as_coords()

@pytest.mark.parametrize(('radius', 'origin', 'expected_rect'),
    [
        (100, None, (-100, -100, 100, 100)),
        (100, (25, 25), (-75, -75, 125, 125)),
        (100, Coord2i(25, 25), (-75, -75, 125, 125)),
        (100, (-25, -25), (-125, -125, 75, 75)),
        (100, Coord2i(-25, -25), (-125, -125, 75, 75)),
        (-100, None, ()),
    ],
)
def test_rect_from_radius(
        radius: int,
        origin: Coord2i | tuple[int, int] | None,
        expected_rect: tuple[int, int, int, int],
    ) -> None:
    if radius <= 0:
        with pytest.raises(ValueError, match='radius must be greater than zero'):
            r = Rect.from_radius(radius, origin)
        return
    r: Rect = Rect.from_radius(radius, origin)
    assert r.as_tuple() == expected_rect

@pytest.mark.parametrize(('coords', 'step_count_x', 'step_count_y'),
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
def test_grid_instance(coords: tuple[int, int, int, int], step_count_x: int, step_count_y: int) -> None:
    g: Grid = Grid(coords, step=10)
    assert (g.rect.x1, g.rect.y1, g.rect.x2, g.rect.y2) == g.rect.as_tuple() == coords
    assert len(g.steps_x) == step_count_x
    assert len(g.steps_y) == step_count_y
    assert g.steps_count == (len(g.steps_x) * len(g.steps_y)) == (step_count_x * step_count_y) \
        == len(list(g.iter_steps()))
