# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

This release is meant to be a major overhaul to the entire squaremap-combine project, and includes **many breaking changes**. In general, lots of cleanup and linting has been done (in part thanks to moving from pylint to ruff), and many features have been either removed or reworked for the sake of narrowing project scope and strengthening core functionality. Notably...

- The previous `dearpygui` implementation of the GUI wrapper has been removed — the plan is to eventually replace it with a new Qt/PySide-based GUI, but the focus right now is on improving the CLI.
- Options for styling image output (mainly grid-related) have been reduced or simplified — again, to put more focus on core functionality.

### Added

- Added multiple CLI options:
  - Added `-z/--zoom`
  - Added `--grid-lines`
- Added module `const`
- Added test module `test_grid_class`
- Added class `util.Grid`
- Added class `util.Rect`
- Added enum class `const.NamedColorHex`
- Added `JSONEncoder`-extended class `ImplementableJSONEncoder` to `util`
  - Allows classes to implement a `__json__()` method for serialization

### Changed

- Changed multiple CLI options:
  - All options now either only use a single character for their short name, or have no short name at all
  - Renamed `--output-dir` to `--out`, now takes a file path instead of a directory path
  - Renamed `-a/--area` to `-r/--rect`
  - Renamed `-g/--grid-interval` to `-g/--grid`
  - Renamed `-gcf/--grid-coords-format` to `--grid-coords` (no short name)
- Renamed module `helper` to `util`
- Renamed class `AssertionMessage` in module `errors` to `ErrMsg`
- Moved class `Coord2i` from `combine_core` to `util`
- Renamed class attribute `MapImage.detail_mul` to `MapImage.zoom`

### Deprecated

- The dearpygui-powered GUI wrapper is no longer supported, and will be replaced by a PySide/Qt implementation at later date

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
  - Aliases `ColorRGB` and `ColorRGBA` were unused, `Rectangle` has been replaced with a full class in the form of `util.Rect`
- Removed multiple class methods from `combine_core.MapImage`: `getbbox()`, `paste()`, `save()`
  - The object's `img` attribute should be accessed directly for these methods instead
- Removed class `StyleJSONEncoder` from `util`; replaced with `ImplementableJSONEncoder`
- Removed class attribute `COMMON` from `util.Color`
- Removed class method `from_name` from `util.Color`
- Removed method `to_json` from `combine_core.CombinerStyle`
- Removed function `util.copy_method_signature`
