---
name: browser-browse
description: Control local Chrome/Edge browser via agents-browser MCP. Headless CDP by default. Navigate, take interactive snapshots with @ref IDs, click, type, and screenshot without Playwright or heavy Node overhead.
---

# Browser Browse Skill

Use this skill when interacting with web pages, testing web applications, or automating browser tasks using `agents-browser`.

## Headless Default (Critical)

- **Default mode is headless** (`--headless=new`). All CDP tools work without a visible window.
- Do **not** open a visible browser unless the human explicitly asks (e.g. "zeig Fenster", "visible", "open in my browser").
- Stay headless for automate / scrape / search / snapshot / screenshot / click / type.
- Visible CDP window only via `browser_open(url, visible=True)` or `browser_set_headless(False)`.
- Personal OS browser (Floorp/Firefox/Chrome with their cookies) only via `browser_system_open(url)` when human asks to open in *their* desktop browser.

## Strict Execution Principles (Anti-Loop & Fast Execution)

1. **Never URL-Hop**:
   - Do NOT try 4 different domains or repeat `browser_open` in a loop.
   - Choose one definitive URL (or use `browser_search(query)`) and stay on that page.

2. **Auto-Consent is Active**:
   - Cookie banners and GDPR overlays are automatically dismissed by the MCP server.
   - Do not waste tool turns searching for accept buttons.

3. **Fast 2-Turn Execution Loop**:
   - **Turn 1 (Open & Scan)**: `browser_open(url)` $\rightarrow$ `browser_snapshot()`.
   - **Turn 2 (Act & Verify)**: `browser_click("@ref")` or `browser_type("@ref", "query", press_enter=True)` $\rightarrow$ `browser_screenshot()`.
   - Done. Return results immediately.

## Tool Cheat Sheet

| Action | Tool Call | Notes |
| --- | --- | --- |
| Navigate (headless) | `browser_open(url="...")` | Default. No window. Auto-dismisses cookies |
| Navigate (visible) | `browser_open(url="...", visible=True)` | Only if human asks for a window |
| System browser | `browser_system_open(url="...")` | OS default browser; only on explicit ask |
| Toggle mode | `browser_set_headless(True\|False)` | Restart CDP browser headless/visible |
| Inspect | `browser_snapshot()` | Returns `@1`, `@2` element refs, headings, and clean text |
| Click | `browser_click(target="@1")` | Click by `@ref`, selector, or text |
| Type | `browser_type(target="@2", text="...", press_enter=True)` | Focuses & inputs text |
| Select | `browser_select(target="@3", value="Option")` | Selects dropdown `<select>` option by text/value |
| Scroll | `browser_scroll(direction="down", amount=400)` | Scroll page ('down', 'up', 'top', 'bottom') |
| Go Back | `browser_go_back()` | Navigates back in history |
| Reload | `browser_reload(ignore_cache=False)` | Reloads page |
| Wait Stable | `browser_wait_stable()` | Waits for network/DOM quiet state |
| In-Page Find | `browser_find(query="...")` | Search text occurrences without loading full text |
| Screenshot | `browser_screenshot(full_page=False)` | Captures current viewport PNG (works headless) |
| Fast Search | `browser_search(query="...")` | Instant top-10 search results without hopping |
| Reader Mode | `browser_read_article()` | Cleans page and returns readable markdown |
