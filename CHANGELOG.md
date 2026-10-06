# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.45.0] - 2026-10-06

### Added
- `--help-json` machine-readable CLI catalog for Cordis / suite overlay generation.
- CLI (and MCP) check PyPI at most once per day for a newer release and print one stderr / tool-response line (`uv tool upgrade …`). Disabled with `AGENTS_NO_UPDATE_CHECK=1` or when `CI` is set; offline/timeout stays silent.

### Changed
- CI runs only on pull requests to `main`.

### Removed
- GitHub Release is no longer cut automatically on `v*.*.*` tags (manual `gh release create` from CHANGELOG instead).

### Note
- GitHub previously tagged `v0.44.0` without a matching PyPI upload (PyPI stayed at `0.43.0`). This release is the first suite-aligned browser cut meant for PyPI after that gap.

## [0.44.0] - 2026-09-04

### Added
- Headless-by-default CDP (`--headless=new`); snapshot, click, type, search, scrape, and the rest run without a window. `AGENTS_BROWSER_HEADLESS=0` forces visible launches.
- Visible window on explicit ask: `browser_open(..., visible=True)`, `browser_set_headless(False)`, CLI `open --visible`.
- `browser_system_open` opens a URL in the user's desktop browser (their cookies and logins) only when asked.

### Changed
- Attaches only to a debug browser matching the requested headless/visible mode; a wrong-mode process is closed and relaunched.

## [0.43.0] - 2026-08-23

### Added
- `browser_select`: pick `<select>` options by visible text, value, or substring via `@ref` or CSS.
- `browser_scroll`: viewport scroll (`down` / `up` / `top` / `bottom`) with optional pixel distance.
- `browser_find`: in-page text search with match counts and focus navigation.
- `browser_wait_stable`: wait for DOM mutations and in-flight fetch/XHR before continuing.
- `browser_go_back` and `browser_reload` (hard or soft cache).
- Bundled ABI and skills auto-sync for install and IDE onboarding.

## [0.42.0] - 2026-08-20

### Added
- Direct Chrome DevTools Protocol WebSocket connection (no Playwright, Puppeteer, or Node).
- Compact `@ref` element snapshots for clicks and typing.
- Built-in search, reader-mode, scrape, and batch form fill.
- Persistent sessions under `~/.agents/browser`.
- Multi-IDE MCP autowire (Cursor, Antigravity, Claude, Zed).

[Unreleased]: https://github.com/Lolaplex/agents-browser/compare/v0.44.0...HEAD
[0.44.0]: https://github.com/Lolaplex/agents-browser/compare/v0.43.0...v0.44.0
[0.43.0]: https://github.com/Lolaplex/agents-browser/compare/v0.42.0...v0.43.0
[0.42.0]: https://github.com/Lolaplex/agents-browser/releases/tag/v0.42.0
=======
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
>>>>>>> feat/update-check
