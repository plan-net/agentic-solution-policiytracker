"""Claude Agent module for PolicyTracker - connects to Knowledge Graph via MCP.

This module provides a Claude-based chat agent that uses the MCP protocol
to query the political monitoring knowledge graph. It integrates with
the existing ChatContextTracker for session persistence and graph visualization.
"""

from .agent import PolicyTrackerAgent
from .mcp_client import MCPClient

__all__ = ["PolicyTrackerAgent", "MCPClient"]
