"""FastMCP Server definitions for agents-browser."""

from __future__ import annotations

import json
from typing import Dict, Optional
from mcp.server.fastmcp import FastMCP
from .cdp import CDPClient

mcp = FastMCP("agents-browser")

_client: Optional[CDPClient] = None


def get_client() -> CDPClient:
    global _client
    if _client is None:
        _client = CDPClient()
    return _client


@mcp.tool()
async def browser_open(url: str, new_tab: bool = False, visible: bool = False) -> str:
    """Navigate browser to URL (or open in a new tab).

    Parameters:
    - url: Web page URL to navigate to.
    - new_tab: If True, opens in a new tab.
    - visible: If True, opens with a visible desktop window instead of headless background.
    """
    try:
        client = get_client()
        return await client.open(url, new_tab=new_tab, visible=visible)
    except Exception as e:
        return f"Error opening URL: {e}"


@mcp.tool()
async def browser_system_open(url: str) -> str:
    """Open a URL directly in the user's personal default operating system browser (e.g. Floorp, Firefox, Chrome, Edge).

    Use this when the human user explicitly asks to open or inspect a page in their personal desktop browser
    with their own saved logins, bookmarks, cookies, and extensions.
    """
    try:
        import webbrowser
        if not url.startswith(("http://", "https://", "file://", "about:")):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opened {url} in your desktop default browser."
    except Exception as e:
        return f"Error opening in system browser: {e}"


@mcp.tool()
async def browser_set_headless(headless: bool = True) -> str:
    """Toggle background headless mode for agents-browser automation.

    Parameters:
    - headless: True for silent, fast background operation without opening windows (default).
                False to launch and show a visible browser window on the desktop.
    """
    try:
        client = get_client()
        return await client.set_headless(headless)
    except Exception as e:
        return f"Error setting headless mode: {e}"


@mcp.tool()
async def browser_snapshot() -> str:
    """Capture a clean text snapshot of the current page, headings, and interactive elements with index refs (@1, @2)."""
    try:
        client = get_client()
        return await client.snapshot()
    except Exception as e:
        return f"Error capturing snapshot: {e}"


@mcp.tool()
async def browser_click(target: str) -> str:
    """Click an element by its ref index (e.g. '@1'), CSS selector (e.g. '#submit'), or visible text (e.g. 'Login')."""
    try:
        client = get_client()
        return await client.click(target)
    except Exception as e:
        return f"Error clicking element: {e}"


@mcp.tool()
async def browser_type(target: str, text: str, clear: bool = False, press_enter: bool = False) -> str:
    """Focus an input/textarea element and type text into it.

    Parameters:
    - target: Ref index (e.g. '@2'), CSS selector, or matching text.
    - text: Text string to input.
    - clear: If true, clear existing input content first.
    - press_enter: If true, simulate Enter key press / form submission after typing.
    """
    try:
        client = get_client()
        return await client.type_text(target, text, clear=clear, press_enter=press_enter)
    except Exception as e:
        return f"Error typing into element: {e}"


@mcp.tool()
async def browser_screenshot(full_page: bool = False) -> str:
    """Capture a PNG screenshot of the current page and return base64 encoded PNG."""
    try:
        client = get_client()
        b64 = await client.screenshot(full_page=full_page)
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        return f"Error capturing screenshot: {e}"


@mcp.tool()
async def browser_evaluate(script: str) -> str:
    """Execute raw JavaScript expression in the page context and return the result."""
    try:
        client = get_client()
        res = await client.evaluate(script)
        if isinstance(res, (dict, list)):
            return json.dumps(res, indent=2)
        return str(res)
    except Exception as e:
        return f"Error evaluating script: {e}"


