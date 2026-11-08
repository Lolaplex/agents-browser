---
name: browser-browse
description: Control local Chrome/Edge browser via agents-browser MCP or CLI. Headless CDP by default. Task-adaptive tools for research, automation, scraping, UI audits, and screencasts without Playwright or Node overhead.
---

# Browser Browse Skill

Use this skill when interacting with web pages, researching content, testing local/remote web applications, scraping data, or recording screen activity using `agents-browser` (works via **MCP tools** AND **standalone CLI commands**).

## Headless Default (Critical)

- **Default mode is headless** (`--headless=new`). All CDP tools work without a visible window.
- Do **not** open a visible browser unless the human explicitly asks (e.g. "zeig Fenster", "visible", "open in my browser").
- Stay headless for automate / scrape / search / snapshot / screenshot / click / type / audit / record.
- Visible CDP window only via `browser_open(url, visible=True)` / `agents-browser open <url> --visible` or `browser_set_headless(False)` / `agents-browser headless off`.
- Personal OS browser (Floorp/Firefox/Chrome with their cookies) only via `browser_system_open(url)` / `agents-browser system-open <url>` when human asks to open in *their* desktop browser.

## Standalone CLI Mode (When MCP is not used)

Every capability is available directly from the shell, preserving active tabs and `@ref` indices across separate commands:

```bash
agents-browser open https://example.com
agents-browser snapshot -i                  # compact interactive-only @refs (@1, @2)
agents-browser click @1                     # includes hit-test occlusion check
agents-browser snapshot -d                  # diff: only added/changed/removed @refs
agents-browser type @2 "hello" --enter
agents-browser fill '{"@1": "user", "@2": "pass"}' --submit @3
agents-browser audit                        # console errors, overflow, broken media
agents-browser close
```

Use `--session <name>` on any CLI command to run isolated parallel browser sessions.

## Task-Adaptive Execution Guide (Choose Tools by Task)

Do not force a single rigid workflow for every task. Choose the most direct tools depending on what the user actually wants:

### 1. Research, Reading & Docs
*When the goal is finding information, reading articles, or reviewing documentation:*
- **Fast Search**: `browser_search(query="...")` (`agents-browser search "..."`) for instant top-10 organic results without browser hopping.
- **Clean Reading**: `browser_open(url)` $\rightarrow$ `browser_read_article()` (`agents-browser read`). Strips navbars, ads, footers and returns clean markdown. Do not waste tokens inspecting the DOM.
- **PDF Documents**: `browser_extract_pdf(url_or_ref="...")` (`agents-browser extract-pdf ...`) to extract text preview and download PDF directly.
- **Fast JSON/REST API**: `browser_fetch(url, method="GET")` (`agents-browser fetch <url>`) to fetch data using browser session cookies without DOM overhead.

### 2. Interaction & Web Automation
*When the goal is logging in, clicking buttons, filling forms, or navigating web apps:*
- **Scan & Target**: `browser_open(url)` $\rightarrow$ `browser_snapshot(interactive_only=True)` (`agents-browser snapshot -i`) to obtain compact `@1`, `@2` element refs.
- **Act**: `browser_click("@1")` (`agents-browser click @1`) or `browser_type("@2", "text", press_enter=True)` (`agents-browser type @2 "text" --enter`).
- **Verify Delta**: `browser_snapshot(diff=True)` (`agents-browser snapshot -d`) to inspect only what changed after an action.
- **Dropdowns & Forms**: `browser_select("@3", "value")` or batch fill with `browser_fill_form(fields_json='{"@1": "user", "@2": "pass"}', submit_selector="@3")`.
- **Bring into View**: `browser_scroll(target="@1")` (`agents-browser scroll @1`) to scroll directly to the element.
- **Wait for Quiet**: `browser_wait_stable()` (`agents-browser wait`) if async network requests or animations are running.

### 3. Data Scraping & Tables
*When the goal is extracting tabular data, link catalogs, or structured text:*
- Use `browser_scrape(selector="table", mode="table")` (`agents-browser scrape table --mode table`) for direct Markdown table output.
- Modes: `table` (Markdown tables), `links` (Markdown links), `text` (clean text), `html` (raw markup).
- **Files/Assets**: `browser_download(ref_or_url="@1", dest_path="...")` (`agents-browser download @1 --dest ...`) to download directly to a local directory.

### 4. UI Testing & Frontend Development
*When the goal is verifying local dev servers (`localhost:5173`, etc.), fixing CSS, or debugging layouts:*
- **Page Healthcheck**: `browser_open(url)` $\rightarrow$ `browser_audit()` (`agents-browser audit`) to check for:
  * Uncaught console errors & warnings
  * Horizontal layout overflow (identifies the exact element overflowing the viewport)
  * Broken images (`naturalWidth === 0`)
  * Failed 4xx/5xx network requests
  * Loaded web fonts
