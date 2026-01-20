"""Claude Agent module for PolicyTracker - connects to Knowledge Graph via MCP.

This module provides Claude-based chat agents that use the MCP protocol
to query the political monitoring knowledge graph. It integrates with
the existing ChatContextTracker for session persistence and graph visualization.

Uses Claude Agent SDK for automatic agentic loop and native MCP support.
"""

from .agent_sdk import PolicyTrackerSDKAgent
from .mcp_client import MCPClient

# Alias for backward compatibility
PolicyTrackerAgent = PolicyTrackerSDKAgent

__all__ = ["PolicyTrackerAgent", "PolicyTrackerSDKAgent", "MCPClient"]
