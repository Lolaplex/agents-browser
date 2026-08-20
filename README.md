# agents-browser

<p align="left">
  <a href="https://github.com/Lolaplex/agents-browser/releases"><img src="https://img.shields.io/badge/version-0.42.0-blue.svg?style=flat-square" alt="Version 0.42.0"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Standard-orange.svg?style=flat-square" alt="MCP"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://pypi.org/project/agents-browser/"><img src="https://img.shields.io/pypi/v/agents-browser.svg?style=flat-square" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License"></a>
</p>

**Ultra-fast, zero-Node Python CDP Browser MCP for AI coding agents.**  
Connects directly to your local Chrome, Edge, or Brave instance via native Chrome DevTools Protocol. Shared across **Cursor**, **Claude Code**, **Antigravity**, and **Zed**.

---

## Why `.agents/browser`?

Traditional browser automation MCPs (Playwright, Puppeteer) introduce massive friction:
- Download ~300MB Chromium binaries that hog disk space
- Spin up heavy Node.js runtimes that leave detached zombie processes
- Lack access to existing user sessions, cookies, and saved logins
- Dump 100k+ tokens of raw bloated HTML into LLM context windows

**`agents-browser` connects directly to your installed browser via native CDP:**
- **Zero Node.js / Zero 300MB Downloads:** Pure lightweight Python (`FastMCP` + `websockets`).
- **Indexed `@ref` Interactive Snapshots:** Generates clean markdown with compact element references (`[@1] Button: Login`, `[@2] Input: Search`).
- **High-Level Built-in Tools:** Web search, clean reader-mode extraction, table scraping, batch form filling.
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
 │              LOCAL BROWSER (Chrome / Edge / Brave)          │
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

---

## CLI Reference

| Command | Purpose |
|---------|---------|
| `agents-browser init` | Plug & Play setup: auto-configures MCP across Cursor, Antigravity, Claude Desktop, Zed |
| `agents-browser open <URL>` | Navigates the browser to the specified URL |
| `agents-browser search "<query>"` | Performs a web search and prints top 10 organic markdown results |
| `agents-browser read` | Extracts active web page in clean Reader Mode |
| `agents-browser snapshot` | Captures text outline with compact indexed `@ref` interactive elements |
| `agents-browser screenshot --out <file>` | Captures a full or viewport PNG screenshot |
| `agents-browser serve` | Runs the FastMCP stdio server (default) |

---

## MCP Tools Reference

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `browser_open` | `url`, `new_tab` (default: `false`) | Navigate active tab or spawn a new tab. |
| `browser_snapshot` | *None* | Extract clean text outline with indexed `@ref` element IDs (`@1`, `@2`). |
| `browser_click` | `target` | Click element by `@ref` (e.g. `@1`), CSS selector, or matching text. |
| `browser_type` | `target`, `text`, `clear`, `press_enter` | Focus and type text into input/textarea. |
| `browser_search` | `query`, `engine` (default: `"duckduckgo"`) | Direct web search returning top organic results with Title, URL, and Snippet. |
| `browser_read_article` | *None* | Extracts clean article markdown, stripping ads, navbars, and banners. |
| `browser_scrape` | `selector`, `mode` (`"text"`, `"table"`, `"links"`) | Structured data extraction from CSS selector. |
| `browser_fill_form` | `fields_json`, `submit_selector` | Batch fill form fields and submit in one call. |
| `browser_screenshot` | `full_page` (default: `false`) | Capture PNG screenshot as base64. |
| `browser_evaluate` | `script` | Execute arbitrary JavaScript in tab context. |
| `browser_tabs` | *None* | List active browser tabs with IDs and titles. |
| `browser_switch_tab` | `tab_id` | Switch active tab focus. |

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
- [`abi/CDP.md`](abi/CDP.md) — Chrome DevTools Protocol direct WebSocket implementation.

---

## Testing & Verification

Run the test suite:

```bash
python tests/run_all_tests.py
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
