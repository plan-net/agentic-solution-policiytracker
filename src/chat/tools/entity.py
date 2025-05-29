"""Entity-focused tools for exploring the knowledge graph."""

import logging
from typing import List, Dict, Any, Optional, Type
from datetime import datetime, timedelta
from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field
from graphiti_core import Graphiti

logger = logging.getLogger(__name__)


class EntityDetailsInput(BaseModel):
    """Input schema for entity details tool."""
    entity_name: str = Field(description="Name of the entity to get details for")
    entity_type: Optional[str] = Field(default=None, description="Type of entity (Policy, Company, Politician, etc.)")


class EntityRelationshipsInput(BaseModel):
    """Input schema for entity relationships tool."""
    entity_name: str = Field(description="Name of the entity to find relationships for")
    max_relationships: int = Field(default=10, description="Maximum number of relationships to return")
    relationship_types: Optional[List[str]] = Field(default=None, description="Specific relationship types to filter for")


class EntityTimelineInput(BaseModel):
    """Input schema for entity timeline tool."""
    entity_name: str = Field(description="Name of the entity to get timeline for")
    days_back: int = Field(default=365, description="Number of days back to search for timeline events")


class SimilarEntitiesInput(BaseModel):
    """Input schema for similar entities tool."""
    entity_name: str = Field(description="Name of the entity to find similar entities for")
    max_similar: int = Field(default=5, description="Maximum number of similar entities to return")


class EntityDetailsTool(BaseTool):
    """Tool for getting detailed information about a specific entity."""
    
    name: str = "get_entity_details"
    description: str = "Get comprehensive details about a specific entity (policy, company, politician, etc.) including its properties and basic context."
    args_schema: Type[BaseModel] = EntityDetailsInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, entity_name: str, entity_type: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, entity_name: str, entity_type: Optional[str] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get detailed information about an entity."""
        try:
            logger.info(f"Getting details for entity: {entity_name}")
            
            # Search for the entity with focus on getting comprehensive information
            search_query = f"{entity_name} details properties characteristics"
            if entity_type:
                search_query += f" type:{entity_type}"
            
            # Use advanced search with node-focused configuration
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
            search_results = await self.client._search(search_query, config=NODE_HYBRID_SEARCH_RRF)
            
            # Extract results from both edges and nodes
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, 'nodes') and search_results.nodes:
                results.extend(search_results.nodes)
            
            if not results:
                return f"No information found for entity '{entity_name}'"
            
            # Aggregate information about the entity
            entity_facts = []
            entity_properties = set()
            source_episodes = set()
            
            for result in results[:10]:  # Top 10 most relevant results
                # Handle both edges (facts) and nodes (summaries)
                content = ""
                if hasattr(result, 'fact') and result.fact:
                    content = result.fact
                elif hasattr(result, 'summary') and result.summary:
                    content = result.summary
                
                if content and entity_name.lower() in content.lower():
                    entity_facts.append(content)
                    
                    # Extract properties/characteristics
                    if hasattr(result, 'episodes') and result.episodes:
                        source_episodes.update([str(ep) for ep in result.episodes])
            
            # Format comprehensive response
            response = f"## Entity Details: {entity_name}\n\n"
            
            if entity_type:
                response += f"**Type**: {entity_type}\n\n"
            
            response += "**Key Information:**\n"
            for i, fact in enumerate(entity_facts[:8], 1):
                response += f"{i}. {fact}\n"
            
            if source_episodes:
                response += f"\n**Information Sources**: Found in {len(source_episodes)} document(s)\n"
            
            if len(entity_facts) > 8:
                response += f"\n... and {len(entity_facts) - 8} more facts available."
            
            logger.info(f"Retrieved {len(entity_facts)} facts for entity {entity_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting entity details: {e}")
            return f"Error retrieving details for {entity_name}: {str(e)}"


class EntityRelationshipsTool(BaseTool):
    """Tool for exploring relationships from a specific entity."""
    
    name: str = "get_entity_relationships"
    description: str = "Explore what other entities are connected to this entity and how they are related. Shows the network of relationships."
    args_schema: Type[BaseModel] = EntityRelationshipsInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, entity_name: str, max_relationships: int = 10, relationship_types: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, entity_name: str, max_relationships: int = 10, relationship_types: Optional[List[str]] = None, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get relationships for an entity."""
        try:
            logger.info(f"Finding relationships for entity: {entity_name}")
            
            # Search for relationships involving this entity
            search_query = f"{entity_name} relationship connection affects influences involves"
            if relationship_types:
                search_query += " " + " ".join(relationship_types)
            
            # Use advanced search with edge-focused configuration for relationships
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)
            
            # Extract edges for relationship analysis
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            
            if not results:
                return f"No relationships found for entity '{entity_name}'"
            
            # Process relationships
            relationships = []
            relationship_counts = {}
            
            for result in results[:max_relationships * 2]:  # Get more to filter
                fact = result.fact
                
                # Look for relationship patterns in facts
                if entity_name.lower() in fact.lower():
                    # Extract the relationship type if available
                    rel_type = getattr(result, 'name', 'RELATED_TO')
                    
                    relationships.append({
                        'fact': fact,
                        'type': rel_type,
                        'episodes': getattr(result, 'episodes', [])
                    })
                    
                    # Count relationship types
                    relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1
            
            # Format response
            response = f"## Relationships for: {entity_name}\n\n"
            
            if relationship_counts:
                response += "**Relationship Types:**\n"
                for rel_type, count in sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True):
                    response += f"- {rel_type}: {count} connections\n"
                response += "\n"
            
            response += "**Key Relationships:**\n"
            for i, rel in enumerate(relationships[:max_relationships], 1):
                response += f"{i}. [{rel['type']}] {rel['fact']}\n"
            
            if len(relationships) > max_relationships:
                response += f"\n... and {len(relationships) - max_relationships} more relationships available."
            
            logger.info(f"Found {len(relationships)} relationships for {entity_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting entity relationships: {e}")
            return f"Error retrieving relationships for {entity_name}: {str(e)}"


