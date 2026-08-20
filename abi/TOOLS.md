# ABI: Tools Reference

| Tool | Signature | Purpose |
| --- | --- | --- |
| `browser_open` | `(url: str, new_tab: bool = False) -> str` | Navigates to a URL |
| `browser_snapshot` | `() -> str` | Captures structural text & indexed `@ref` interactive elements |
| `browser_click` | `(target: str) -> str` | Clicks by `@ref` (e.g. `@1`), CSS selector, or visible text |
| `browser_type` | `(target: str, text: str, clear: bool = False, press_enter: bool = False) -> str` | Types text into input or textarea |
| `browser_search` | `(query: str, engine: str = "duckduckgo") -> str` | Direct organic web search with structured results in one call |
| `browser_read_article` | `() -> str` | Clean Reader-Mode markdown of the primary article |
| `browser_scrape` | `(selector: str = "body", mode: str = "text") -> str` | Structured CSS scraping (`text`, `table`, `links`, `html`) |
| `browser_fill_form` | `(fields_json: str, submit_selector: str = "") -> str` | Batch form filling and submission |
| `browser_screenshot` | `(full_page: bool = False) -> str` | Captures PNG base64 screenshot |
| `browser_evaluate` | `(script: str) -> str` | Executes JavaScript expression |
| `browser_tabs` | `() -> str` | Lists active browser tabs |
| `browser_switch_tab` | `(tab_id: str) -> str` | Switches active focus to another tab |
