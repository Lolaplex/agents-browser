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
| `browser_scroll` | `(direction: str = "down", amount: int = 400) -> str` | Scrolls page ('down', 'up', 'top', 'bottom') |
| `browser_go_back` | `() -> str` | Navigates back in history |
| `browser_reload` | `(ignore_cache: bool = False) -> str` | Reloads current page |
| `browser_wait_stable` | `(timeout_ms: int = 8000, quiet_ms: int = 500) -> str` | Waits for network/DOM quiet state |
| `browser_find` | `(query: str, forward: bool = True, match_case: bool = False) -> str` | Searches text occurrences without loading full text |
| `browser_search` | `(query: str, engine: str = "duckduckgo") -> str` | Direct organic web search with structured results in one call |
| `browser_read_article` | `() -> str` | Clean Reader-Mode markdown of the primary article |
| `browser_scrape` | `(selector: str = "body", mode: str = "text") -> str` | Structured CSS scraping (`text`, `table`, `links`, `html`) |
| `browser_fill_form` | `(fields_json: str, submit_selector: str = "") -> str` | Batch form filling and submission |
| `browser_screenshot` | `(full_page: bool = False) -> str` | Captures PNG base64 screenshot |
| `browser_evaluate` | `(script: str) -> str` | Executes JavaScript expression |
| `browser_tabs` | `() -> str` | Lists active browser tabs |
| `browser_switch_tab` | `(tab_id: str) -> str` | Switches active focus to another tab |
