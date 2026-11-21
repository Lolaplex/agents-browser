# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `web_extract`/read fallbacks pretty-print raw JSON endpoints (application/json bodies used to return "(no readable text)").
- `browser_fill_form` accepts a `fields` dict alongside the `fields_json` string form.
- `browser_record` output notes "(mostly static page)" when screencast yields <5 unique frames (damage-based capture reads as near-empty otherwise).
- `agents-browser install [--full]`: opt-in Chrome for Testing download into `<host>/browser/bin/` (`chrome-headless-shell` ~100MB; `--full` for the visible-capable `chrome` binary). Pure stdlib, no root; discovery prefers env override, then system browsers, then managed binaries. Never bundled — pip install stays 0MB.
- Lite mode (default on, `AGENTS_BROWSER_LITE=0` off): `Network.setBlockedURLs` skips image/font/media requests on navigations to cut renderer RAM on heavy pages. Auto-disables — unblocking and reloading — when `browser_screenshot`/`browser_audit`/`browser_record` or visible mode runs, since real pixels need media loaded. `browser_lite` MCP tool toggles mid-session.
- `--disable-dev-shm-usage` launch flag on detected containers (`/.dockerenv`, `/run/.containerenv`, or cgroup match) so Chrome survives small `/dev/shm`.
- `--help-json` emits `cordis_expose: true` so agents-harness auto-mounts this package's commands as Cordis tools when no checked-in manifest exists (#32/#34).
- `web_search` + `web_extract` MCP tools: dependency-free stdlib HTTP path for hosts with no Chrome/CDP at all (bare VPS, containers). Search runs `auto` (searxng via `AGENTS_SEARXNG_URL`, then duckduckgo, then bing HTML) or a named engine; extract strips script/nav chrome to readable markdown-ish text + links via the `webtext` module (no JS rendering). `browser_search` and `browser_read_url`/`browser_scrape` fall back to the same path when no Chromium session is available.

### Changed
- Console/network log buffers clear on navigation and tab switch so `browser_audit`/`browser_get_logs` stop mixing entries from other tabs sharing the debug profile.
- Sync tests point at the workspace root (`<host>/workspaces/default`) now that `AGENTS_HOME` is removed; canonical rules/AGENTS.md land under the selected workspace.

### Changed
- `.mailmap` maps legacy `Klix`/`Felix Kempf` author names to `Klix927` (no history rewrite; display only).

### Added
- Workspace resolver: browser profile lives on the host (`<host>/browser`, env `AGENTS_BROWSER_PROFILE`; `AGENTS_BROWSER_SESSION` kept as a deprecated one-release alias). Artifacts (screenshots, downloads, recordings) are workspace-scoped under `<ws>/browser/`. Sync writes rules/skills/AGENTS.md into the workspace root and `mcp.json` on the host. Update-check cache under `<host>/cache/updates/`.
- **Standalone CLI with full MCP parity.** Every `browser_*` tool now has a shell verb: `open`, `snapshot` (`-i` interactive-only, `-d` diff), `click`, `type`, `fill`, `select`, `scroll`, `back`, `reload`, `wait`, `find`, `tabs`, `switch-tab`, `read`, `scrape`, `screenshot`, `audit`, `inspect`, `headless`, `close`, and `skills`. The background browser keeps the active tab and the `@ref` indices across separate invocations.
- `--help-json` declares `side_effects` for every CLI verb, so the harness classifies a read as read-only and an action as mutating.
- `click` checks visibility, disabled state, and `elementFromPoint` hit-testing before it acts, so a covering modal is reported instead of silently swallowed.

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
