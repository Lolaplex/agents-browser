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
- **No browser on host?** `agents-browser install` downloads chrome-headless-shell (~100MB, Chrome for Testing) into `<host>/browser/bin/` — opt-in, never bundled. `--full` fetches the full `chrome` binary (required for visible mode). Debian servers: `apt install chromium` works too (found via `which`).
- **Lite mode** (default, `AGENTS_BROWSER_LITE=0` disables): blocks image/font/media requests on navigations to cut RAM. Auto-off when `browser_screenshot`/`browser_audit`/`browser_record`/visible mode runs (reloads for real pixels). Toggle mid-session: `browser_lite`.
- Containers (small `/dev/shm`): `--disable-dev-shm-usage` is added automatically when detected.

## Install & Sync
```bash
pip install -e .
python -m agents_browser sync --init
```
