# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.45.0] - 2026-10-06

### Added
- `--help-json` machine-readable CLI catalog for Cordis / suite overlay generation.
- CLI (and MCP) check PyPI at most once per day for a newer release and print one stderr / tool-response line (`uv tool upgrade …`). Disabled with `AGENTS_NO_UPDATE_CHECK=1` or when `CI` is set; offline/timeout stays silent.

### Note
- GitHub previously tagged `v0.44.0` without a matching PyPI upload (PyPI stayed at `0.43.0`). This release is the first suite-aligned browser cut meant for PyPI after that gap.

## [0.44.0] - 2026-09-04

See GitHub release notes for the headless CDP browser MCP surface.

[Unreleased]: https://github.com/Lolaplex/agents-browser/compare/v0.45.0...HEAD
[0.45.0]: https://github.com/Lolaplex/agents-browser/compare/v0.44.0...v0.45.0
[0.44.0]: https://github.com/Lolaplex/agents-browser/releases/tag/v0.44.0
