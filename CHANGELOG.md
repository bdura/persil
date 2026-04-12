# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

### Added

- `lazy` API to replace `forward`-definition
- `Parser.span` method to attach location spans to results
- `RowCol.index` field
- `Parser.alt` takes the responsibility for `Parser.__or__`,
  which becomes a simple proxy
- `ParseError` exception class, now the only exception raised to
  user code on parse failure. It exposes structured `.err`, `.index`,
  `.expected`, and `.location` attributes.

### Fixed

- `from_enum` now fails on empty enum
- `Parser.until` would not handle max properly
- `Parser.skip` (`<<`) was returning the wrong index
- `many` parser no longer relies on a magic upper-bound value
- Better `eof`, `index` and `line_info` typing
- `Err.aggregate` no longer merges expectations across different
  stream positions — only the furthest error's expectations are kept,
  producing cleaner error messages

### Changed

- **Breaking:** `eof`, `index` and `line_info` are now functions returning
  parsers instead of bare parser instances
- **Breaking:** `from_stream` `desc` parameter is now keyword-only
- **Breaking:** `transform` parameter in `tag`, `string`, and
  `from_enum` defaults to `None` instead of `noop`; `tag` skips the
  transform call entirely when none is provided
- **Breaking:** `Err` is now a plain dataclass, no longer an
  `Exception`. Code that caught `Err` directly should catch
  `ParseError` instead.
- **Breaking:** `Err.expected` is now a `frozenset[str]` instead of
  `list[str]`, deduplicating alternatives automatically
- **Breaking:** `Err.location` is now `RowCol | int` instead of a
  pre-formatted string, making errors machine-readable
- **Breaking:** `Ok.ok_or_raise` / `Err.ok_or_raise` renamed to
  `Ok.ok` / `Err.ok`
- `Parser.until` gets a `return_other` parameter
- Rename `Parser.until_discard` to `Parser.until_excluding`
- Rename internal `SoftError` to `Backtrack` for clarity
- Simplify `regex` parser, removing type-unsafe groups
- All error construction sites now use `Err.from_stream`

### Removed

- `generate` decorator
- `forward`-definition API
- `noop` utility function
- Support for Python 3.11 and below

## [0.1.0] - 2024-04-19

Initial release :tada:

### Features

- Type-hinted "fork" of the excellent parsy library
- Type-friendly, Rust-inspired Result interface
- Added a `Stream` API for fully typed complex parsers
- Support for RegEx group dictionaries

### Deprecated

- `generate` decorator.

<!-- General links -->

[Keep a Changelog]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: https://semver.org/spec/v2.0.0.html

<!-- Release links -->

[Unreleased]: https://github.com/bdura/persil/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/bdura/persil/releases/tag/v0.1.0
