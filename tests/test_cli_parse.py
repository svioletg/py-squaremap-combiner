import pytest

from squaremap_combine.cli import opt_crop, opt_grid_font, opt_grid_lines, opt_rect
from squaremap_combine.geo import Rect
from squaremap_combine.util import Color


def test_opt_crop() -> None:
    assert opt_crop('200,100') == (200, 100)
    assert opt_crop('200, 100') == (200, 100)
    with pytest.raises(SystemExit):
        assert opt_crop('200')

def test_opt_grid_font() -> None:
    assert opt_grid_font('Consolas.ttf') == ('Consolas.ttf', 32, Color.from_name('white'))
    assert opt_grid_font('Arial.ttf, 16') == ('Arial.ttf', 16, Color.from_name('white'))
    assert opt_grid_font('Times New Roman.ttf, 16, red') == ('Times New Roman.ttf', 16, Color.from_name('red'))

def test_opt_grid_lines() -> None:
    assert opt_grid_lines('black') == (Color.from_name('black'), 1)
    assert opt_grid_lines('black 1') == (Color.from_name('black'), 1)
    assert opt_grid_lines('white 4') == (Color.from_name('white'), 4)
    assert opt_grid_lines('#ff00ff 2') == (Color.from_hex('#ff00ff'), 2)

def test_opt_rect() -> None:
    expected: Rect = Rect((-32, -16, 32, 16))
    assert opt_rect('')('-32,-16,32,16') == expected
    assert opt_rect('')('-32, -16, 32, 16') == expected
    with pytest.raises(SystemExit):
        assert opt_rect('')('-32, -16, 32')
    with pytest.raises(SystemExit):
        assert opt_rect('')('-32, -16')
    with pytest.raises(SystemExit):
        assert opt_rect('')('-32')