class EntityTimelineTool(BaseTool):
    """Tool for tracking how an entity has evolved over time."""
    
    name: str = "get_entity_timeline"
    description: str = "Track how an entity has evolved, changed, or been mentioned over time. Shows temporal progression of events."
    args_schema: Type[BaseModel] = EntityTimelineInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, entity_name: str, days_back: int = 365, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, entity_name: str, days_back: int = 365, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get timeline of entity evolution."""
        try:
            logger.info(f"Getting timeline for entity: {entity_name} ({days_back} days back)")
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            # Search for temporal mentions of the entity
            search_query = f"{entity_name} timeline history evolution changes development"
            
            # Use advanced search with edge-focused configuration for temporal analysis
            from graphiti_core.search.search_config_recipes import EDGE_HYBRID_SEARCH_RRF
            search_results = await self.client._search(search_query, config=EDGE_HYBRID_SEARCH_RRF)
            
            # Extract edges for timeline analysis
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            
            if not results:
                return f"No timeline information found for entity '{entity_name}'"
            
            # Try to extract temporal information from facts
            timeline_events = []
            
            for result in results:
                fact = result.fact
                if entity_name.lower() in fact.lower():
                    # Try to extract date/time information from the fact
                    event = {
                        'fact': fact,
                        'episodes': getattr(result, 'episodes', []),
                        'timestamp': None  # Would need episode details to get exact timestamp
                    }
                    
                    # Look for temporal keywords in the fact
                    temporal_keywords = ['announced', 'released', 'published', 'enacted', 'implemented', 'proposed', 'approved']
                    for keyword in temporal_keywords:
                        if keyword in fact.lower():
                            event['type'] = keyword
                            break
                    
                    timeline_events.append(event)
            
            # Format timeline response
            response = f"## Timeline for: {entity_name}\n\n"
            response += f"**Time Range**: Last {days_back} days\n\n"
            
            if timeline_events:
                response += "**Key Timeline Events:**\n"
                for i, event in enumerate(timeline_events[:10], 1):
                    event_type = event.get('type', 'Event')
                    response += f"{i}. **{event_type.title()}**: {event['fact']}\n"
                
                if len(timeline_events) > 10:
                    response += f"\n... and {len(timeline_events) - 10} more timeline events available."
            else:
                response += f"No specific timeline events found for {entity_name} in the last {days_back} days."
            
            # Note about temporal precision
            response += "\n\n*Note: Timeline precision depends on document timestamps. Use temporal search tools for more precise date-based queries.*"
            
            logger.info(f"Found {len(timeline_events)} timeline events for {entity_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting entity timeline: {e}")
            return f"Error retrieving timeline for {entity_name}: {str(e)}"


class SimilarEntitesTool(BaseTool):
    """Tool for finding entities similar to a given entity."""
    
    name: str = "find_similar_entities"
    description: str = "Find entities that are similar or related to the given entity based on graph structure and context."
    args_schema: Type[BaseModel] = SimilarEntitiesInput
    
    client: Graphiti = None
    
    def __init__(self, graphiti_client: Graphiti, **kwargs):
        super().__init__(**kwargs)
        self.client = graphiti_client
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, entity_name: str, max_similar: int = 5, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute synchronously - placeholder."""
        return "Sync not implemented - use async version"
    
    async def _arun(self, entity_name: str, max_similar: int = 5, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Find similar entities."""
        try:
            logger.info(f"Finding similar entities to: {entity_name}")
            
            # Search for similar entities using context and relationships
            search_query = f"{entity_name} similar like comparable equivalent type category"
            
            # Use advanced search with node-focused configuration for entity similarity
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
            search_results = await self.client._search(search_query, config=NODE_HYBRID_SEARCH_RRF)
            
            # Extract both nodes and edges for similarity analysis
            results = []
            if hasattr(search_results, 'edges') and search_results.edges:
                results.extend(search_results.edges)
            if hasattr(search_results, 'nodes') and search_results.nodes:
                results.extend(search_results.nodes)
            
            if not results:
                return f"No similar entities found for '{entity_name}'"
            
            # Extract potential similar entities from facts
            similar_entities = {}
            
            for result in results:
                fact = result.fact
                
                # Extract entity names that appear with the target entity
                # This is a simplified approach - in practice would need NER
                words = fact.lower().split()
                
                # Look for capitalized phrases that might be entity names
                import re
                entity_patterns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', fact)
                
                for potential_entity in entity_patterns:
                    if potential_entity != entity_name and len(potential_entity) > 2:
                        if potential_entity not in similar_entities:
                            similar_entities[potential_entity] = []
                        similar_entities[potential_entity].append(fact)
            
            # Rank by frequency of co-occurrence
            ranked_similar = sorted(similar_entities.items(), 
                                  key=lambda x: len(x[1]), reverse=True)[:max_similar]
            
            # Format response
            response = f"## Similar Entities to: {entity_name}\n\n"
            
            if ranked_similar:
                response += "**Most Similar Entities:**\n"
                for i, (similar_entity, contexts) in enumerate(ranked_similar, 1):
                    response += f"{i}. **{similar_entity}** (appears together in {len(contexts)} context(s))\n"
                    # Show one example context
                    if contexts:
                        response += f"   Example: {contexts[0][:100]}...\n"
                response += "\n"
            else:
                response += f"No clearly similar entities identified for {entity_name}.\n\n"
            
            # Suggest using community detection for better similarity
            response += "*Note: For more sophisticated similarity analysis, consider using community detection tools to find entities in the same cluster.*"
            
            logger.info(f"Found {len(ranked_similar)} similar entities for {entity_name}")
            return response
            
        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return f"Error finding similar entities to {entity_name}: {str(e)}"