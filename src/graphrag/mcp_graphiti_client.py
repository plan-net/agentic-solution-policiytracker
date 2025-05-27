"""
MCP Client for Graphiti temporal knowledge graph operations.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_mcp_adapters import MCPToolkit
import httpx

from ..config import Settings

logger = logging.getLogger(__name__)

class GraphitiMCPClient:
    """Client for interacting with Graphiti via MCP server."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the Graphiti MCP client."""
        self.settings = settings or Settings()
        self.base_url = f"http://{self.settings.GRAPHITI_MCP_HOST}:{self.settings.GRAPHITI_MCP_PORT}"
        self.sse_url = f"{self.base_url}/sse"
        
        # Initialize MCP toolkit
        try:
            self.toolkit = MCPToolkit(
                server_name="graphiti-memory",
                transport="sse",
                url=self.sse_url
            )
            logger.info(f"Connected to Graphiti MCP server at {self.sse_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Graphiti MCP server: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test if the MCP server is accessible."""
        try:
            async with httpx.AsyncClient() as client:
                # Try to connect to the SSE endpoint
                response = await client.get(
                    self.sse_url,
                    headers={"Accept": "text/event-stream"}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def add_episode(
        self,
        name: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a new episode (document/event) to the knowledge graph."""
        try:
            params = {
                "name": name,
                "content": content,
                "timestamp": timestamp.isoformat() if timestamp else datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            result = await self.toolkit.call_tool("add_episode", **params)
            logger.info(f"Added episode: {name}")
            return result
        except Exception as e:
            logger.error(f"Failed to add episode: {e}")
            raise
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        time_range: Optional[tuple[datetime, datetime]] = None
    ) -> List[Dict[str, Any]]:
        """Search the knowledge graph with optional time range."""
        try:
            params = {
                "query": query,
                "limit": limit
            }
            
            if time_range:
                params["start_date"] = time_range[0].isoformat()
                params["end_date"] = time_range[1].isoformat()
            
            results = await self.toolkit.call_tool("search", **params)
            logger.info(f"Search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_entity_mentions(
        self,
        entity_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get all mentions of an entity across episodes."""
        try:
            results = await self.toolkit.call_tool(
                "get_entity_mentions",
                entity_name=entity_name,
                limit=limit
            )
            logger.info(f"Found {len(results)} mentions of {entity_name}")
            return results
        except Exception as e:
            logger.error(f"Failed to get entity mentions: {e}")
            raise
    
    async def delete_episode(self, episode_id: str) -> bool:
        """Delete an episode from the knowledge graph."""
        try:
            result = await self.toolkit.call_tool(
                "delete_episode",
                episode_id=episode_id
            )
            logger.info(f"Deleted episode: {episode_id}")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to delete episode: {e}")
            raise
    
    async def clear_graph(self) -> bool:
        """Clear the entire knowledge graph (use with caution!)."""
        try:
            result = await self.toolkit.call_tool("clear")
            logger.warning("Cleared entire knowledge graph")
            return result.get("success", False)
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            raise