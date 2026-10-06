"""Minimal CDP Browser MCP for AI coding agents."""

from .cdp import CDPClient
from .mcp_server import mcp

__version__ = "0.44.1"
__all__ = ["CDPClient", "mcp", "__version__"]

