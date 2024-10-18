"""
Tests for `squaremap_combine.combine_core`.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageChops

from squaremap_combine.combine_core import Combiner

TEST_TILES = Path('example-tiles')
TEST_CONTROL = Path('tests/data/control') # Control group, image results to check tests against
TEST_OUT = Path('tests/data/out') # Where to temporarily store test output files, if needed

@dataclass
class CombinerTestParams:
    """Defines a set of parameters for the `Combiner` class and `Combiner.combine` function each to test with."""
    tiles_dir: Path = TEST_TILES / '2000x2000'
    cls_kwargs: dict[str, Any] = field(default_factory=dict)
    func_kwargs: dict[str, Any] = field(default_factory=lambda: {'world': 'minecraft_overworld', 'detail': 3})

WORLDS = ['minecraft_overworld', 'minecraft_the_nether', 'minecraft_the_end']
DETAIL_LEVELS = [0, 1, 2, 3]

TEST_PARAMS_OUTLINE: dict[str, CombinerTestParams] = {
    'basic': CombinerTestParams(),
    'grid512': CombinerTestParams(cls_kwargs={'grid_interval': (512, 512)})
}

def check_missing_control():
    """Raises an error if no corresponding images are found for a test parameter set."""
    for name in TEST_PARAMS_OUTLINE:
        if len([*TEST_CONTROL.glob(f'{name}*.png')]) == 0:
            raise FileNotFoundError(f'No reference images are available for parameter set: {name}')

def generate_test_params():
    """Use the defined `TEST_PARAMS_OUTLINE` to generate additional parameter sets based off a few known
    finite options, like detail level or world choice.
    """
    param_dict = {}

    for name, params in TEST_PARAMS_OUTLINE.items():
        for world in WORLDS:
            for detail in DETAIL_LEVELS:
                tiles_dir = params.tiles_dir
                cls_kwargs = params.cls_kwargs
                func_kwargs = params.func_kwargs.copy()
                func_kwargs['world'] = world
                func_kwargs['detail'] = detail
                param_dict[f'{name}-world-{world}-detail-{detail}'] = CombinerTestParams(tiles_dir, cls_kwargs, func_kwargs)

    return param_dict

TEST_PARAMS_FULL: dict[str, CombinerTestParams] = generate_test_params()

def generate_control_group():
    """Creates an image using every set of test parameters available, to be used as a control group against later tests.
    This will need to be run if any param set names have changed, or `combine_core` saw a fundamental change that altered
    how it creates images, thus rendering the previous control group inaccurate.
    """
    for name, params in TEST_PARAMS_FULL.items():
        outfile = TEST_CONTROL / f'{name}.png'
        print(f'{params}\n -> {outfile}')
        combiner = Combiner(params.tiles_dir, **params.cls_kwargs)
        combiner.combine(**params.func_kwargs).save(TEST_CONTROL / f'{name}.png')

@pytest.mark.parametrize('param_set', TEST_PARAMS_FULL)
def test_map_creation(param_set):
    """Tests map image creation using a given `CombinerTestParams` instance."""
    name, params = param_set, TEST_PARAMS_FULL[param_set]
    combiner = Combiner(params.tiles_dir, **params.cls_kwargs)
    result = combiner.combine(**params.func_kwargs).img.convert(mode='RGB')
    control = Image.open(TEST_CONTROL / f'{name}.png').convert(mode='RGB')
    diff = ImageChops.difference(control, result)
    assert diff.getbbox() is None

def main(): # pylint: disable=missing-function-docstring
    if input('Generate new control group? (y/n) ').strip().lower() != 'y':
        print('Cancelling.')
        return

    print(TEST_CONTROL.absolute())
    if input('Ensure the control group directory above is correct before continuing. (y/n) ').strip().lower() != 'y':
        print('Cancelling.')
        return

    print('Removing old group...')
    for f in TEST_CONTROL.glob('*.png'):
        print(f'Delete: {f.absolute()}')
        os.remove(f.absolute())

    print('Generating new group...')
    generate_control_group()

if __name__ == '__main__':
    main()
else:
    check_missing_control()
