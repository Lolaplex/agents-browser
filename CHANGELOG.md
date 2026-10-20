# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.46.0] - 2026-10-20

### Added
- **Developer Page Evaluation & Inspection Suite**:
  - `browser_audit`: 1-click automated developer healthcheck for active page (uncaught console errors/warnings, horizontal layout overflow with offending element detection, broken media, failed 4xx/5xx network requests, loaded web fonts).
  - `browser_inspect`: Full element inspection in one call (Tag, Classes, Attributes, Text snippet, Bounding Rect, Typography, Box-Model, Parent & Children preview).
  - `browser_get_styles`: Direct computed CSS inspection and declared CSS custom variables (`--*`), eliminating need for ad-hoc `browser_evaluate` JavaScript.
  - `browser_get_layout`: Exact geometry metrics (x, y, width, height, top/right/bottom/left), scroll metrics, and viewport visibility/overflow checks.
  - `browser_get_logs`: Buffered console logs, runtime uncaught exceptions, and failed HTTP requests with log filtering (`all`, `console`, `error`, `network`).
  - `browser_set_viewport`: Viewport resizing and device emulation presets (`mobile`/`iphone`, `tablet`/`ipad`, `desktop`, `fhd`) via CDP `Emulation.setDeviceMetricsOverride`.
  - `browser_record`: Native screen recording using CDP `Page.startScreencast` with direct pipe encoding to MP4 video (or GIF) via local `ffmpeg`.
  - `browser_record_start` & `browser_record_stop`: Interactive multi-step screencast recording across multiple actions/tools.
  - Target-based scrolling in `browser_scroll`: Supports `target` parameter (`@ref`, CSS selector, or matching text) to smoothly scroll any element into view.
  - Download trap interception in `browser_open`: Detects direct file downloads on navigation and reports downloaded filename and path instead of leaving page on `about:blank`.
  - `browser_download`: Intercepts and monitors CDP downloads (`Page.downloadWillBegin`, `Page.downloadProgress` until `state == 'completed'`) via element click or URL, saving into a controlled directory and returning the exact verified local path.
  - `browser_fetch`: Fast non-DOM HTTP/REST client using browser session cookies without DOM parsing or rendering overhead.
  - `browser_extract_pdf`: Direct extraction of PDF streams via Chrome PDF Viewer (Blob-Extract or `Page.printToPDF`), saving PDF to disk with extracted text preview and page count.
  - CLI subcommands for `download`, `fetch`, and `extract-pdf`.

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
