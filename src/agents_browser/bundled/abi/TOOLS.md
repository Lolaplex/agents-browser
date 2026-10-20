# ABI: Tools Reference

| Tool | Signature | Purpose |
| --- | --- | --- |
| `browser_open` | `(url: str, new_tab: bool = False, visible: bool = False) -> str` | Navigates to a URL (headless by default, visible if requested) |
| `browser_system_open` | `(url: str) -> str` | Opens URL in user's OS default desktop browser (Floorp, Firefox, Chrome, Edge) |
| `browser_set_headless` | `(headless: bool = True) -> str` | Toggles background headless mode (True = background, False = window) |
| `browser_snapshot` | `() -> str` | Captures structural text & indexed `@ref` interactive elements |
| `browser_click` | `(target: str) -> str` | Clicks by `@ref` (e.g. `@1`), CSS selector, or visible text |
| `browser_type` | `(target: str, text: str, clear: bool = False, press_enter: bool = False) -> str` | Types text into input or textarea |
| `browser_select` | `(target: str, value: str) -> str` | Selects dropdown `<select>` option by text/value/index |
| `browser_scroll` | `(direction: str = "down", amount: int = 400, target: Optional[str] = None) -> str` | Scrolls page ('down', 'up', 'top', 'bottom'), or scrolls a target element into view |
| `browser_go_back` | `() -> str` | Navigates back in history |
| `browser_reload` | `(ignore_cache: bool = False) -> str` | Reloads current page |
| `browser_wait_stable` | `(timeout_ms: int = 8000, quiet_ms: int = 500) -> str` | Waits for network/DOM quiet state |
| `browser_find` | `(query: str, forward: bool = True, match_case: bool = False) -> str` | Searches text occurrences without loading full text |
| `browser_search` | `(query: str, engine: str = "duckduckgo") -> str` | Direct organic web search with structured results in one call |
| `browser_read_article` | `() -> str` | Clean Reader-Mode markdown of the primary article |
| `browser_scrape` | `(selector: str = "body", mode: str = "text") -> str` | Structured CSS scraping (`text`, `table`, `links`, `html`) |
| `browser_fill_form` | `(fields_json: str, submit_selector: str = "") -> str` | Batch form filling and submission |
| `browser_screenshot` | `(full_page: bool = False, path: str = "") -> str` | Saves PNG under `~/.agents/browser/screenshots/` (or `path`) and returns path text + FastMCP `Image` for display |
| `browser_evaluate` | `(script: str) -> str` | Executes JavaScript expression |
| `browser_tabs` | `() -> str` | Lists active browser tabs |
| `browser_switch_tab` | `(tab_id: str) -> str` | Switches active focus to another tab |
| `browser_download` | `(ref_or_url: str = "", dest_path: str = "") -> str` | Intercepts & monitors CDP downloads via element click or URL, returning exact local path |
| `browser_fetch` | `(url: str, method: str = "GET", headers: Optional[str \| dict] = None, json_data: Optional[Any] = None, body: Optional[str] = None) -> str` | Fast HTTP/REST request bypassing DOM, using browser session cookies |
| `browser_extract_pdf` | `(url_or_ref: str = "", save_path: str = "", max_pages: int = 20) -> str` | Extracts PDF streams via Chrome PDF Viewer or Page.printToPDF with text preview and page count |
| `browser_inspect` | `(target: str) -> str` | Detailed element inspection: Tag, Attributes, Text, Geometry, Typography, Colors, Box-Model |
| `browser_audit` | `() -> str` | Automated developer quality audit (console errors, layout overflow, broken media, network failures, fonts) |
| `browser_get_styles` | `(target: str, properties: Optional[List[str]] = None) -> str` | Inspects computed CSS properties and declared CSS custom variables |
| `browser_get_layout` | `(target: str) -> str` | Inspects bounding box (x, y, w, h), scroll metrics, and viewport visibility/overflow |
| `browser_get_logs` | `(log_type: str = "all", limit: int = 50, clear: bool = False) -> str` | Retrieves buffered console logs, uncaught exceptions, and failed HTTP network requests |
| `browser_set_viewport` | `(width: int = 1280, height: int = 900, preset: str = "", mobile: bool = False) -> str` | Sets viewport dimensions or applies presets ('mobile', 'tablet', 'desktop', 'fhd') |
| `browser_record` | `(duration_sec: float = 5.0, fps: int = 15, path: str = "") -> str` | Records screen activity on the active tab for N seconds and exports to MP4/GIF |
| `browser_record_start` | `(fps: int = 15) -> str` | Begins interactive screen recording session |
| `browser_record_stop` | `(path: str = "") -> str` | Stops recording session and encodes frames to MP4 video (or GIF) |
