"""Minimal CDP Browser MCP for AI coding agents."""

from __future__ import annotations

from typing import Any

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("agents-browser")
except _PackageNotFoundError:  # a source checkout that was never installed
    __version__ = "0.0.0+source"

__all__ = ["CDPClient", "mcp", "__version__"]


def __getattr__(name: str) -> Any:
    if name == "CDPClient":
        from .cdp import CDPClient

        return CDPClient
    if name == "mcp":
        from .mcp_server import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
