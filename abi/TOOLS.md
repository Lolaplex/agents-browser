# ABI: Tools Reference

| Tool | Signature | CLI Equivalent | Purpose |
| --- | --- | --- | --- |
| `browser_open` | `(url: str, new_tab: bool = False, visible: bool = False) -> str` | `agents-browser open <url> [--new-tab] [--visible]` | Navigates to a URL (headless by default, visible if requested) |
| `browser_system_open` | `(url: str) -> str` | `agents-browser system-open <url>` | Opens URL in user's OS default desktop browser (Floorp, Firefox, Chrome, Edge) |
| `browser_set_headless` | `(headless: bool = True) -> str` | `agents-browser headless [on\|off]` | Toggles background headless mode (True = background, False = window) |
| `browser_snapshot` | `(interactive_only: bool = False, diff: bool = False) -> str` | `agents-browser snapshot [-i] [-d]` | Captures structural text & indexed `@ref` interactive elements (or diff/interactive-only) |
| `browser_click` | `(target: str, force: bool = False) -> str` | `agents-browser click <target> [--force]` | Clicks by `@ref` (e.g. `@1`), CSS selector, or visible text (with hit-test occlusion check) |
| `browser_type` | `(target: str, text: str, clear: bool = False, press_enter: bool = False) -> str` | `agents-browser type <target> <text> [--clear] [--enter]` | Types text into input or textarea |
| `browser_select` | `(target: str, value: str) -> str` | `agents-browser select <target> <value>` | Selects dropdown `<select>` option by text/value/index |
| `browser_scroll` | `(direction: str = "down", amount: int = 400, target: Optional[str] = None) -> str` | `agents-browser scroll [direction\|@ref] [amount]` | Scrolls page ('down', 'up', 'top', 'bottom'), or scrolls a target element into view |
| `browser_go_back` | `() -> str` | `agents-browser back` | Navigates back in history |
| `browser_reload` | `(ignore_cache: bool = False) -> str` | `agents-browser reload [--ignore-cache]` | Reloads current page |
| `browser_wait_stable` | `(timeout_ms: int = 8000, quiet_ms: int = 500) -> str` | `agents-browser wait` | Waits for network/DOM quiet state |
| `browser_find` | `(query: str, forward: bool = True, match_case: bool = False) -> str` | `agents-browser find <query>` | Searches text occurrences without loading full text |
| `browser_search` | `(query: str, engine: str = "duckduckgo") -> str` | `agents-browser search <query>` | Direct organic web search with structured results in one call |
| `browser_read_article` | `() -> str` | `agents-browser read` | Clean Reader-Mode markdown of the primary article |
| `browser_scrape` | `(selector: str = "body", mode: str = "text") -> str` | `agents-browser scrape [selector] [--mode <mode>]` | Structured CSS scraping (`text`, `table`, `links`, `html`) |
| `browser_fill_form` | `(fields_json: str, submit_selector: str = "") -> str` | `agents-browser fill '<json>' [--submit <ref>]` | Batch form filling and submission |
| `browser_screenshot` | `(full_page: bool = False, path: str = "") -> str` | `agents-browser screenshot [path] [--full-page]` | Saves PNG under `~/.agents/browser/screenshots/` (or `path`) and returns path text |
| `browser_evaluate` | `(script: str) -> str` | `agents-browser eval <script>` | Executes JavaScript expression |
| `browser_tabs` | `() -> str` | `agents-browser tabs` | Lists active browser tabs |
| `browser_switch_tab` | `(tab_id: str) -> str` | `agents-browser switch-tab <tab_id>` | Switches active focus to another tab |
| `browser_download` | `(ref_or_url: str = "", dest_path: str = "") -> str` | `agents-browser download <target> [--dest <path>]` | Intercepts & monitors CDP downloads via element click or URL, returning exact local path |
| `browser_fetch` | `(url: str, method: str = "GET", headers: Optional[str \| dict] = None, json_data: Optional[Any] = None, body: Optional[str] = None) -> str` | `agents-browser fetch <url> [--method <m>] [--data <d>]` | Fast HTTP/REST request bypassing DOM, using browser session cookies |
| `browser_extract_pdf` | `(url_or_ref: str = "", save_path: str = "", max_pages: int = 20) -> str` | `agents-browser extract-pdf [target] [--out <path>]` | Extracts PDF streams via Chrome PDF Viewer or Page.printToPDF with text preview and page count |
| `browser_inspect` | `(target: str) -> str` | `agents-browser inspect <target>` | Detailed element inspection: Tag, Attributes, Text, Geometry, Typography, Colors, Box-Model |
| `browser_audit` | `() -> str` | `agents-browser audit` | Automated developer quality audit (console errors, layout overflow, broken media, network failures, fonts) |
| `browser_get_styles` | `(target: str, properties: Optional[List[str]] = None) -> str` | `agents-browser styles <target> [--props <p>]` | Inspects computed CSS properties and declared CSS custom variables |
| `browser_get_layout` | `(target: str) -> str` | `agents-browser layout <target>` | Inspects bounding box (x, y, w, h), scroll metrics, and viewport visibility/overflow |
| `browser_get_logs` | `(log_type: str = "all", limit: int = 50, clear: bool = False) -> str` | `agents-browser logs [--type <t>] [--limit <n>]` | Retrieves buffered console logs, uncaught exceptions, and failed HTTP network requests |
| `browser_set_viewport` | `(width: int = 1280, height: int = 900, preset: str = "", mobile: bool = False) -> str` | `agents-browser viewport [preset\|width] [height]` | Sets viewport dimensions or applies presets ('mobile', 'tablet', 'desktop', 'fhd') |
| `browser_record` | `(duration_sec: float = 5.0, fps: int = 15, path: str = "") -> str` | `agents-browser record [--duration <s>] [--out <p>]` | Records screen activity on the active tab for N seconds and exports to MP4/GIF |
| `browser_record_start` | `(fps: int = 15) -> str` | *MCP Interactive* | Begins interactive screen recording session |
| `browser_record_stop` | `(path: str = "") -> str` | *MCP Interactive* | Stops recording session and encodes frames to MP4 video (or GIF) |
