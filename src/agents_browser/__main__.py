"""CLI entrypoint for running agents-browser."""

from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime
import json
import sys
import warnings
from pathlib import Path

# Force UTF-8 on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from . import __version__


def _resolve_screenshot_path(path: str = "") -> Path:
    from .cdp import artifacts_dir
    d = artifacts_dir("screenshots")
    d.mkdir(parents=True, exist_ok=True)
    if path.strip():
        out = Path(path).expanduser()
        if not out.is_absolute():
            out = d / out.name
        return out
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return d / f"shot-{stamp}.png"


def main(argv: list[str] | None = None) -> None:
    raw_args = list(argv if argv is not None else sys.argv[1:])

    # Fast-path for --version / version and --help-json before heavy imports or network checks
    if raw_args and raw_args[0] in ("version", "-v", "--version"):
        print(f"agents-browser {__version__}")
        return
    if raw_args and raw_args[0] in ("help",):
        raw_args = ["--help"]

    if "--help-json" in raw_args:
        from .help_json import help_json

        print(json.dumps(help_json(), indent=2))
        return

    parser = argparse.ArgumentParser(
        prog="agents-browser",
        description="Minimal CDP Browser MCP & CLI for AI coding agents. Zero Node, zero 300MB downloads.",
    )
    parser.add_argument(
        "--help-json",
        action="store_true",
        help="Emit machine-readable CLI spec as JSON.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"agents-browser {__version__}",
    )
    parser.add_argument(
        "--session",
        default="",
        help="Optional isolated browser session name (uses isolated profile and port).",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve (default)
    subparsers.add_parser("serve", help="Run the FastMCP server over stdio (default)")

    # init (Plug & Play)
    subparsers.add_parser("init", help="Plug & Play setup: auto-configure MCP in all IDEs and sync skills")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Auto-configure MCP server across host IDEs and sync skills")
    sync_parser.add_argument("--init", action="store_true", help="Perform initial host IDE registration")

    # skills (on-demand CLI skill instructions for non-MCP agents)
    skills_parser = subparsers.add_parser("skills", help="Print agent skill instructions for CLI or MCP workflows")
    skills_parser.add_argument("name", nargs="?", default="core", help="Skill name ('core', 'browser-browse', 'browser-scrape', 'list')")

    # open
    open_parser = subparsers.add_parser("open", help="Open a URL in browser")
    open_parser.add_argument("url", help="URL to navigate to")
    open_parser.add_argument("--new-tab", action="store_true", help="Open URL in a new tab")
    open_parser.add_argument("--visible", action="store_true", help="Launch visible browser window instead of background headless")

    # system-open
    sys_parser = subparsers.add_parser("system-open", help="Open URL directly in default desktop browser (e.g. Floorp, Firefox, Chrome)")
    sys_parser.add_argument("url", help="URL to open in system default browser")

    # headless
    hl_parser = subparsers.add_parser("headless", help="Switch browser mode between headless background and visible window")
    hl_parser.add_argument("mode", nargs="?", default="on", choices=["on", "off", "true", "false", "1", "0"], help="'on'/'true' for headless, 'off'/'false' for visible window")

    # close
    subparsers.add_parser("close", help="Close the managed CDP browser instance")

    # snapshot
    snap_parser = subparsers.add_parser("snapshot", help="Capture page text outline with @ref interactive element indices")
    snap_parser.add_argument("-i", "--interactive", "--interactive-only", dest="interactive_only", action="store_true", help="Return only interactive @ref elements (saves ~70% tokens)")
    snap_parser.add_argument("-d", "--diff", action="store_true", help="Show only interactive elements added/changed/removed since last snapshot")

    # click
    click_parser = subparsers.add_parser("click", help="Click element by @ref (e.g. @1), CSS selector, or visible text")
    click_parser.add_argument("target", help="Target @ref, CSS selector, or visible text")
    click_parser.add_argument("--force", action="store_true", help="Bypass hit-test occlusion and disabled checks")

    # type
    type_parser = subparsers.add_parser("type", help="Focus input/textarea and type text")
    type_parser.add_argument("target", help="Target @ref, CSS selector, or matching text")
    type_parser.add_argument("text", help="Text string to type")
    type_parser.add_argument("--clear", action="store_true", help="Clear existing input value first")
    type_parser.add_argument("--enter", "--press-enter", dest="press_enter", action="store_true", help="Simulate Enter key press / submit after typing")

    # fill (single field clear+type or JSON batch fill)
    fill_parser = subparsers.add_parser("fill", help="Fill an input field (clears first) or batch-fill a JSON map of fields")
    fill_parser.add_argument("target_or_json", help="Target @ref/selector OR JSON dictionary '{\"@1\": \"val\"}'")
    fill_parser.add_argument("text", nargs="?", default=None, help="Text value when filling a single target")
    fill_parser.add_argument("--submit", default="", help="Optional submit button @ref or selector to click after batch fill")

    # select
    sel_parser = subparsers.add_parser("select", help="Select dropdown <select> option by value, text, or substring")
    sel_parser.add_argument("target", help="Target @ref or CSS selector of <select>")
    sel_parser.add_argument("value", help="Option value or visible text")

    # scroll
    scroll_parser = subparsers.add_parser("scroll", help="Scroll page ('down', 'up', 'top', 'bottom') or scroll target element into view")
    scroll_parser.add_argument("direction", nargs="?", default="down", help="Direction ('down', 'up', 'top', 'bottom') or target @ref/selector")
    scroll_parser.add_argument("amount", nargs="?", type=int, default=400, help="Pixel amount to scroll (default 400)")
    scroll_parser.add_argument("--target", default="", help="Specific @ref, CSS selector, or text to scroll into view")

    # back
    subparsers.add_parser("back", help="Navigate back in browser history")

    # reload
    reload_parser = subparsers.add_parser("reload", help="Reload active page")
    reload_parser.add_argument("--ignore-cache", action="store_true", help="Force hard reload ignoring cache")

    # wait
    wait_parser = subparsers.add_parser("wait", help="Wait for network requests and DOM mutations to settle")
    wait_parser.add_argument("--timeout-ms", type=int, default=8000, help="Max timeout in milliseconds (default 8000)")
    wait_parser.add_argument("--quiet-ms", type=int, default=500, help="Quiet window in milliseconds (default 500)")

    # find
    find_parser = subparsers.add_parser("find", help="Search text in page and return match count")
    find_parser.add_argument("query", help="Search query string")
    find_parser.add_argument("--match-case", action="store_true", help="Case-sensitive match")

    # tabs
    subparsers.add_parser("tabs", help="List open browser tabs with IDs, titles, and URLs")

    # switch-tab
    stab_parser = subparsers.add_parser("switch-tab", help="Switch active focus to tab ID")
    stab_parser.add_argument("tab_id", help="Target tab ID from 'agents-browser tabs'")

    # search
    search_parser = subparsers.add_parser("search", help="Perform a web search and print structured results")
    search_parser.add_argument("query", help="Search query string")
    search_parser.add_argument("--engine", default="duckduckgo", help="Search engine (default duckduckgo)")

    # read
    subparsers.add_parser("read", help="Read article in clean Reader Mode markdown")

    # read-url (browserless)
    ru_parser = subparsers.add_parser(
        "read-url", help="Fetch URL and extract readable text (no browser needed)")
    ru_parser.add_argument("url", help="Target URL")
    ru_parser.add_argument("--max-chars", type=int, default=12000)

    # scrape
    scrape_parser = subparsers.add_parser("scrape", help="Extract structured content (text, table, links, html) from CSS selector")
    scrape_parser.add_argument("selector", nargs="?", default="body", help="CSS selector (default 'body')")
    scrape_parser.add_argument("--mode", default="text", choices=["text", "table", "links", "html"], help="Extraction mode")

    # screenshot
    shot_parser = subparsers.add_parser("screenshot", help="Capture PNG screenshot")
    shot_parser.add_argument("path", nargs="?", default="", help="Optional output PNG file path")
    shot_parser.add_argument("--out", default="", help="Output PNG file path")
    shot_parser.add_argument("--full-page", action="store_true", help="Capture full scrollable page")

    # download
    dl_parser = subparsers.add_parser("download", help="Download file via element click or URL")
    dl_parser.add_argument("target", help="Element ref (@1), selector, or download URL")
    dl_parser.add_argument("--dest", default="", help="Destination file or directory path")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="Fast HTTP request using browser session cookies without DOM")
    fetch_parser.add_argument("url", help="Target URL to fetch")
    fetch_parser.add_argument("--method", default="GET", help="HTTP method (default GET)")
    fetch_parser.add_argument("--headers", default="", help="Optional JSON string of HTTP headers")
    fetch_parser.add_argument("--data", "--json", dest="data", default=None, help="JSON or text payload for request body")

    # extract-pdf
    pdf_parser = subparsers.add_parser("extract-pdf", help="Extract PDF stream via printToPDF or blob extract")
    pdf_parser.add_argument("target", nargs="?", default="", help="PDF URL or element ref (defaults to current page)")
    pdf_parser.add_argument("--out", default="", help="Output PDF file path")
    pdf_parser.add_argument("--max-pages", type=int, default=20, help="Max pages for text preview (default 20)")

    # audit
    subparsers.add_parser("audit", help="Run developer audit: console errors, horizontal overflow, broken media, failed requests")

    # inspect
    insp_parser = subparsers.add_parser("inspect", help="Inspect element tag, attributes, geometry, typography, and box model")
    insp_parser.add_argument("target", help="Target @ref, CSS selector, or visible text")

    # styles
    styles_parser = subparsers.add_parser("styles", help="Inspect computed CSS styles and CSS custom variables")
    styles_parser.add_argument("target", help="Target @ref, CSS selector, or visible text")
    styles_parser.add_argument("--props", default="", help="Comma-separated CSS property names")

    # layout
    layout_parser = subparsers.add_parser("layout", help="Inspect bounding rect, scroll metrics, and viewport visibility")
    layout_parser.add_argument("target", help="Target @ref, CSS selector, or visible text")

    # logs
    logs_parser = subparsers.add_parser("logs", help="Retrieve console logs, uncaught exceptions, and failed HTTP requests")
    logs_parser.add_argument("--type", dest="log_type", default="all", choices=["all", "console", "error", "network"], help="Log filter")
    logs_parser.add_argument("--limit", type=int, default=50, help="Max log lines (default 50)")
    logs_parser.add_argument("--clear", action="store_true", help="Clear log buffer after reading")

    # viewport
    vp_parser = subparsers.add_parser("viewport", help="Set viewport dimensions or device preset ('mobile', 'tablet', 'desktop', 'fhd')")
    vp_parser.add_argument("preset_or_width", nargs="?", default="desktop", help="Preset name ('mobile', 'tablet', 'desktop', 'fhd') or width in px")
    vp_parser.add_argument("height", nargs="?", type=int, default=900, help="Height in px when width is numeric")
    vp_parser.add_argument("--mobile", action="store_true", help="Enable mobile touch emulation")

    # eval
    eval_parser = subparsers.add_parser("eval", help="Execute JavaScript expression in active tab")
    eval_parser.add_argument("script", help="JavaScript expression to evaluate")

    # record
    rec_parser = subparsers.add_parser("record", help="Record screen activity to MP4 video or GIF")
    rec_parser.add_argument("--duration", type=float, default=5.0, help="Recording duration in seconds (default 5.0)")
    rec_parser.add_argument("--fps", type=int, default=15, help="Frames per second (default 15)")
    rec_parser.add_argument("--out", default="", help="Output .mp4 or .gif file path")

    args = parser.parse_args(raw_args)

    # Lazy-load FastMCP ONLY when running the MCP server
    if args.command in (None, "serve"):
        warnings.filterwarnings("ignore", message=".*IncompleteFieldDefinitionWarning.*")
        warnings.filterwarnings("ignore", message=".*Field 'lifespan' has an incomplete definition.*")
        from .mcp_server import mcp

        mcp.run()
        return

    try:
        from .updates import check_for_updates
        check_for_updates("agents-browser", __version__)
    except Exception:
        pass

    if args.command in ("init", "sync"):
        from .sync import main as sync_main

        cmd_argv = ["--init"] if (args.command == "init" or getattr(args, "init", False)) else []
        sys.exit(sync_main(cmd_argv))

    if args.command == "skills":
        from .sync import get_skill_source

        name = (args.name or "core").strip().lower()
        if name == "list":
            print("Available skills: core, browser-browse, browser-scrape")
            return
        if name in ("browser-browse", "browse", "core"):
            p = get_skill_source("browser-browse") / "SKILL.md"
            print(p.read_text(encoding="utf-8"))
            return
        if name in ("browser-scrape", "scrape"):
            p = get_skill_source("browser-scrape") / "SKILL.md"
            print(p.read_text(encoding="utf-8"))
            return
        p = get_skill_source("browser-browse") / "SKILL.md"
        print(p.read_text(encoding="utf-8"))
        return

    if args.command == "system-open":
        import webbrowser
        url = args.url if args.url.startswith(("http://", "https://", "file://", "about:")) else f"https://{args.url}"
        webbrowser.open(url)
        print(f"Opened {url} in system default browser.")
        return

    from .cdp import CDPClient

    session_name = getattr(args, "session", "") or None
    light_commands = {
        "snapshot", "click", "type", "fill", "select", "scroll", "back",
        "wait", "find", "tabs", "read", "scrape", "inspect", "styles",
        "layout", "viewport", "eval", "screenshot",
    }

    async def _run_cli() -> None:
        headless_init = None
        if args.command == "open" and getattr(args, "visible", False):
            headless_init = False
        c = CDPClient(headless=headless_init, session=session_name)
        c._light_mode = args.command in light_commands
        try:
            cmd = args.command
            if cmd == "open":
                print(await c.open(args.url, new_tab=args.new_tab, visible=args.visible))
            elif cmd == "headless":
                want_hl = args.mode.lower() in ("on", "true", "1")
                print(await c.set_headless(want_hl))
            elif cmd == "close":
                await c.close()
                print("Closed managed browser instance.")
            elif cmd == "snapshot":
                print(await c.snapshot(interactive_only=args.interactive_only, diff=args.diff))
            elif cmd == "click":
                print(await c.click(args.target, force=args.force))
            elif cmd == "type":
                print(await c.type_text(args.target, args.text, clear=args.clear, press_enter=args.press_enter))
            elif cmd == "fill":
                raw_t = args.target_or_json.strip()
                if raw_t.startswith("{") and args.text is None:
                    fields = json.loads(raw_t)
                    print(await c.fill_form(fields, submit_selector=args.submit))
                else:
                    val = args.text if args.text is not None else ""
                    print(await c.type_text(raw_t, val, clear=True, press_enter=bool(args.submit)))
                    if args.submit:
                        print(await c.click(args.submit))
            elif cmd == "select":
                print(await c.select(args.target, args.value))
            elif cmd == "scroll":
                target = args.target
                direction = args.direction
                if not target and (direction.startswith("@") or direction.startswith("#") or direction.startswith(".")):
                    target = direction
                    direction = "down"
                print(await c.scroll(direction=direction, amount=args.amount, target=target or None))
            elif cmd == "back":
                print(await c.go_back())
            elif cmd == "reload":
                print(await c.reload(ignore_cache=args.ignore_cache))
            elif cmd == "wait":
                print(await c.wait_stable(timeout_ms=args.timeout_ms, quiet_ms=args.quiet_ms))
            elif cmd == "find":
                print(await c.find_in_page(args.query, match_case=args.match_case))
            elif cmd == "tabs":
                tabs = await c.list_tabs()
                if not tabs:
                    print("No open browser tabs.")
                else:
                    for t in tabs:
                        print(f"[{t['id']}] {t['title']} ({t['url']}){t['active']}")
            elif cmd == "switch-tab":
                print(await c.switch_tab(args.tab_id))
            elif cmd == "search":
                print(await c.search(args.query, engine=args.engine))
            elif cmd == "read":
                print(await c.read_article())
            elif cmd == "read-url":
                from .webtext import fetch_text

                try:
                    print(fetch_text(args.url, max_chars=args.max_chars))
                except Exception as exc:
                    print(f"Error reading {args.url}: {exc}")
            elif cmd == "scrape":
                print(await c.scrape(selector=args.selector, mode=args.mode))
            elif cmd == "screenshot":
                out_arg = args.out or args.path
                b64 = await c.screenshot(full_page=args.full_page)
                p = _resolve_screenshot_path(out_arg) if not out_arg else Path(out_arg)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(base64.b64decode(b64))
                print(f"Screenshot saved to {p.resolve()}")
            elif cmd == "download":
                print(await c.download(ref_or_url=args.target, dest_path=args.dest))
            elif cmd == "fetch":
                print(await c.fetch(url=args.url, method=args.method, headers=args.headers or None, json_data=args.data))
            elif cmd == "extract-pdf":
                print(await c.extract_pdf(url_or_ref=args.target, save_path=args.out, max_pages=args.max_pages))
            elif cmd == "audit":
                print(await c.audit())
            elif cmd == "inspect":
                print(await c.inspect(args.target))
            elif cmd == "styles":
                props = [x.strip() for x in args.props.split(",") if x.strip()] if args.props else None
                print(await c.get_styles(args.target, properties=props))
            elif cmd == "layout":
                print(await c.get_layout(args.target))
            elif cmd == "logs":
                print(await c.get_logs(log_type=args.log_type, limit=args.limit, clear=args.clear))
            elif cmd == "viewport":
                pw = str(args.preset_or_width).strip()
                if pw.isdigit():
                    print(await c.set_viewport(width=int(pw), height=args.height, mobile=args.mobile))
                else:
                    print(await c.set_viewport(preset=pw, mobile=args.mobile))
            elif cmd == "eval":
                res = await c.evaluate(args.script)
                if isinstance(res, (dict, list)):
                    print(json.dumps(res, indent=2, ensure_ascii=False))
                else:
                    print(res)
            elif cmd == "record":
                print(await c.record(duration_sec=args.duration, fps=args.fps, path=args.out))
        finally:
            await c.close_ws()

    asyncio.run(_run_cli())


if __name__ == "__main__":
    main()
