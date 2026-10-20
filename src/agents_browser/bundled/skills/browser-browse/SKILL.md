---
name: browser-browse
description: Control local Chrome/Edge browser via agents-browser MCP. Headless CDP by default. Task-adaptive tools for research, automation, scraping, UI audits, and screencasts without Playwright or Node overhead.
---

# Browser Browse Skill

Use this skill when interacting with web pages, researching content, testing local/remote web applications, scraping data, or recording screen activity using `agents-browser`.

## Headless Default (Critical)

- **Default mode is headless** (`--headless=new`). All CDP tools work without a visible window.
- Do **not** open a visible browser unless the human explicitly asks (e.g. "zeig Fenster", "visible", "open in my browser").
- Stay headless for automate / scrape / search / snapshot / screenshot / click / type / audit / record.
- Visible CDP window only via `browser_open(url, visible=True)` or `browser_set_headless(False)`.
- Personal OS browser (Floorp/Firefox/Chrome with their cookies) only via `browser_system_open(url)` when human asks to open in *their* desktop browser.

## Task-Adaptive Execution Guide (Choose Tools by Task)

Do not force a single rigid workflow for every task. Choose the most direct tools depending on what the user actually wants:

### 1. Research, Reading & Docs
*When the goal is finding information, reading articles, or reviewing documentation:*
- **Fast Search**: `browser_search(query="...")` for instant top-10 organic results without browser hopping.
- **Clean Reading**: `browser_open(url)` $\rightarrow$ `browser_read_article()`. Strips navbars, ads, footers and returns clean markdown. Do not waste tokens inspecting the DOM.
- **PDF Documents**: `browser_extract_pdf(url_or_ref="...")` to extract text preview and download PDF directly.
- **Fast JSON/REST API**: `browser_fetch(url, method="GET")` to fetch data using browser session cookies without DOM overhead.

### 2. Interaction & Web Automation
*When the goal is logging in, clicking buttons, filling forms, or navigating web apps:*
- **Scan & Target**: `browser_open(url)` $\rightarrow$ `browser_snapshot()` to obtain compact `@1`, `@2` element refs.
- **Act**: `browser_click("@1")` or `browser_type("@2", "text", press_enter=True)`.
- **Dropdowns & Forms**: `browser_select("@3", "value")` or batch fill with `browser_fill_form(fields_json='{"@1": "user", "@2": "pass"}', submit_selector="@3")`.
- **Bring into View**: `browser_scroll(target="@1" or "#submit")` to scroll directly to the element.
- **Wait for Quiet**: `browser_wait_stable()` if async network requests or animations are running.

### 3. Data Scraping & Tables
*When the goal is extracting tabular data, link catalogs, or structured text:*
- Use `browser_scrape(selector="table", mode="table")` for direct Markdown table output.
- Modes: `table` (Markdown tables), `links` (Markdown links), `text` (clean text), `html` (raw markup).
- **Files/Assets**: `browser_download(ref_or_url="@1", dest_path="...")` to download directly to a local directory.

### 4. UI Testing & Frontend Development
*When the goal is verifying local dev servers (`localhost:5173`, etc.), fixing CSS, or debugging layouts:*
- **Page Healthcheck**: `browser_open(url)` $\rightarrow$ `browser_audit()` to check for:
  * Uncaught console errors & warnings
  * Horizontal layout overflow (identifies the exact element overflowing the viewport)
  * Broken images (`naturalWidth === 0`)
  * Failed 4xx/5xx network requests
  * Loaded web fonts
- **Element Inspection**: `browser_inspect("@1")` or `browser_get_styles("@1")` / `browser_get_layout("@1")`. Never write ad-hoc `browser_evaluate` JavaScript just to read bounding boxes or computed styles.
- **Responsive Breakpoints**: `browser_set_viewport(preset="mobile"|"tablet"|"desktop")`.
- **Runtime Errors**: `browser_get_logs(log_type="error")`.

### 5. Visual Proofs & Demos
*When the human wants to see visual evidence of a bug, styling, or workflow:*
- **Static Screenshots**: `browser_screenshot(full_page=False, path="")`.
- **Dynamic Recordings**: `browser_record(duration_sec=5.0)` for a one-shot video of animations/hover effects, or `browser_record_start()` $\rightarrow$ perform actions $\rightarrow$ `browser_record_stop()` for multi-step workflow videos.

---

## Tool Cheat Sheet

| Category | Tool | Common Usage |
| --- | --- | --- |
| **Navigation** | `browser_open(url, visible=False)` | Headless navigation (handles auto-consent & downloads) |
| | `browser_system_open(url)` | User's desktop OS browser (only on explicit ask) |
| | `browser_set_headless(True\|False)` | Switch background headless mode |
| | `browser_go_back()`, `browser_reload()` | History navigation & hard refresh |
| **Research** | `browser_search(query)` | Organic web search results in one call |
| | `browser_read_article()` | Extract reader-mode clean markdown |
| | `browser_extract_pdf(url_or_ref)` | Extract PDF stream/text and save file |
| | `browser_fetch(url, method)` | Fast REST API call using browser cookies |
| **Automation** | `browser_snapshot()` | Indexed text tree with `@1`, `@2` refs |
| | `browser_click(target)` | Click by `@ref`, selector, or text |
| | `browser_type(target, text)` | Type into input or textarea |
| | `browser_select(target, value)` | Select dropdown `<select>` option |
| | `browser_fill_form(fields_json)` | Batch form fill and submit |
| | `browser_scroll(direction, amount, target)` | Smooth scroll or scroll target into view |
| | `browser_wait_stable()` | Wait for network/DOM quiet state |
| **Scraping** | `browser_scrape(selector, mode)` | Extract `table`, `links`, `text`, or `html` |
| | `browser_download(ref_or_url)` | Intercept and monitor file downloads |
| **UI Testing** | `browser_audit()` | 1-click check: console errors, overflow, broken media |
| | `browser_inspect(target)` | Full element card: tag, attrs, geometry, typo, box-model |
| | `browser_get_styles(target, props)` | Computed CSS properties and CSS variables |
| | `browser_get_layout(target)` | Bounding box, scroll metrics, visibility |
| | `browser_get_logs(log_type)` | Console logs, uncaught exceptions, network errors |
| | `browser_set_viewport(preset)` | Responsive breakpoints ('mobile', 'tablet', 'desktop') |
| **Visuals** | `browser_screenshot(full_page, path)` | Save PNG screenshot |
| | `browser_record(duration_sec)` | One-shot MP4/GIF screencast recording |
| | `browser_record_start()` / `stop()` | Multi-step interactive workflow recording |
