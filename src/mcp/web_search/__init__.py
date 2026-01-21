"""Web Search MCP Server.

Provides MCP tools for web search via Exa.ai and DPA news.
"""

from .server import app, mcp_server

__all__ = ["app", "mcp_server"]
