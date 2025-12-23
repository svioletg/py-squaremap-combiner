# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-beta.2]

### Fixed

- Fixed log message format used in file logging to be consistent with stdout log format

## [1.0.0-beta.1]

This release is meant to be a major overhaul to the entire squaremap-combine project, and includes **many breaking changes**. In general, lots of cleanup and linting has been done (in part thanks to moving from pylint to ruff), and many features have been either removed or reworked for the sake of narrowing project scope and strengthening core functionality. Notably...

- The previous `dearpygui` implementation of the GUI wrapper has been removed — the plan is to eventually replace it with a new Qt/PySide-based GUI, but the focus right now is on improving the CLI.
- Options for styling image output (mainly grid-related) have been reduced or simplified — again, to put more focus on core functionality.

### Added

- Added multiple CLI options:
  - Added `-z/--zoom`
  - Added `--grid-lines`
  - Added `--grid-font`
  - Added `--no-progress-bar`
- Added module `const`
- Added module `geo`
  - Added class `Coord2f`
    - Largely identical to `Coord2i`, but operates on floats exclusively
  - Added class `Grid`
  - Added class `Rect`
  - Added method `map()` to `Coord2i`
- Added test module `test_color_class`
- Added test module `test_geometry`
- Added `JSONEncoder`-extended class `ImplementableJSONEncoder` to `util`
  - Allows classes to implement a `__json__()` method for serialization
- Added enum class `const.NamedColorHex`
- Added enum class `logging.LogLevel`
- Added function `util.coerce_to`
- Added function `util.draw_corners`

### Changed

- Changed multiple CLI options:
  - All options now either only use a single character for their short name, or have no short name at all
  - Renamed `--output-dir` to `--out`, now takes a file path instead of a directory path
  - Renamed `-g/--grid-interval` to `-g/--grid`
  - Renamed `-gcf/--grid-coords-format` to `--grid-coords` (no short name)
- Renamed module `combine_cli` to `cli`
- Renamed module `combine_core` to `core`
- Renamed module `helper` to `util`
- Renamed class `AssertionMessage` in module `errors` to `ErrMsg`
- Moved class `Coord2i` from `core` to `geo`
- Renamed attribute `MapImage.detail_mul` to `MapImage.zoom`
- Rewrote class `core.Combiner`, [see the docs](https://squaremap-combine.readthedocs.io/en/latest/reference/core.html#squaremap_combine.core.Combiner) for details
- In module `util`:
  - Renamed method `Color.to_hex()` to `Color.as_hex()`
  - Renamed method `Color.to_rgb()` to `Color.as_rgb()`
  - Renamed method `Color.to_rgba()` to `Color.as_rgba()`
- In module `geo`:
  - `Coord2i` is now subscriptable, with `Coord2i(...)[0], Coord2i(...)[1]` being equivalent to `Coord2i(...).x, Coord2i(...).y`
  - `Coord2i.__init__()` can now accept a `tuple[int, int]` or another `Coord2i` instance as a first argument, in which case no `y` argument is required
- `logging.enable_logging()` now only affects `logging.logger`

### Removed

- Removed multiple CLI options:
  - Removed `-ext/--output-ext`; image format now inferred from the suffix of `-o/--out`
  - Removed `-t/--timestamp`
  - Removed `-fs/--force-size`
  - Removed `-sf/--style-file`
  - Removed `-so/--style-override`
- Removed optional dependency group `gui`
- Removed module `gui`
- Removed module `project`; contents moved to `const`
- Removed module `type_alias`
  - Aliases `ColorRGB` and `ColorRGBA` were unused and thus not moved anywhere
  - Alias `Rectangle` removed, either the new `Rect` class or `tuple[int, int, int, int]` will be used
- In module `core`:
  - Removed class `MapImage`
  - Removed class `MapImageCoord`
  - Removed class `GameCoord`
  - Removed method `draw_grid_lines()` from `core.Combiner`
  - Removed method `draw_grid_coords_text()` from `core.Combiner`
  - Removed method `to_json()` from `core.CombinerStyle`
  - Removed multiple methods from `core.MapImage`: `getbbox()`, `paste()`, `save()`
    - The object's `img` attribute should be accessed directly for these methods instead
- In module `util`:
  - Removed class `StyleJSONEncoder`; replaced with `ImplementableJSONEncoder`
  - Removed class attribute `COMMON` from `Color`
  - Removed class method `from_name()` from `Color`
  - Removed multiple functions: `confirm_yn()`, `copy_method_signature()`, `filled_tuple()`
- Removed multiple constants from `const`:
  - `APP_SETTINGS_PATH`
  - `DEFAULT_COORDS_FORMAT`
  - `DEFAULT_OUTFILE_FORMAT`
  - `DEFAULT_TIME_FORMAT`
  - `OPT_AUTOSAVE_PATH`
  - `STYLE_AUTOSAVE_PATH`
