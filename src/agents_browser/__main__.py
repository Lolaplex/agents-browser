"""CLI entrypoint for running agents-browser."""

from __future__ import annotations

import argparse
import asyncio
import base64
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

# Suppress upstream pydantic_settings forward-ref warnings
warnings.filterwarnings("ignore", message=".*IncompleteFieldDefinitionWarning.*")
warnings.filterwarnings("ignore", message=".*Field 'lifespan' has an incomplete definition.*")

from . import __version__
from .cdp import CDPClient
from .mcp_server import mcp
from .sync import main as sync_main


def main(argv: list[str] | None = None) -> None:
    raw_args = list(argv if argv is not None else sys.argv[1:])

    # Support plain positional 'version' and 'help'
    if raw_args and raw_args[0] in ("version",):
        print(f"agents-browser {__version__}")
        return
    if raw_args and raw_args[0] in ("help",):
        raw_args = ["--help"]

    parser = argparse.ArgumentParser(
        prog="agents-browser",
        description="Minimal CDP Browser MCP for AI coding agents. Zero Node, zero 300MB downloads.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"agents-browser {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve (default)
    subparsers.add_parser("serve", help="Run the FastMCP server over stdio (default)")

    # init (Plug & Play)
    subparsers.add_parser("init", help="Plug & Play setup: auto-configure MCP in all IDEs and sync skills")

    # sync
    sync_parser = subparsers.add_parser("sync", help="Auto-configure MCP server across host IDEs and sync skills")
    sync_parser.add_argument("--init", action="store_true", help="Perform initial host IDE registration")

    # open
    open_parser = subparsers.add_parser("open", help="Open a URL in browser")
    open_parser.add_argument("url", help="URL to navigate to")

    # search
    search_parser = subparsers.add_parser("search", help="Perform a web search and print structured results")
    search_parser.add_argument("query", help="Search query string")

    # read
    subparsers.add_parser("read", help="Read article in Reader Mode")

    # snapshot
    subparsers.add_parser("snapshot", help="Capture page text outline with @ref interactive element indices")

    # screenshot
    shot_parser = subparsers.add_parser("screenshot", help="Capture screenshot")
    shot_parser.add_argument("--out", default="screenshot.png", help="Output PNG file path")

    args = parser.parse_args(raw_args)

    if args.command in (None, "serve"):
        mcp.run()
    elif args.command in ("init", "sync"):
        cmd_argv = ["--init"] if (args.command == "init" or getattr(args, "init", False)) else []
        sys.exit(sync_main(cmd_argv))
    elif args.command == "open":
        async def _open():
            c = CDPClient()
            try:
                res = await c.open(args.url)
                print(res)
            finally:
                await c.close_ws()
        asyncio.run(_open())
    elif args.command == "search":
        async def _search():
            c = CDPClient()
            try:
                res = await c.search(args.query)
                print(res)
            finally:
                await c.close_ws()
        asyncio.run(_search())
    elif args.command == "read":
        async def _read():
            c = CDPClient()
            try:
                res = await c.read_article()
                print(res)
            finally:
                await c.close_ws()
        asyncio.run(_read())
    elif args.command == "snapshot":
        async def _snap():
            c = CDPClient()
            try:
                res = await c.snapshot()
                print(res)
            finally:
                await c.close_ws()
        asyncio.run(_snap())
    elif args.command == "screenshot":
        async def _shot():
            c = CDPClient()
            try:
                b64 = await c.screenshot()
                p = Path(args.out)
                p.write_bytes(base64.b64decode(b64))
                print(f"Screenshot saved to {p.resolve()}")
            finally:
                await c.close_ws()
        asyncio.run(_shot())


if __name__ == "__main__":
    main()
