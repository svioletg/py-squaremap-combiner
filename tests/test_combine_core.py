"""
Tests for `squaremap_combine.combine_core`.
"""

import json
import os
from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from tqdm import tqdm

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

def generate_test_params() -> dict:
    """Use the defined `TEST_PARAMS_OUTLINE` to generate additional parameter sets based off a few known
    finite options, like detail level or world choice.
    """
    param_dict = {}
    # Every dimension has the same format of "X_Y.png" files in the same size,
    # running this through each one is overkill
    world = 'minecraft_overworld'

    for name, params in TEST_PARAMS_OUTLINE.items():
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

    Storing large amounts of images for this is not ideal, so instead the images are hashed and stored to a JSON file
    keyed by their test parameter set names.

    This function generates 10 images at a time, and then waits for user input to continue. This is so they can be
    manually verified as accurate before being hashed. If the user confirms they are, the images are converted,
    stored in the soon-to-be-JSON dictionary, and deleted. This continues until the dictionary of test parameters is exhausted.
    """
    stored: dict[str, Path] = {}
    hash_dict: dict[str, str] = {}

    def verify_and_encode_stored():
        print('\n')
        if input('Verify the current batch of control images are accurate before they are encoded. (y/n) ') \
            .lower().strip() != 'y':
            print('Cancelled.')
            return
        else:
            for k, v in tqdm(stored.items()):
                barr = BytesIO()
                Image.open(v).save(barr, format='png')
                hash_dict[k] = sha256(barr.getvalue()).hexdigest()
                os.remove(v)
            stored.clear()

    for name, params in tqdm(TEST_PARAMS_FULL.items()):
        outfile = TEST_CONTROL / f'{name}.png'
        tqdm.write(f'{params}\n -> {outfile}')

        combiner = Combiner(params.tiles_dir, **params.cls_kwargs)
        combiner.combine(**params.func_kwargs).save(outfile)
        stored[name] = outfile

        if len(stored) == 10:
            verify_and_encode_stored()
    if len(stored) != 0:
        verify_and_encode_stored()

    with open(TEST_CONTROL / 'control_group_hash.json', 'w', encoding='utf-8') as f:
        json.dump(hash_dict, f, indent=4)

def load_control_group() -> dict[str, str]:
    """Load the control group JSON."""
    with open(TEST_CONTROL / 'control_group_hash.json', 'r', encoding='utf-8') as f:
        return json.load(f)

control_group_hash: dict[str, str] = load_control_group()

def check_missing_control():
    """Raises an error if no corresponding images are found for a test parameter set."""
    test_keys = set(TEST_PARAMS_FULL.keys())
    json_keys = set(control_group_hash.keys())
    diff = test_keys - json_keys
    if diff:
        raise KeyError(f'Control hashes are missing for these tests: {', '.join(diff)}')

@pytest.mark.parametrize('param_set', TEST_PARAMS_FULL)
def test_map_creation(param_set):
    """Tests map image creation using a given `CombinerTestParams` instance."""
    name, params = param_set, TEST_PARAMS_FULL[param_set]
    combiner = Combiner(params.tiles_dir, **params.cls_kwargs)
    test_barr = BytesIO()
    combiner.combine(**params.func_kwargs).save(test_barr, format='png')
    assert control_group_hash[name] == sha256(test_barr.getvalue()).hexdigest()

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
