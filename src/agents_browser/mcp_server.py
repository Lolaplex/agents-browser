"""FastMCP Server definitions for agents-browser."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

from mcp.server.fastmcp import FastMCP, Image

from . import __version__
from .cdp import CDPClient
from .updates import attach_mcp_update_notice

BROWSER_INSTRUCTIONS = (
    "agents-browser — minimal zero-Node headless CDP browser automation.\n"
    "- ALWAYS use agents-browser instead of Playwright/Puppeteer/Node or writing ad-hoc terminal scripts.\n"
    "- Headless by default (`--headless=new`). Only pass `visible=True` or `browser_system_open` when the human explicitly asks.\n"
    "- CHOOSE THE RIGHT TOOL PER USE CASE (Do not default to one flow for everything):\n"
    "  * Research & Reading: Use `browser_search(query)`, `browser_read_article()` (clean distraction-free Markdown), "
    "`browser_extract_pdf()`, or `browser_fetch()`. Zero DOM/snapshot overhead.\n"
    "  * Web Interaction & Forms: `browser_open` -> `browser_snapshot()` for compact `@1`, `@2` refs -> "
    "`browser_click`, `browser_type`, `browser_select`, or `browser_fill_form`. Use `browser_scroll(target='@1')` to bring elements into view.\n"
    "  * Data Scraping & Tables: `browser_scrape(mode='table'|'links'|'text')` for formatted output, and `browser_download()` for files.\n"
    "  * UI Testing & Local Dev (debug layout/frontend): Use `browser_audit()` for layout overflow & console error healthchecks, "
    "`browser_inspect` / `browser_get_styles` / `browser_get_layout` instead of raw JS eval, and `browser_set_viewport` for responsive tests.\n"
    "  * Visual Proofs & Demos: Use `browser_screenshot()` for static checks, and `browser_record(duration_sec=...)` or "
    "`browser_record_start()` / `browser_record_stop()` for animation/flow recordings."
)

BROWSER_RULES_BLOCK = f"<browser_rules>\n{BROWSER_INSTRUCTIONS}\n</browser_rules>"

mcp = FastMCP("agents-browser", instructions=BROWSER_INSTRUCTIONS)
attach_mcp_update_notice(mcp, "agents-browser", __version__)

_rules_delivered_in_process = False
_orig_add_tool = mcp.add_tool


def _add_tool_with_rules(fn, *args, **kwargs):
    import functools
    import inspect

    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapped(*a, **kw):
            global _rules_delivered_in_process
            res = await fn(*a, **kw)
            if isinstance(res, str) and not _rules_delivered_in_process:
                _rules_delivered_in_process = True
                return f"{BROWSER_RULES_BLOCK}\n\n{res}"
            return res

        return _orig_add_tool(async_wrapped, *args, **kwargs)

    @functools.wraps(fn)
    def sync_wrapped(*a, **kw):
        global _rules_delivered_in_process
        res = fn(*a, **kw)
        if isinstance(res, str) and not _rules_delivered_in_process:
            _rules_delivered_in_process = True
            return f"{BROWSER_RULES_BLOCK}\n\n{res}"
        return res

    return _orig_add_tool(sync_wrapped, *args, **kwargs)


mcp.add_tool = _add_tool_with_rules  # type: ignore[method-assign]

_client: Optional[CDPClient] = None


def get_client() -> CDPClient:
    global _client
    if _client is None:
        _client = CDPClient()
    return _client


def screenshots_dir() -> Path:
    """Persistent screenshot dir under ~/.agents/browser/screenshots."""
    d = Path.home() / ".agents" / "browser" / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def downloads_dir() -> Path:
    """Persistent downloads dir under ~/.agents/browser/downloads."""
    d = Path.home() / ".agents" / "browser" / "downloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def recordings_dir() -> Path:
    """Persistent recordings dir under ~/.agents/browser/recordings."""
    d = Path.home() / ".agents" / "browser" / "recordings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_screenshot_path(path: str = "") -> Path:
    """Resolve output PNG path. Empty → timestamped file in screenshots_dir()."""
    if path.strip():
        out = Path(path).expanduser()
        if not out.is_absolute():
            out = screenshots_dir() / out.name
        return out
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return screenshots_dir() / f"shot-{stamp}.png"


@mcp.tool()
async def browser_open(url: str, new_tab: bool = False, visible: bool = False) -> str:
    """Navigate headless CDP browser to URL (or open in a new tab).

    PROACTIVE USAGE: ALWAYS call this tool (followed by `browser_snapshot`) when verifying web UIs,
    testing local dev servers, or inspecting live pages instead of using Playwright/Puppeteer.

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

    Use this ONLY when the human user explicitly asks to open or inspect a page in their personal desktop browser
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
    """Capture a clean text snapshot of the current page, headings, and interactive elements with index refs (@1, @2).

    PROACTIVE USAGE: Call immediately after `browser_open` or page navigation to inspect the DOM and obtain `@ref` targets.
    """
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
async def browser_screenshot(
    full_page: bool = False, path: str = ""
) -> str:
    """Capture a PNG screenshot, save it to disk, and return an Image for display.

    Always writes a real PNG file (default: ~/.agents/browser/screenshots/shot-<timestamp>.png).
    Returns a short path string plus FastMCP Image so the host can show the picture —
    not a giant base64 data-URL string.

    Parameters:
    - full_page: If true, capture the full scrollable page.
    - path: Optional output path. Relative names land in the screenshots dir.
    """
    try:
        client = get_client()
        b64 = await client.screenshot(full_page=full_page)
        if not b64:
            return "Error capturing screenshot: empty image data"
        out = resolve_screenshot_path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(b64))
        return f"Screenshot saved: {out}"
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
async def browser_scroll(direction: str = "down", amount: int = 400, target: Optional[str] = None) -> str:
    """Scroll the active browser page, or scroll a specific target element smoothly into view.

    Parameters:
    - direction: 'down', 'up', 'top', or 'bottom' (used when target is not set).
    - amount: Pixel distance to scroll (for 'down'/'up', default 400).
    - target: Optional ref index (e.g. '@1'), CSS selector (e.g. '#pricing'), or text content to scroll into view.
    """
    try:
        client = get_client()
        return await client.scroll(direction=direction, amount=amount, target=target)
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