- **Element Inspection**: `browser_inspect("@1")` (`agents-browser inspect @1`) or `browser_get_styles("@1")` (`agents-browser styles @1`) / `browser_get_layout("@1")` (`agents-browser layout @1`). Never write ad-hoc `browser_evaluate` JavaScript just to read bounding boxes or computed styles.
- **Responsive Breakpoints**: `browser_set_viewport(preset="mobile"|"tablet"|"desktop")` (`agents-browser viewport mobile`).
- **Runtime Errors**: `browser_get_logs(log_type="error")` (`agents-browser logs --type error`).

### 5. Visual Proofs & Demos
*When the human wants to see visual evidence of a bug, styling, or workflow:*
- **Static Screenshots**: `browser_screenshot(full_page=False, path="")` (`agents-browser screenshot`).
- **Dynamic Recordings**: `browser_record(duration_sec=5.0)` (`agents-browser record --duration 5`) for a one-shot video of animations/hover effects, or `browser_record_start()` $\rightarrow$ perform actions $\rightarrow$ `browser_record_stop()` for multi-step workflow videos.

---

## Tool Cheat Sheet (MCP & CLI Parity)

| Category | MCP Tool | CLI Equivalent | Purpose |
| --- | --- | --- | --- |
| **Navigation** | `browser_open(url, visible=False)` | `agents-browser open <url> [--visible]` | Headless navigation (auto-consent & downloads) |
| | `browser_system_open(url)` | `agents-browser system-open <url>` | User's desktop OS browser (only on explicit ask) |
| | `browser_set_headless(True\|False)` | `agents-browser headless on\|off` | Switch background headless mode |
| | `browser_go_back()`, `browser_reload()` | `agents-browser back`, `reload` | History navigation & hard refresh |
| | `browser_tabs()`, `browser_switch_tab(id)` | `agents-browser tabs`, `switch-tab <id>` | List and switch active browser tabs |
| **Research** | `browser_search(query)` | `agents-browser search "<query>"` | Organic web search results in one call |
| | `browser_read_article()` | `agents-browser read` | Extract reader-mode clean markdown |
| | `browser_extract_pdf(url_or_ref)` | `agents-browser extract-pdf [target]` | Extract PDF stream/text and save file |
| | `browser_fetch(url, method)` | `agents-browser fetch <url>` | Fast REST API call using browser cookies |
| **Automation** | `browser_snapshot(interactive_only, diff)` | `agents-browser snapshot [-i] [-d]` | Indexed text tree with `@1`, `@2` refs |
| | `browser_click(target, force=False)` | `agents-browser click <target> [--force]` | Click by `@ref`, selector, or text (hit-tested) |
| | `browser_type(target, text, clear, press_enter)` | `agents-browser type <target> "<text>" [--clear] [--enter]` | Type into input or textarea |
| | `browser_fill_form(fields_json, submit_selector)` | `agents-browser fill '<json>' [--submit @ref]` | Single or batch form fill and submit |
| | `browser_select(target, value)` | `agents-browser select <target> "<val>"` | Select dropdown `<select>` option |
| | `browser_scroll(direction, amount, target)` | `agents-browser scroll [dir\|@ref]` | Smooth scroll or scroll target into view |
| | `browser_wait_stable()` | `agents-browser wait` | Wait for network/DOM quiet state |
| | `browser_find(query)` | `agents-browser find "<query>"` | In-page text search & match count |
| **Scraping** | `browser_scrape(selector, mode)` | `agents-browser scrape [sel] --mode <m>` | Extract `table`, `links`, `text`, or `html` |
| | `browser_download(ref_or_url)` | `agents-browser download <target>` | Intercept and monitor file downloads |
| **UI Testing** | `browser_audit()` | `agents-browser audit` | 1-click check: console errors, overflow, media |
| | `browser_inspect(target)` | `agents-browser inspect <target>` | Full element card: tag, attrs, geometry, typo |
| | `browser_get_styles(target, props)` | `agents-browser styles <target>` | Computed CSS properties and CSS variables |
| | `browser_get_layout(target)` | `agents-browser layout <target>` | Bounding box, scroll metrics, visibility |
| | `browser_get_logs(log_type)` | `agents-browser logs [--type error]` | Console logs, uncaught exceptions, network |
| | `browser_set_viewport(preset)` | `agents-browser viewport <preset>` | Responsive breakpoints ('mobile', 'tablet', 'desktop') |
| | `browser_evaluate(script)` | `agents-browser eval "<js>"` | Execute JavaScript expression in active tab |
| **Visuals** | `browser_screenshot(full_page, path)` | `agents-browser screenshot [--full-page]` | Save PNG screenshot |
| | `browser_record(duration_sec)` | `agents-browser record [--duration 5]` | One-shot MP4/GIF screencast recording |
