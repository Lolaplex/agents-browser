"""Minimal CDP Browser MCP for AI coding agents."""

from __future__ import annotations

from typing import Any

__version__ = "0.46.0"

__all__ = ["CDPClient", "mcp", "__version__"]


def __getattr__(name: str) -> Any:
    if name == "CDPClient":
        from .cdp import CDPClient

        return CDPClient
    if name == "mcp":
        from .mcp_server import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
