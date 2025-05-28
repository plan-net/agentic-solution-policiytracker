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


# Enhanced entity types for political domain with relationship guidance
class Policy(BaseModel):
    """Government policies, laws, and regulations that create compliance obligations and affect companies."""
    policy_name: str = Field(..., description="Official name of the policy, law, or regulation that companies must comply with")
    jurisdiction: str | None = Field(None, description="Geographic region where this policy is enforced and companies must comply")
    status: str | None = Field(None, description="Current legislative status: draft, enacted, implemented, or repealed")
    effective_date: str | None = Field(None, description="Date when companies must begin compliance with this policy")
    regulatory_body: str | None = Field(None, description="Government agency that enforces this policy and monitors compliance")


class Company(BaseModel):
    """Business entities that are subject to government regulations and policies."""
    company_name: str = Field(..., description="Name of the company that may be regulated, fined, or required to comply with policies")
    industry: str | None = Field(None, description="Business sector that determines which regulations apply to this company")
    headquarters: str | None = Field(None, description="Primary location that determines jurisdictional authority over the company")
    size: str | None = Field(None, description="Company scale (startup, SME, large corporation) affecting regulatory requirements")
    regulatory_status: str | None = Field(None, description="Current compliance status or regulatory issues facing the company")


class Politician(BaseModel):
    """Political figures who propose, support, or oppose policies and regulations."""
    politician_name: str = Field(..., description="Name of the politician who influences, proposes, or votes on policies affecting companies")
    position: str | None = Field(None, description="Official role that grants authority to create or influence regulatory policy")
    party: str | None = Field(None, description="Political party affiliation that indicates policy stance and voting patterns")
    jurisdiction: str | None = Field(None, description="Geographic area where this politician has regulatory authority")
    policy_focus: str | None = Field(None, description="Key policy areas this politician champions or opposes")


class GovernmentAgency(BaseModel):
    """Regulatory bodies that enforce policies and monitor company compliance."""
    agency_name: str = Field(..., description="Name of the government agency that enforces regulations and monitors company compliance")
    jurisdiction: str | None = Field(None, description="Geographic area where this agency has enforcement authority")
    mandate: str | None = Field(None, description="Regulatory powers and responsibilities for overseeing company compliance")
    regulatory_power: str | None = Field(None, description="Types of enforcement actions this agency can take against companies")
    enforcement_history: str | None = Field(None, description="Notable fines, sanctions, or actions taken against companies")


class LegalFramework(BaseModel):
    """Overarching legal systems that establish regulatory authority and company obligations."""
    framework_name: str = Field(..., description="Name of the legal framework that establishes company regulatory obligations")
    framework_type: str | None = Field(None, description="Type of legal instrument: constitutional law, statutory law, regulatory code")
    jurisdiction: str | None = Field(None, description="Geographic scope where companies must comply with this framework")
    domain: str | None = Field(None, description="Regulatory area: data privacy, AI ethics, cybersecurity, financial compliance")
    company_impact: str | None = Field(None, description="How this framework affects company operations and compliance requirements")


class Regulation(BaseModel):
    """Specific regulatory requirements that companies must implement and follow."""
    regulation_name: str = Field(..., description="Specific regulation that creates compliance obligations for companies")
    regulatory_body: str | None = Field(None, description="Agency responsible for enforcing this regulation against companies")
    compliance_deadline: str | None = Field(None, description="Date by which companies must achieve full compliance")
    penalties: str | None = Field(None, description="Fines, sanctions, or penalties for companies that violate this regulation")
    affected_industries: str | None = Field(None, description="Business sectors and company types subject to this regulation")


class LobbyGroup(BaseModel):
    """Organizations that advocate for or against policies on behalf of companies and industries."""
    group_name: str = Field(..., description="Name of organization that lobbies politicians and agencies on behalf of companies")
    focus_area: str | None = Field(None, description="Policy domains where this group advocates for company interests")
    members: str | None = Field(None, description="Companies, industries, or organizations represented by this lobby group")
    position: str | None = Field(None, description="Stance on regulations: supportive of company interests or regulatory compliance")
    lobbying_target: str | None = Field(None, description="Politicians, agencies, or policies this group seeks to influence")


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
    
    async def get_relationship_distribution(self) -> dict:
        """Get distribution of relationship types in the graph."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        try:
            query = """
            MATCH ()-[r]->() 
            WHERE NOT type(r) IN ['MEMBER_OF', 'HAS_EMBEDDING']
            RETURN type(r) as relationship_type, count(*) as count
            ORDER BY count DESC
            LIMIT 10
            """
            
            async with self.client.driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                
                return {
                    rel['relationship_type']: rel['count'] 
                    for rel in records
                }
        except Exception as e:
            logger.warning(f"Failed to get relationship distribution: {e}")
            return {}
    
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
    """Extract document date from content using common patterns."""
    import re
    from datetime import datetime as dt
    
    # Check first 1000 characters for date patterns
    content_start = content[:1000]
    
    # ISO format: 2024-05-27, Published: 2024-05-27
    iso_pattern = r'(?:Published|Date|Updated|Effective):\s*(\d{4}-\d{2}-\d{2})'
    match = re.search(iso_pattern, content_start, re.IGNORECASE)
    if match:
        try:
            date_str = match.group(1)
            parsed_date = dt.strptime(date_str, '%Y-%m-%d')
            if 2020 <= parsed_date.year <= 2030:
                return parsed_date
        except ValueError:
            pass
    
    # YYYY-MM-DD anywhere in text
    date_pattern = r'(\d{4}-\d{1,2}-\d{1,2})'
    matches = re.findall(date_pattern, content_start)
    for match in matches:
        try:
            parsed_date = dt.strptime(match, '%Y-%m-%d')
            if 2020 <= parsed_date.year <= 2030:
                return parsed_date
        except ValueError:
            continue
    
    return None