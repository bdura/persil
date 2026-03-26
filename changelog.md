# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `lazy` API to replace `forward`-definition
- `Parser.alt` takes the responsibility for `Parser.__or__`,
  which becomes a simple proxy

### Fixed

- `from_enum` now fails on empty enum
- `Parser.until` would not handle max properly
- `Parser.skip` (`<<`) was returning the wrong index

### Changed

- `Parser.until` gets a `return_other` parameter
- Rename `Parser.until_discard` to `Parser.until_excluding`
- Simplify `regex` parser, removing type-unsafe groups

### Removed

- `generate` decorator
- `forward`-definition API
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

[Unreleased]: https://github.com/olivierlacan/keep-a-changelog/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/olivierlacan/keep-a-changelog/releases/tag/v0.1.0
