"""secb-mcp: the SEC-bench Linux kernel harness exposed as MCP tools."""

from .server import main, mcp

__all__ = ["main", "mcp"]
