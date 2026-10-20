"""Minimal CDP Browser MCP for AI coding agents."""

__version__ = "0.46.0"

from .cdp import CDPClient
from .mcp_server import mcp

__all__ = ["CDPClient", "mcp", "__version__"]
