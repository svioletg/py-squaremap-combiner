# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

- In `combine_core`:
  - `MapImage` methods `getbbox()`, `paste()`, and `save()` removed — the object's `img` attribute should be accessed directly instead
- CLI options:
  - All options now either only use a single character for their short name, or have no short name at all
  - `--output-dir` renamed to `--out`, now takes a file path instead of a directory path
  - `-a/--area` renamed to `-r/--rect`

### Deprecated

- The dearpygui-powered GUI wrapper is no longer supported, and will be replaced by a PySide/Qt implementation at later date

### Removed

- CLI options:
  - Removed the `-ext/--output-ext` option; now inferred from the suffix of `-o/--out`
  - Removed the `-t/--timestamp` option
  - Removed the `-fs/--force-size` option
