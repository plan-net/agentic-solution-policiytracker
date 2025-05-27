"""
MCP Client for Graphiti temporal knowledge graph operations.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

from ..config import GraphRAGSettings

logger = logging.getLogger(__name__)


class GraphitiMCPClient:
    """Client for interacting with Graphiti via MCP server."""

    def __init__(self, settings: Optional[GraphRAGSettings] = None):
        """Initialize the Graphiti MCP client."""
        self.settings = settings or GraphRAGSettings()
        self.base_url = (
            f"http://{self.settings.GRAPHITI_MCP_HOST}:{self.settings.GRAPHITI_MCP_PORT}"
        )
        self.sse_url = f"{self.base_url}/sse"

        # Configure MCP client
        self.client_config = {"graphiti": {"url": self.sse_url, "transport": "sse"}}

        self.client = None
        self.tools = None
        logger.info(f"Configured Graphiti MCP client for {self.sse_url}")

    async def _ensure_connected(self):
        """Ensure the MCP client is connected and tools are loaded."""
        if self.client is None:
            try:
                self.client = MultiServerMCPClient(self.client_config)
                self.tools = await self.client.get_tools()
                logger.info(f"Connected to Graphiti MCP server, loaded {len(self.tools)} tools")
            except Exception as e:
                logger.error(f"Failed to connect to Graphiti MCP server: {e}")
                raise

    async def _call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a specific MCP tool by name."""
        await self._ensure_connected()

        # Find the tool
        tool = None
        for t in self.tools:
            if hasattr(t, "name") and t.name == tool_name:
                tool = t
                break

        if tool is None:
            available_tools = [t.name for t in self.tools if hasattr(t, "name")]
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available_tools}")

        # Call the tool
        try:
            result = await tool.ainvoke(kwargs)
            return result
        except Exception as e:
            logger.error(f"Failed to call tool '{tool_name}': {e}")
            raise

    async def test_connection(self) -> bool:
        """Test if the MCP server is accessible."""
        try:
            await self._ensure_connected()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def add_episode(
        self,
        name: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Add a new episode (document/event) to the knowledge graph."""
        try:
            params = {
                "name": name,
                "episode_body": content,  # Graphiti uses episode_body not content
                "source": "text",
                "source_description": metadata.get("source_description", "") if metadata else "",
            }

            result = await self._call_tool("add_memory", **params)
            logger.info(f"Added episode: {name}")
            return result
        except Exception as e:
            logger.error(f"Failed to add episode: {e}")
            raise

    async def search(
        self,
        query: str,
        max_nodes: int = 10,
        time_range: Optional[tuple[datetime, datetime]] = None,
    ) -> list[dict[str, Any]]:
        """Search the knowledge graph with optional time range."""
        try:
            params = {"query": query, "max_nodes": max_nodes}

            result = await self._call_tool("search_memory_nodes", **params)
            logger.info("Search returned results")
            return result
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def search_facts(self, query: str, max_facts: int = 10) -> list[dict[str, Any]]:
        """Search for relevant facts in the knowledge graph."""
        try:
            params = {"query": query, "max_facts": max_facts}

            result = await self._call_tool("search_memory_facts", **params)
            logger.info(f"Found facts for query: {query}")
            return result
        except Exception as e:
            logger.error(f"Failed to search facts: {e}")
            raise

    async def get_episodes(self, last_n: int = 10) -> list[dict[str, Any]]:
        """Get the most recent episodes."""
        try:
            params = {"last_n": last_n}
            result = await self._call_tool("get_episodes", **params)
            logger.info(f"Retrieved {last_n} recent episodes")
            return result
        except Exception as e:
            logger.error(f"Failed to get episodes: {e}")
            raise

    async def delete_episode(self, uuid: str) -> bool:
        """Delete an episode from the knowledge graph."""
        try:
            result = await self._call_tool("delete_episode", uuid=uuid)
            logger.info(f"Deleted episode: {uuid}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete episode: {e}")
            raise

    async def clear_graph(self) -> bool:
        """Clear the entire knowledge graph (use with caution!)."""
        try:
            result = await self._call_tool("clear_graph")
            logger.warning("Cleared entire knowledge graph")
            return True
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            raise

    async def list_available_tools(self) -> list[str]:
        """List all available MCP tools."""
        await self._ensure_connected()
        return [tool.name for tool in self.tools if hasattr(tool, "name")]
