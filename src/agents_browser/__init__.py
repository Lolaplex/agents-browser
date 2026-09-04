"""Minimal CDP Browser MCP for AI coding agents."""

from .cdp import CDPClient
from .mcp_server import mcp

__version__ = "0.44.0"
__all__ = ["CDPClient", "mcp", "__version__"]