@mcp.tool()
async def browser_tabs() -> str:
    """List open browser tabs and targets with their IDs, titles, and URLs."""
    try:
        client = get_client()
        tabs = await client.list_tabs()
        if not tabs:
            return "No open browser tabs."
        lines = ["Active Tabs:"]
        for t in tabs:
            lines.append(f"- [{t['id']}] {t['title']} ({t['url']}){t['active']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tabs: {e}"


@mcp.tool()
async def browser_select(target: str, value: str) -> str:
    """Select an option in a dropdown (<select>) element by option value, text, or substring match.

    Parameters:
    - target: Ref index (e.g. '@2'), CSS selector, or matching text of the select element.
    - value: Desired option value, full text, or partial text.
    """
    try:
        client = get_client()
        return await client.select(target, value)
    except Exception as e:
        return f"Error selecting option: {e}"


@mcp.tool()
async def browser_scroll(direction: str = "down", amount: int = 400) -> str:
    """Scroll the active browser page.

    Parameters:
    - direction: 'down', 'up', 'top', or 'bottom'
    - amount: Pixel distance to scroll (for 'down'/'up', default 400).
    """
    try:
        client = get_client()
        return await client.scroll(direction=direction, amount=amount)
    except Exception as e:
        return f"Error scrolling: {e}"


@mcp.tool()
async def browser_go_back() -> str:
    """Navigate back in browser history."""
    try:
        client = get_client()
        return await client.go_back()
    except Exception as e:
        return f"Error navigating back: {e}"


@mcp.tool()
async def browser_reload(ignore_cache: bool = False) -> str:
    """Reload the current browser page.

    Parameters:
    - ignore_cache: If true, forces a hard refresh ignoring browser cache.
    """
    try:
        client = get_client()
        return await client.reload(ignore_cache=ignore_cache)
    except Exception as e:
        return f"Error reloading page: {e}"


@mcp.tool()
async def browser_wait_stable(timeout_ms: int = 8000, quiet_ms: int = 500) -> str:
    """Wait for network requests (fetch/XHR) and DOM mutations to settle before continuing.

    Parameters:
    - timeout_ms: Maximum wait time in milliseconds (default 8000).
    - quiet_ms: Quiet duration in milliseconds required to consider page stable (default 500).
    """
    try:
        client = get_client()
        return await client.wait_stable(timeout_ms=timeout_ms, quiet_ms=quiet_ms)
    except Exception as e:
        return f"Error waiting for stability: {e}"


@mcp.tool()
async def browser_find(query: str, forward: bool = True, match_case: bool = False) -> str:
    """Search for text in page and return match stats and highlight position.

    Parameters:
    - query: Search text string.
    - forward: Search forward (True) or backward (False).
    - match_case: Case-sensitive search flag.
    """
    try:
        client = get_client()
        return await client.find_in_page(query=query, forward=forward, match_case=match_case)
    except Exception as e:
        return f"Error searching text: {e}"


@mcp.tool()
async def browser_switch_tab(tab_id: str) -> str:
    """Switch active focus to a specific tab ID from browser_tabs."""
    try:
        client = get_client()
        return await client.switch_tab(tab_id)
    except Exception as e:
        return f"Error switching tab: {e}"



# --- High-Level Built-in Scraper & Search Tools ---


@mcp.tool()
async def browser_search(query: str, engine: str = "duckduckgo") -> str:
    """Perform a web search and return structured top-10 organic results (Title, URL, Snippet) in one call."""
    try:
        client = get_client()
        return await client.search(query=query, engine=engine)
    except Exception as e:
        return f"Error searching: {e}"


@mcp.tool()
async def browser_read_article() -> str:
    """Extract clean Reader-Mode markdown of the primary article/content on the page, stripping navbars, footers, and ads."""
    try:
        client = get_client()
        return await client.read_article()
    except Exception as e:
        return f"Error reading article: {e}"


@mcp.tool()
async def browser_scrape(selector: str = "body", mode: str = "text") -> str:
    """Extract structured data from elements matching a CSS selector.

    Modes:
    - 'text': Cleans and returns textual content.
    - 'table': Formats HTML <table> into Markdown table.
    - 'links': Extracts all [title](url) links.
    - 'html': Returns outer HTML markup.
    """
    try:
        client = get_client()
        return await client.scrape(selector=selector, mode=mode)
    except Exception as e:
        return f"Error scraping selector '{selector}': {e}"


@mcp.tool()
async def browser_fill_form(fields_json: str, submit_selector: str = "") -> str:
    """Batch fill multiple form fields in one call and optionally submit.

    Parameters:
    - fields_json: JSON string mapping target ref/selector to value, e.g. '{"@1": "myuser", "@2": "mypass"}'
    - submit_selector: Optional CSS selector or @ref to click after filling (e.g. '@3' or '#submit').
    """
    try:
        client = get_client()
        fields = json.loads(fields_json)
        if not isinstance(fields, dict):
            return "Error: fields_json must be a JSON dictionary of {target: value}"
        return await client.fill_form(fields, submit_selector=submit_selector)
    except Exception as e:
        return f"Error batch filling form: {e}"


# Auto-trace all tool calls to ~/.agents/traces/ if agents-traces is installed
try:
    from agents_traces import auto_trace_mcp
    auto_trace_mcp(mcp)
except Exception:
    pass