# --- Coder Evaluation, Inspection & Recording Tools ---


@mcp.tool()
async def browser_inspect(target: str) -> str:
    """Inspect an element in full detail: Tag, Classes, Attributes, Text, Geometry, Typography, Colors, and Box-Model.

    PROACTIVE CODER USAGE: Call this tool instead of writing custom `browser_evaluate` JavaScript whenever you need
    to inspect element attributes, computed styling, visibility, or dimensions.

    Parameters:
    - target: Ref index (e.g. '@1'), CSS selector (e.g. '#header'), or visible text match.
    """
    try:
        client = get_client()
        return await client.inspect(target)
    except Exception as e:
        return f"Error inspecting element: {e}"


@mcp.tool()
async def browser_audit() -> str:
    """Run an automated developer quality audit of the active page.

    Detects:
    1. Uncaught console exceptions and console.error/warn logs.
    2. Horizontal layout overflow breaking mobile/desktop viewports (with offending elements).
    3. Broken images/media (failed to load or 0 natural width).
    4. Failed HTTP network requests (4xx/5xx).
    5. Active loaded web fonts.

    Returns a concise developer markdown report.
    """
    try:
        client = get_client()
        return await client.audit()
    except Exception as e:
        return f"Error running page audit: {e}"


@mcp.tool()
async def browser_get_styles(target: str, properties: Optional[List[str]] = None) -> str:
    """Inspect computed CSS styles and CSS variables of an element.

    Parameters:
    - target: Ref index (e.g. '@1'), CSS selector, or matching text.
    - properties: Optional list of CSS properties to inspect (e.g. ['font-family', 'color', 'background-color']).
                 If omitted, returns a comprehensive set of design tokens and declared CSS variables.
    """
    try:
        client = get_client()
        return await client.get_styles(target, properties=properties)
    except Exception as e:
        return f"Error getting styles: {e}"


@mcp.tool()
async def browser_get_layout(target: str) -> str:
    """Inspect element geometry (x, y, width, height, bounding box), scroll dimensions, and viewport visibility.

    Parameters:
    - target: Ref index (e.g. '@1'), CSS selector, or matching text.
    """
    try:
        client = get_client()
        return await client.get_layout(target)
    except Exception as e:
        return f"Error getting layout: {e}"


@mcp.tool()
async def browser_get_logs(log_type: str = "all", limit: int = 50, clear: bool = False) -> str:
    """Retrieve buffered browser console logs, uncaught exceptions, and failed network requests.

    Parameters:
    - log_type: 'all' (default), 'console', 'error', or 'network'.
    - limit: Maximum number of recent log entries to return (default 50).
    - clear: If True, clears the log buffer after retrieval.
    """
    try:
        client = get_client()
        return await client.get_logs(log_type=log_type, limit=limit, clear=clear)
    except Exception as e:
        return f"Error retrieving logs: {e}"


@mcp.tool()
async def browser_set_viewport(
    width: int = 1280,
    height: int = 900,
    preset: str = "",
    mobile: bool = False,
) -> str:
    """Set browser viewport dimensions or apply standard device presets for responsive testing.

    Presets:
    - 'mobile' / 'iphone': 390x844 (mobile emulation, 3x scale)
    - 'tablet' / 'ipad': 820x1180 (mobile emulation, 2x scale)
    - 'desktop' / 'laptop': 1440x900
    - 'fhd' / 'desktop-wide': 1920x1080

    Parameters:
    - width: Custom viewport width in pixels (default 1280).
    - height: Custom viewport height in pixels (default 900).
    - preset: Optional preset name overriding custom width/height.
    - mobile: Whether to emulate a mobile device touch screen.
    """
    try:
        client = get_client()
        return await client.set_viewport(width=width, height=height, preset=preset, mobile=mobile)
    except Exception as e:
        return f"Error setting viewport: {e}"


