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
        "description": "Minimal CDP Browser MCP & CLI for AI coding agents",
        "commands": {
            "serve": {
                "usage": "agents-browser serve",
                "description": "Run the FastMCP server over stdio (default)",
                "side_effects": "read-only",
            },
            "init": {
                "usage": "agents-browser init",
                "description": "Plug & Play setup: auto-configure MCP in host IDEs and sync skills",
                "side_effects": "mutating",
            },
            "sync": {
                "usage": "agents-browser sync [--init]",
                "description": "Auto-configure MCP server across host IDEs and sync skills",
                "side_effects": "mutating",
            },
            "skills": {
                "usage": "agents-browser skills [NAME]",
                "description": "Print agent skill instructions for CLI or MCP workflows ('core', 'browser-browse', 'browser-scrape')",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Skill name (default 'core')"}
                    },
                },
            },
            "open": {
                "usage": "agents-browser open URL [--new-tab] [--visible]",
                "description": "Open a URL in the managed Chromium (headless by default)",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to navigate to"},
                        "new_tab": {"type": "boolean", "description": "Open in a new tab"},
                        "visible": {"type": "boolean", "description": "Launch visible desktop browser window"},
                    },
                    "required": ["url"],
                },
            },
            "system-open": {
                "usage": "agents-browser system-open URL",
                "description": "Open URL in the OS default desktop browser",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to open in system browser"},
                    },
                    "required": ["url"],
                },
            },
            "headless": {
                "usage": "agents-browser headless [on|off]",
                "description": "Switch browser mode between headless background and visible window",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "description": "'on' for headless, 'off' for visible window"},
                    },
                },
            },
            "close": {
                "usage": "agents-browser close",
                "description": "Close the managed CDP browser instance",
                "side_effects": "mutating",
            },
            "snapshot": {
                "usage": "agents-browser snapshot [--interactive] [--diff]",
                "description": "Page text outline with @ref interactive elements",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "interactive": {"type": "boolean", "description": "Return only interactive @ref elements"},
                        "diff": {"type": "boolean", "description": "Show only changes since previous snapshot"},
                    },
                },
            },
            "click": {
                "usage": "agents-browser click TARGET [--force]",
                "description": "Click element by @ref (e.g. @1), CSS selector, or visible text (with hit-test occlusion check)",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Element @ref, CSS selector, or text"},
                        "force": {"type": "boolean", "description": "Bypass occlusion and disabled checks"},
                    },
                    "required": ["target"],
                },
            },
            "type": {
                "usage": "agents-browser type TARGET TEXT [--clear] [--enter]",
                "description": "Focus input/textarea and type text",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Input @ref, CSS selector, or text"},
                        "text": {"type": "string", "description": "Text to type"},
                        "clear": {"type": "boolean", "description": "Clear input first"},
                        "enter": {"type": "boolean", "description": "Press Enter / submit after typing"},
                    },
                    "required": ["target", "text"],
                },
            },
            "fill": {
                "usage": "agents-browser fill TARGET_OR_JSON [TEXT] [--submit SELECTOR]",
                "description": "Fill a single field (clearing first) or batch-fill a JSON map of fields",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_or_json": {"type": "string", "description": "Target @ref/selector or JSON dict of fields"},
                        "text": {"type": "string", "description": "Text value when filling a single field"},
                        "submit": {"type": "string", "description": "Optional submit @ref or selector to click"},
                    },
                    "required": ["target_or_json"],
                },
            },
            "select": {
                "usage": "agents-browser select TARGET VALUE",
                "description": "Select dropdown <select> option by value, text, or substring",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Select @ref or CSS selector"},
                        "value": {"type": "string", "description": "Option value or text"},
                    },
                    "required": ["target", "value"],
                },
            },
            "scroll": {
                "usage": "agents-browser scroll [DIRECTION] [AMOUNT] [--target TARGET]",
                "description": "Scroll page ('down', 'up', 'top', 'bottom') or scroll target element into view",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "description": "Direction ('down', 'up', 'top', 'bottom')"},
                        "target": {"type": "string", "description": "Optional @ref or selector to scroll into view"},
                    },
                },
            },
            "back": {
                "usage": "agents-browser back",
                "description": "Navigate back in browser history",
                "side_effects": "mutating",
            },
            "reload": {
                "usage": "agents-browser reload [--ignore-cache]",
                "description": "Reload active page",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ignore_cache": {"type": "boolean", "description": "Force hard reload ignoring cache"},
                    },
                },
            },
            "wait": {
                "usage": "agents-browser wait [--timeout-ms MS] [--quiet-ms MS]",
                "description": "Wait for network requests and DOM mutations to settle",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timeout_ms": {"type": "integer", "description": "Timeout in milliseconds"},
                        "quiet_ms": {"type": "integer", "description": "Quiet duration in milliseconds"},
                    },
                },
            },
            "find": {
                "usage": "agents-browser find QUERY [--match-case]",
                "description": "Search text occurrences in page without loading full DOM",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Text to search for"},
                        "match_case": {"type": "boolean", "description": "Case-sensitive search"},
                    },
                    "required": ["query"],
                },
            },
            "tabs": {
                "usage": "agents-browser tabs",
                "description": "List open browser tabs with IDs, titles, and URLs",
                "side_effects": "read-only",
            },
            "switch-tab": {
                "usage": "agents-browser switch-tab TAB_ID",
                "description": "Switch active focus to tab ID",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tab_id": {"type": "string", "description": "Target tab ID"},
                    },
                    "required": ["tab_id"],
                },
            },
            "search": {
                "usage": "agents-browser search QUERY [--engine ENGINE]",
                "description": "Web search with structured organic results",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "engine": {"type": "string", "description": "Search engine (default duckduckgo)"},
                    },
                    "required": ["query"],
                },
            },
            "read": {
                "usage": "agents-browser read",
                "description": "Reader-mode markdown of the current page article",
                "side_effects": "read-only",
            },
            "scrape": {
                "usage": "agents-browser scrape [SELECTOR] [--mode MODE]",
                "description": "Extract structured content ('text', 'table', 'links', 'html') from CSS selector",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector (default 'body')"},
                        "mode": {"type": "string", "description": "'text', 'table', 'links', or 'html'"},
                    },
                },
            },
            "screenshot": {
                "usage": "agents-browser screenshot [PATH] [--out PATH] [--full-page]",
                "description": "Capture a PNG screenshot of the current page",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "out": {"type": "string", "description": "Output PNG path"},
                        "full_page": {"type": "boolean", "description": "Capture full scrollable page"},
                    },
                },
            },
            "download": {
                "usage": "agents-browser download TARGET [--dest PATH]",
                "description": "Download a file via element click or URL to controlled destination",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Element @ref, selector, or URL"},
                        "dest": {"type": "string", "description": "Destination file or directory path"},
                    },
                    "required": ["target"],
                },
            },
            "fetch": {
                "usage": "agents-browser fetch URL [--method METHOD] [--headers JSON] [--data JSON]",
                "description": "Fast HTTP/JSON request using browser cookies without DOM rendering",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "Target URL"},
                        "method": {"type": "string", "description": "HTTP method"},
                        "headers": {"type": "string", "description": "JSON string of headers"},
                        "data": {"type": "string", "description": "Request body payload"},
                    },
                    "required": ["url"],
                },
            },
            "extract-pdf": {
                "usage": "agents-browser extract-pdf [TARGET] [--out PATH] [--max-pages N]",
                "description": "Directly extract PDF streams, convert pages via Page.printToPDF or extract PDF Viewer blobs",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "PDF URL or @ref"},
                        "out": {"type": "string", "description": "Output PDF path"},
                        "max_pages": {"type": "integer", "description": "Max pages to preview"},
                    },
                },
            },
            "audit": {
                "usage": "agents-browser audit",
                "description": "Run developer quality audit: console errors, horizontal overflow, broken images, network errors",
                "side_effects": "read-only",
            },
            "inspect": {
                "usage": "agents-browser inspect TARGET",
                "description": "Inspect element tag, attributes, geometry, typography, and box-model",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Element @ref, CSS selector, or text"},
                    },
                    "required": ["target"],
                },
            },
            "styles": {
                "usage": "agents-browser styles TARGET [--props PROPS]",
                "description": "Inspect computed CSS properties and custom CSS variables",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Element @ref, CSS selector, or text"},
                        "props": {"type": "string", "description": "Comma-separated CSS property names"},
                    },
                    "required": ["target"],
                },
            },
            "layout": {
                "usage": "agents-browser layout TARGET",
                "description": "Inspect element bounding rect, scroll metrics, and viewport visibility",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Element @ref, CSS selector, or text"},
                    },
                    "required": ["target"],
                },
            },
            "logs": {
                "usage": "agents-browser logs [--type TYPE] [--limit N] [--clear]",
                "description": "Retrieve buffered console logs, uncaught exceptions, and failed HTTP requests",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "'all', 'console', 'error', or 'network'"},
                        "limit": {"type": "integer", "description": "Max log lines"},
                        "clear": {"type": "boolean", "description": "Clear log buffer"},
                    },
                },
            },
            "viewport": {
                "usage": "agents-browser viewport [PRESET_OR_WIDTH] [HEIGHT] [--mobile]",
                "description": "Set viewport dimensions or device preset ('mobile', 'tablet', 'desktop', 'fhd')",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preset_or_width": {"type": "string", "description": "Preset name or pixel width"},
                        "height": {"type": "integer", "description": "Pixel height"},
                        "mobile": {"type": "boolean", "description": "Enable mobile touch emulation"},
                    },
                },
            },
            "eval": {
                "usage": "agents-browser eval SCRIPT",
                "description": "Execute JavaScript expression in active tab",
                "side_effects": "mutating",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {"type": "string", "description": "JavaScript expression"},
                    },
                    "required": ["script"],
                },
            },
            "record": {
                "usage": "agents-browser record [--duration SEC] [--fps FPS] [--out PATH]",
                "description": "Record screen activity to MP4 video or GIF",
                "side_effects": "read-only",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "duration": {"type": "number", "description": "Duration in seconds"},
                        "fps": {"type": "integer", "description": "Frames per second"},
                        "out": {"type": "string", "description": "Output file path"},
                    },
                },
            },
        },
        "flags": ["--help-json", "--version", "--session"],
        "env": [
            "AGENTS_BROWSER_BIN",
            "AGENTS_BROWSER_HEADLESS",
            "AGENTS_BROWSER_SESSION",
            "AGENTS_BROWSER_PORT",
            "CHROME_PATH",
            "BROWSER_PATH",
        ],
    }
