<h1 align="center">.agents / browser</h1>

<p align="center">
  <a href="https://github.com/Lolaplex/agents-browser/releases"><img src="https://img.shields.io/badge/version-0.46.0-blue.svg?style=flat-square" alt="Version 0.46.0"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Standard-orange.svg?style=flat-square" alt="MCP"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://pypi.org/project/agents-browser/"><img src="https://img.shields.io/pypi/v/agents-browser.svg?style=flat-square" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <strong>Ultra-fast, zero-Node Python CDP Browser MCP for AI coding agents.</strong><br>
  Connects directly to your local Chrome, Edge, or Brave instance via native CDP. Headless by default.
</p>

---

## Quickstart

### 1-Step Setup

```bash
pip install agents-browser && agents-browser init
```

Scaffolds `~/.agents/browser/`, autowires MCP configurations into your installed IDEs, and registers assistant skills.

> [!TIP]
> **🤖 Agent-Driven Setup (Zero Friction):**  
> Simply tell your coding agent: **"Install and set up agents-browser for me."**  
> The agent installs the package, runs `agents-browser init`, and interacts with web applications, documentation, and search engines autonomously.

*Source checkouts can also be installed and managed using [vand](https://github.com/Lolaplex/vand).*

---

## Why `.agents/browser`?

Traditional browser automation MCPs (Playwright, Puppeteer) introduce massive friction:
- Download ~300MB Chromium binaries that hog disk space
- Spin up heavy Node.js runtimes that leave detached zombie processes
- Lack access to existing user sessions, cookies, and saved logins
- Dump 100k+ tokens of raw bloated HTML into LLM context windows

**`agents-browser` connects directly to your installed browser via native CDP:**
- **Headless by Default:** Silent `--headless=new` background automation. Visible window only on explicit ask.
- **Zero Node.js / Zero 300MB Downloads:** Pure lightweight Python (`FastMCP` + `websockets`).
- **Indexed `@ref` Interactive Snapshots:** Generates clean markdown with compact element references (`[@1] Button: Login`, `[@2] Input: Search`).
- **High-Level Built-in Tools:** Web search, clean reader-mode extraction, table scraping, batch form filling, dropdown selection, viewport scrolling, in-page search, and network/DOM stability detection.
- **Persistent Sessions (`~/.agents/browser`):** Preserves cookies, sessions, and saved logins across turns.
- **Universal Multi-IDE Auto-Config:** Plugs into Cursor, Antigravity, Claude Desktop, and Zed in 1 second.

---

## Architecture & Flow

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                     CODING AGENT / IDE                      │
 │     Cursor · Antigravity · Claude Code · Windsurf · Zed     │
 └──────────────────────────────┬──────────────────────────────┘
                                │  FastMCP stdio
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                  AGENTS-BROWSER CDP CLIENT                  │
 │    Pure Python WebSocket · Port 9222 · Zero Node Runtime    │
 └──────────────────────────────┬──────────────────────────────┘
                                │  Direct CDP Commands
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │     LOCAL BROWSER (Chrome / Edge / Brave) — headless=new    │
 │    Persistent Profile: ~/.agents/browser                    │
 └──────────────┬───────────────────────────────┬──────────────┘
                │                               │
                ▼                               ▼
 ┌─────────────────────────────┐ ┌─────────────────────────────┐
 │    INDEXED SNAPSHOTS        │ │      HIGH-LEVEL TOOLS       │
 │  [@1] Button: Sign In       │ │  browser_search             │
 │  [@2] Input: Search         │ │  browser_read_article       │
 │  Compact Interactive Tokens │ │  browser_fill_form          │
 └─────────────────────────────┘ └─────────────────────────────┘
```

---

## CLI Reference

| Command | Purpose |
|---------|---------|
| `agents-browser init` | Plug & Play setup: auto-configures MCP across Cursor, Antigravity, Claude Desktop, Zed |
| `agents-browser open <URL>` | Navigates headless (add `--visible` for a desktop window) |
| `agents-browser system-open <URL>` | Opens URL in the OS default desktop browser |
| `agents-browser search "<query>"` | Performs a web search and prints top 10 organic markdown results |
| `agents-browser read` | Extracts active web page in clean Reader Mode |
| `agents-browser snapshot` | Captures text outline with compact indexed `@ref` interactive elements |
| `agents-browser screenshot --out <file>` | Captures a full or viewport PNG screenshot |
| `agents-browser serve` | Runs the FastMCP stdio server (default) |

---

## Task-Adaptive Tool Architecture

`agents-browser` adapts dynamically to the developer's specific task without forcing a rigid workflow:

- **Research & Reading:** `browser_search`, `browser_read_article` (distraction-free markdown), `browser_extract_pdf`, `browser_fetch` (fast HTTP using browser cookies).
- **Web Automation & Forms:** `browser_snapshot` (`@ref` indexing) → `browser_click`, `browser_type`, `browser_select`, `browser_fill_form`, `browser_scroll(target=...)`.
- **Data Scraping:** `browser_scrape(mode='table'|'links'|'text')`, `browser_download`.
- **Developer UI Testing & Dev Servers:** `browser_audit` (console errors & horizontal overflow detection), `browser_inspect`, `browser_get_styles`, `browser_get_layout`, `browser_set_viewport`.
- **Visual Proofs & Demos:** `browser_screenshot` (PNG), `browser_record` / `browser_record_start` + `stop` (MP4 video screencast via local ffmpeg).

---

## MCP Tools Reference

| Category | Tool | Parameters | Description |
| :--- | :--- | :--- | :--- |
| **Navigation** | `browser_open` | `url`, `new_tab`, `visible` | Navigate headless by default; intercepts direct downloads & auto-dismisses cookie overlays. |
| | `browser_system_open` | `url` | Open URL in the user's personal desktop browser (Floorp, Firefox, Chrome, Edge). |
| | `browser_set_headless` | `headless` | Toggle background headless mode (True = background, False = window). |
| | `browser_go_back` | *None* | Navigate back in browser history. |
| | `browser_reload` | `ignore_cache` | Reload active page (optional hard refresh). |
| | `browser_tabs` | *None* | List active browser tabs with IDs, titles, and URLs. |
| | `browser_switch_tab` | `tab_id` | Switch active tab focus. |
| **Research** | `browser_search` | `query`, `engine` | Direct web search returning top organic results with Title, URL, and Snippet. |
| | `browser_read_article` | *None* | Extracts clean article markdown, stripping ads, navbars, and banners. |
| | `browser_extract_pdf` | `url_or_ref`, `save_path`, `max_pages` | Extracts PDF streams via Chrome PDF Viewer or Page.printToPDF with text preview. |
| | `browser_fetch` | `url`, `method`, `headers`, `json_data`, `body` | Fast non-DOM HTTP/REST client using browser session cookies without rendering overhead. |
| **Automation** | `browser_snapshot` | *None* | Extract clean text outline with indexed `@ref` element IDs (`@1`, `@2`). |
| | `browser_click` | `target` | Click element by `@ref` (e.g. `@1`), CSS selector, or matching text. |
| | `browser_type` | `target`, `text`, `clear`, `press_enter` | Focus and type text into input/textarea. |
| | `browser_select` | `target`, `value` | Select dropdown `<select>` option by text, value, or substring. |
| | `browser_fill_form` | `fields_json`, `submit_selector` | Batch fill form fields and submit in one call. |
| | `browser_scroll` | `direction`, `amount`, `target` | Scroll page viewport or scroll target element smoothly into view. |
| | `browser_wait_stable` | `timeout_ms`, `quiet_ms` | Wait for network requests (fetch/XHR) and DOM mutations to settle. |
| | `browser_find` | `query`, `forward`, `match_case` | Fast in-page text search with match stats without dumping full page. |
| **Scraping** | `browser_scrape` | `selector`, `mode` (`"table"`, `"links"`, `"text"`, `"html"`) | Structured data extraction from CSS selector into Markdown. |
| | `browser_download` | `ref_or_url`, `dest_path` | Intercept and monitor CDP downloads to controlled local directories. |
| **UI Testing** | `browser_audit` | *None* | Automated developer audit: console errors, horizontal layout overflow, broken media, failed requests. |
| | `browser_inspect` | `target` | Complete element card: tag, attributes, text snippet, geometry, typography, and box-model. |
| | `browser_get_styles` | `target`, `properties` | Inspect computed CSS properties and declared CSS variables (`--*`). |
| | `browser_get_layout` | `target` | Inspect bounding rect (`x, y, w, h`), scroll metrics, and viewport visibility. |
| | `browser_get_logs` | `log_type`, `limit`, `clear` | Retrieve buffered console logs, uncaught exceptions, and failed HTTP network requests. |
| | `browser_set_viewport` | `width`, `height`, `preset`, `mobile` | Set viewport dimensions or apply presets (`mobile`, `tablet`, `desktop`, `fhd`). |
| | `browser_evaluate` | `script` | Execute arbitrary JavaScript expression in tab context. |
| **Visuals** | `browser_screenshot` | `full_page`, `path` | Capture PNG screenshot to `~/.agents/browser/screenshots/` (returns path + FastMCP Image). |
| | `browser_record` | `duration_sec`, `fps`, `path` | One-shot screen recording exported to MP4 video (or GIF) via local ffmpeg. |
| | `browser_record_start` | `fps` | Begin interactive multi-step screen recording session. |
| | `browser_record_stop` | `path` | Stop active recording session and encode captured frames into an MP4 video. |

---

## Supported Ecosystem

- **Claude Code:** Bound via MCP server and `.agents/skills/browser-browse`.
- **Google Antigravity:** Integrated via `.gemini/config` rules and `agents-browser` MCP.
- **Cursor:** Automatically configures `.cursor/mcp.json` and agent rules.
- **Zed:** Configures `context_servers` and mirrors assistant skills.
- **VS Code / Windsurf:** Autowires Cline / Roo-Code MCP configuration.

---

## Open ABI Specification

Detailed architectural specifications live in [`abi/`](abi/):
- [`abi/WHY.md`](abi/WHY.md) — Rationale & why CDP beats heavy Node.js frameworks.
- [`abi/LAYOUT.md`](abi/LAYOUT.md) — Storage taxonomy in `~/.agents/browser/`.
- [`abi/MCP.md`](abi/MCP.md) — Tool surface definitions and request/response contracts.
- [`abi/TOOLS.md`](abi/TOOLS.md) — Exhaustive MCP tool reference & type signatures.
- [`abi/PLATFORM.md`](abi/PLATFORM.md) — Multi-platform browser binary & profile resolution.

---

## Testing & Verification

Run the test suite:

```bash
python tests/run_all_tests.py
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