@mcp.tool()
async def browser_record(duration_sec: float = 5.0, fps: int = 15, path: str = "") -> str:
    """Record screen activity on the active tab for a given duration and export to MP4 video (or GIF).

    Captures high-fidelity CDP screencast frames and encodes them using local ffmpeg into a video file
    under ~/.agents/browser/recordings/ (or custom path).

    Parameters:
    - duration_sec: Recording duration in seconds (default 5.0).
    - fps: Frame rate between 1 and 30 (default 15).
    - path: Optional destination file path (.mp4 or .gif).
    """
    try:
        client = get_client()
        return await client.record(duration_sec=duration_sec, fps=fps, path=path)
    except Exception as e:
        return f"Error recording screen: {e}"


@mcp.tool()
async def browser_record_start(fps: int = 15) -> str:
    """Start capturing an interactive screen recording session.

    Call this before performing clicks, navigation, or scrolling.
    Call `browser_record_stop` when finished to export the MP4 video.

    Parameters:
    - fps: Frame rate between 1 and 30 (default 15).
    """
    try:
        client = get_client()
        return await client.record_start(fps=fps)
    except Exception as e:
        return f"Error starting screen recording: {e}"


@mcp.tool()
async def browser_record_stop(path: str = "") -> str:
    """Stop active screen recording session and encode captured frames into an MP4 video (or GIF).

    Parameters:
    - path: Optional destination file path (.mp4 or .gif). Defaults to timestamped file in ~/.agents/browser/recordings/.
    """
    try:
        client = get_client()
        return await client.record_stop(path=path)
    except Exception as e:
        return f"Error stopping screen recording: {e}"


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


@mcp.tool()
async def browser_download(ref_or_url: str = "", dest_path: str = "") -> str:
    """Download a file by clicking an element (via '@ref', CSS selector, or text) or triggering a URL download.

    Uses CDP Browser.setDownloadBehavior to intercept the download into a controlled directory and monitors
    Page.downloadWillBegin and Page.downloadProgress until completion, returning the exact local file path.

    Parameters:
    - ref_or_url: Element '@ref' (e.g. '@1'), button selector, text, or a direct download URL.
    - dest_path: Optional local destination file or directory path (defaults to ~/.agents/browser/downloads/).
    """
    try:
        client = get_client()
        return await client.download(ref_or_url=ref_or_url, dest_path=dest_path)
    except Exception as e:
        return f"Error downloading file: {e}"


@mcp.tool()
async def browser_fetch(
    url: str,
    method: str = "GET",
    headers: Optional[Union[str, dict]] = None,
    json_data: Optional[Union[str, dict, list]] = None,
    body: Optional[str] = None,
    json: Optional[Union[str, dict, list]] = None,
) -> str:
    """Execute a fast HTTP/REST request bypassing DOM and rendering, using browser session cookies when available.

    Use this for REST APIs, DOI resolvers, OpenAlex, or JSON endpoints to avoid full browser page navigation overhead.

    Parameters:
    - url: API endpoint or webpage URL.
    - method: HTTP method (GET, POST, PUT, DELETE, PATCH, default 'GET').
    - headers: Optional dict or JSON string of HTTP headers.
    - json_data: Optional JSON payload (dict, list, or JSON string) for request body.
    - body: Optional raw string body for non-JSON requests.
    - json: Alias for json_data.
    """
    try:
        client = get_client()
        payload = json if json is not None else json_data
        return await client.fetch(url=url, method=method, headers=headers, body=body, json_data=payload)
    except Exception as e:
        return f"Error executing fetch: {e}"


@mcp.tool()
async def browser_extract_pdf(url_or_ref: str = "", save_path: str = "", max_pages: int = 20) -> str:
    """Directly extract PDF streams, convert pages via Page.printToPDF or extract Chrome PDF Viewer blobs.

    Extracts the binary PDF file to disk and returns structured text content and page counts.

    Parameters:
    - url_or_ref: PDF URL, link '@ref' (e.g. '@2'), or empty string to extract/print current browser page.
    - save_path: Optional local destination path for the saved PDF file.
    - max_pages: Maximum number of pages to include in text preview (default 20).
    """
    try:
        client = get_client()
        return await client.extract_pdf(url_or_ref=url_or_ref, save_path=save_path, max_pages=max_pages)
    except Exception as e:
        return f"Error extracting PDF: {e}"


# Auto-trace all tool calls to ~/.agents/traces/ if agents-traces is installed
try:
    from agents_traces import auto_trace_mcp
    auto_trace_mcp(mcp)
except Exception:
    pass
