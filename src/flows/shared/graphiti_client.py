"""
Shared Graphiti client wrapper with connection pooling and configuration.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class GraphitiConfig:
    """Centralized configuration for Graphiti connections."""
    
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROUP_ID = os.getenv("GRAPHITI_GROUP_ID", "political_monitoring_v2")
    
    @classmethod
    async def create_client(cls) -> Graphiti:
        """Create and initialize Graphiti client."""
        client = Graphiti(cls.NEO4J_URI, cls.NEO4J_USER, cls.NEO4J_PASSWORD)
        await client.build_indices_and_constraints()
        return client


# Custom entity types for political domain (from successful v0.2.0 implementation)
class Policy(BaseModel):
    policy_name: str = Field(..., description="The name of the policy")
    jurisdiction: str | None = Field(None, description="Primary jurisdiction where policy applies")
    status: str | None = Field(None, description="Current status (draft, enacted, implemented, etc.)")
    effective_date: str | None = Field(None, description="When the policy becomes effective")


class Company(BaseModel):
    company_name: str = Field(..., description="The name of the company")
    industry: str | None = Field(None, description="Primary industry or sector")
    headquarters: str | None = Field(None, description="Location of headquarters")
    size: str | None = Field(None, description="Company size (startup, SME, large, multinational)")


class Politician(BaseModel):
    politician_name: str = Field(..., description="The name of the politician")
    position: str | None = Field(None, description="Current position or role")
    party: str | None = Field(None, description="Political party affiliation")
    jurisdiction: str | None = Field(None, description="Geographic jurisdiction of influence")


class GovernmentAgency(BaseModel):
    agency_name: str = Field(..., description="The name of the government agency")
    jurisdiction: str | None = Field(None, description="Geographic jurisdiction")
    mandate: str | None = Field(None, description="Primary mandate or responsibility")
    regulatory_power: str | None = Field(None, description="Type of regulatory authority")


class LegalFramework(BaseModel):
    framework_name: str = Field(..., description="The name of the legal framework")
    framework_type: str | None = Field(None, description="Type (law, regulation, directive, etc.)")
    jurisdiction: str | None = Field(None, description="Geographic scope")
    domain: str | None = Field(None, description="Legal domain (privacy, AI, cybersecurity, etc.)")


class Regulation(BaseModel):
    regulation_name: str = Field(..., description="The name of the regulation")
    regulatory_body: str | None = Field(None, description="Issuing regulatory body")
    compliance_deadline: str | None = Field(None, description="Compliance deadline if applicable")
    penalties: str | None = Field(None, description="Penalties for non-compliance")


class LobbyGroup(BaseModel):
    group_name: str = Field(..., description="The name of the lobby group")
    focus_area: str | None = Field(None, description="Primary area of lobbying focus")
    members: str | None = Field(None, description="Key member organizations")
    position: str | None = Field(None, description="Stated position on key issues")


# Entity types mapping for Graphiti
POLITICAL_ENTITY_TYPES = {
    "Policy": Policy,
    "Company": Company, 
    "Politician": Politician,
    "GovernmentAgency": GovernmentAgency,
    "LegalFramework": LegalFramework,
    "Regulation": Regulation,
    "LobbyGroup": LobbyGroup,
}


class SharedGraphitiClient:
    """Wrapper for Graphiti client with political domain configuration."""
    
    def __init__(self):
        self.client: Optional[Graphiti] = None
        self.config = GraphitiConfig()
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = await GraphitiConfig.create_client()
        logger.info("Graphiti client initialized", 
                   uri=self.config.NEO4J_URI, 
                   group_id=self.config.GROUP_ID)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self.client, 'close'):
            await self.client.close()
        logger.info("Graphiti client closed")
    
    async def add_episode(self, name: str, content: str, source_description: str, 
                         reference_time: Optional[datetime] = None, max_retries: int = 3) -> dict:
        """Add episode with political entity types and retry logic for LLM failures."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Add detailed logging for debugging
        logger.info(f"Adding episode to Graphiti: name='{name}', content_length={len(content)}, source='{source_description}'")
        logger.debug(f"Reference time: {reference_time}, group_id: {self.config.GROUP_ID}")
        logger.debug(f"Entity types count: {len(POLITICAL_ENTITY_TYPES)}")
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.warning(f"Retry attempt {attempt + 1}/{max_retries} for episode: {name}")
                
                result = await self.client.add_episode(
                    name=name,
                    episode_body=content,
                    source_description=source_description,
                    reference_time=reference_time or datetime.now(),
                    source=EpisodeType.text,
                    group_id=self.config.GROUP_ID,
                    entity_types=POLITICAL_ENTITY_TYPES,
                )
                
                logger.info(f"Graphiti episode created successfully: {result.episode.uuid}")
                
                return {
                    "episode_id": result.episode.uuid,
                    "entities": result.nodes,
                    "entity_count": len(result.nodes),
                    "relationships": getattr(result, 'edges', []),
                    "relationship_count": len(getattr(result, 'edges', []))
                }
                
            except Exception as e:
                last_exception = e
                error_msg = str(e)
                
                # Check for specific LLM extraction failures that warrant retry
                is_retryable = (
                    "KeyError" in str(type(e).__name__) and ("''" in error_msg or "empty" in error_msg.lower()) or
                    "target_node_uuid" in error_msg or
                    "uuid_entity_map" in error_msg
                )
                
                if is_retryable and attempt < max_retries - 1:
                    import asyncio
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"LLM extraction error detected (attempt {attempt + 1}/{max_retries}): {error_msg}")
                    logger.info(f"Retrying after {wait_time}s - this is likely due to LLM producing invalid entity relationships")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # Enhanced error logging with full exception details
                    import traceback
                    logger.error(f"Graphiti add_episode failed with exception type: {type(e).__name__}")
                    logger.error(f"Exception message: {str(e)}")
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    logger.error(f"Episode parameters: name='{name}', source='{source_description}', group_id='{self.config.GROUP_ID}'")
                    
                    if attempt == max_retries - 1:
                        logger.error(f"All {max_retries} retry attempts failed for episode: {name}")
                    
                    raise e
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
    
    async def search(self, query: str) -> dict:
        """Search the knowledge graph."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        results = await self.client.search(query)
        return {
            "nodes": results.nodes,
            "node_count": len(results.nodes),
            "query": query
        }
    
    async def build_communities(self, timeout_seconds: int = 60) -> list:
        """Build communities using Graphiti's built-in community detection with timeout."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            import asyncio
            logger.info("Starting community detection algorithm...")
            
            # Run with timeout to prevent hanging
            communities = await asyncio.wait_for(
                self.client.build_communities(), 
                timeout=timeout_seconds
            )
            
            logger.info(f"Built {len(communities)} communities")
            return communities
            
        except asyncio.TimeoutError:
            logger.warning(f"Community building timed out after {timeout_seconds}s")
            return []
        except Exception as e:
            logger.warning(f"Community building failed: {e}")
            return []
    
    async def clear_graph(self) -> bool:
        """Clear all data from the graph using Graphiti's proper clear method."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            # Use the same approach as Graphiti MCP server
            from graphiti_core.utils.maintenance.graph_data_operations import clear_data
            
            logger.info("Clearing all graph data...")
            await clear_data(self.client.driver)
            
            logger.info("Rebuilding indices and constraints...")
            await self.client.build_indices_and_constraints()
            
            logger.info("Graph cleared successfully and indices rebuilt")
            return True
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            return False


def generate_episode_name(doc_path, timestamp: datetime) -> str:
    """Generate consistent episode names for documents."""
    # Handle both Path objects and strings
    if isinstance(doc_path, str):
        doc_path = Path(doc_path)
    return f"political_doc_{doc_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def extract_document_date(content: str) -> Optional[datetime]:
    """Extract document date from content (placeholder for future implementation)."""
    # TODO: Implement date extraction logic
    return None