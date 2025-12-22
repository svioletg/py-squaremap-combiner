import pytest

from squaremap_combine.util import Color, NamedColorHex


@pytest.mark.parametrize(('channels', 'expected'),
    [
        ((0, 0, 0),            Color(0, 0, 0, 255)),
        ((255, 255, 255),      Color(255, 255, 255, 255)),
        ((0, 0, 0, 255),       Color(0, 0, 0, 255)),
        ((255, 255, 255, 127), Color(255, 255, 255, 127)),
    ],
)
def test_color_instance_rgb_rgba(channels: tuple[int, int, int] | tuple[int, int, int, int], expected: Color) -> None:
    c: Color = Color(*channels)
    assert c == expected
    assert channels == c.as_rgba()[:len(channels)]
    assert c == Color(*c.as_rgba())

@pytest.mark.parametrize(('hexcode', 'expected'),
    [
        ('#000000', Color(0, 0, 0, 255)),
        ('#ff0000', Color(255, 0, 0, 255)),
        ('#ff00007f', Color(255, 0, 0, 127)),
    ],
)
def test_color_instance_from_hex(hexcode: str, expected: Color) -> None:
    c: Color = Color.from_hex(hexcode)
    assert c == expected == Color.from_hex(hexcode.removeprefix('#'))

@pytest.mark.parametrize(('name', 'alpha', 'expected'),
    [
        (NamedColorHex.CLEAR, None, Color(0, 0, 0, 0)),
        ('clear', None, Color(0, 0, 0, 0)),
        (NamedColorHex.BLACK, None, Color(0, 0, 0, 255)),
        ('black', None, Color(0, 0, 0, 255)),
        (NamedColorHex.RED, None, Color(255, 0, 0, 255)),
        ('red', None, Color(255, 0, 0, 255)),
        (NamedColorHex.RED, 127, Color(255, 0, 0, 127)),
        ('red', 127, Color(255, 0, 0, 127)),
    ],
)
def test_color_instance_from_name(name: NamedColorHex | str, alpha: int | None, expected: Color) -> None:
    c: Color = Color.from_name(name, alpha)
    assert c == expected
