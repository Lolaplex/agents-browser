# Project: agents-browser

**Role:** Minimal, zero-Node Chrome DevTools Protocol (CDP) Browser MCP for AI coding assistants.
**Stack:** Python, FastMCP, WebSockets, CDP

## Key Concepts
- Connects directly to local Chrome/Edge/Brave instances via port 9222.
- Zero Playwright/Puppeteer, Zero Node.js runtime, Zero 300MB Chromium download.
- **Headless by default** (`--headless=new`). All CDP tools work without a window.
- Visible window only on explicit ask: `browser_open(..., visible=True)` or `browser_set_headless(False)`.
- Personal OS browser: `browser_system_open` only when human asks to open in their desktop browser.
- Fast snapshots with indexed `@ref` IDs (`@1`, `@2`) for interactive elements.
- Built-in high level actions: `browser_search`, `browser_read_article`, `browser_scrape`, `browser_fill_form`.
- Persistent sessions: uses `~/.agents/browser` or attaches to running debug browser.
- Override: `AGENTS_BROWSER_HEADLESS=0` forces visible CDP launches.

## Install & Sync
```bash
pip install -e .
python -m agents_browser sync --init
```
