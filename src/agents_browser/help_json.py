"""Machine-readable CLI catalog for Cordis / suite overlay generation."""
from __future__ import annotations

from typing import Any


def _version() -> str:
    try:
        from pathlib import Path

        init = Path(__file__).with_name("__init__.py")
        for line in init.read_text(encoding="utf-8").splitlines():
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    try:
        from importlib.metadata import version

        return version("agents-browser")
    except Exception:
        return "0.0.0"


def help_json() -> dict[str, Any]:
    return {
        "name": "agents-browser",
        "version": _version(),
        "description": "Minimal CDP Browser MCP for AI coding agents",
        "commands": {
            "serve": {
                "usage": "agents-browser serve",
                "description": "Run the FastMCP server over stdio (default)",
            },
            "init": {
                "usage": "agents-browser init",
                "description": "Plug & Play setup: auto-configure MCP in host IDEs and sync skills",
            },
            "sync": {
                "usage": "agents-browser sync [--init]",
                "description": "Auto-configure MCP server across host IDEs and sync skills",
            },
            "open": {
                "usage": "agents-browser open URL [--visible]",
                "description": "Open a URL in the managed Chromium (headless by default)",
            },
            "system-open": {
                "usage": "agents-browser system-open URL",
                "description": "Open URL in the OS default desktop browser",
            },
            "search": {
                "usage": "agents-browser search QUERY",
                "description": "Web search with structured organic results",
            },
            "read": {
                "usage": "agents-browser read",
                "description": "Reader-mode markdown of the current page article",
            },
            "snapshot": {
                "usage": "agents-browser snapshot",
                "description": "Page text outline with @ref interactive elements",
            },
            "screenshot": {
                "usage": "agents-browser screenshot [--out PATH]",
                "description": "Capture a PNG of the current page",
            },
        },
        "flags": ["--help-json", "--version"],
        "env": ["AGENTS_BROWSER_BIN", "AGENTS_BROWSER_HEADLESS", "CHROME_PATH", "BROWSER_PATH"],
    }
