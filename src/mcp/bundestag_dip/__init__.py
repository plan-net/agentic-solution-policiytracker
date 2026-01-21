"""Bundestag DIP API MCP Server.

Provides MCP tools for querying the German Bundestag
Document and Information System (DIP) API.
"""

from .server import app, mcp_server

__all__ = ["app", "mcp_server"]
