"""Minimal CDP Browser MCP for AI coding agents."""

__version__ = "0.45.0"

from .cdp import CDPClient
from .mcp_server import mcp

__all__ = ["CDPClient", "mcp", "__version__"]
