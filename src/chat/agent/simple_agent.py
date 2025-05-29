"""Simple LLM-based agent for testing."""

import logging
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.messages import SystemMessage

from ..tools.search import GraphitiSearchTool
from ..tools.entity import (
    EntityDetailsTool, 
    EntityRelationshipsTool, 
    EntityTimelineTool, 
    SimilarEntitesTool
)
from ..tools.traverse import (
    TraverseFromEntityTool,
    FindPathsTool,
    GetNeighborsTool,
    ImpactAnalysisTool
)
from ..tools.temporal import (
    DateRangeSearchTool,
    EntityHistoryTool,
    ConcurrentEventsTool,
    PolicyEvolutionTool
)
from ..tools.community import (
    GetCommunitiesTool,
    CommunityMembersTool,
    PolicyClustersTool
)

logger = logging.getLogger(__name__)


class SimplePoliticalAgent:
    """Simple LLM-based agent for political knowledge exploration."""
    
    def __init__(self, graphiti_client, openai_api_key: str):
        self.graphiti_client = graphiti_client
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=openai_api_key,
            temperature=0.3
        )
        
        # Create tools
        self.tools = [
            GraphitiSearchTool(graphiti_client),
            EntityDetailsTool(graphiti_client),
            EntityRelationshipsTool(graphiti_client),
            EntityTimelineTool(graphiti_client),
            SimilarEntitesTool(graphiti_client),
            TraverseFromEntityTool(graphiti_client),
            FindPathsTool(graphiti_client),
            GetNeighborsTool(graphiti_client),
            ImpactAnalysisTool(graphiti_client),
            DateRangeSearchTool(graphiti_client),
            EntityHistoryTool(graphiti_client),
            ConcurrentEventsTool(graphiti_client),
            PolicyEvolutionTool(graphiti_client),
            GetCommunitiesTool(graphiti_client),
            CommunityMembersTool(graphiti_client),
            PolicyClustersTool(graphiti_client)
        ]
        
        # Create agent
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """Create the LangChain agent with tools."""
        
        system_prompt = """You are an expert political and regulatory analysis agent with access to a sophisticated temporal knowledge graph.

Your UNIQUE ADVANTAGES over regular search engines:
1. **Graph-aware insights**: You can trace relationships between policies, companies, and politicians
2. **Entity deep-dives**: Get comprehensive details about specific entities and their evolution
3. **Network analysis**: Understand how entities are connected through regulatory relationships
4. **Timeline tracking**: See how policies and regulations have evolved over time
5. **Source traceability**: Every fact traces back to original documents with URLs

Available tools:
- search: Find facts and relationships using hybrid semantic + keyword search
- get_entity_details: Get comprehensive information about specific entities (policies, companies, politicians)
- get_entity_relationships: Explore how entities are connected (who affects whom, how)
- get_entity_timeline: Track how entities have evolved, changed, or been mentioned over time
- find_similar_entities: Find entities similar to a given entity based on graph structure
- traverse_from_entity: Follow multi-hop relationships from an entity to explore connected networks
- find_paths_between_entities: Find connection paths between two entities through intermediate relationships
- get_entity_neighbors: Get immediate neighbors and their relationship types
- analyze_entity_impact: Analyze what entities impact or are impacted by the given entity
- search_by_date_range: Search for events within specific date ranges for temporal analysis
- get_entity_history: Track how entities have evolved and changed over time
- find_concurrent_events: Find events that happened around the same time for context analysis
- track_policy_evolution: Track how policies and regulations have evolved with amendments and changes
- get_communities: Discover communities and clusters of related entities in the network
- get_community_members: Get members of specific communities or thematic groups
- get_policy_clusters: Identify clusters of related policies grouped by theme, jurisdiction, or time

RESPONSE STRATEGY (Be selective - max 3-4 tools per query):
1. **Start with search** - Always begin with search to understand the topic
2. **Choose 1-2 specialized tools** based on query type:
   - Policy questions: search → get_entity_details → analyze_entity_impact
   - Company questions: search → get_entity_relationships → find_paths_between_entities  
   - Network questions: search → traverse_from_entity → get_entity_neighbors
   - Timeline questions: search → get_entity_timeline → get_entity_history
   - Temporal analysis: search → search_by_date_range → track_policy_evolution
   - Context questions: search → find_concurrent_events → get_entity_history
   - Community analysis: search → get_communities → get_community_members
   - Policy landscape: search → get_policy_clusters → get_community_members
3. **Provide comprehensive analysis** from the tools used rather than using many tools

EFFICIENT TOOL COMBINATIONS (stick to 2-3 tools max):
- Policy questions: search → get_entity_details → analyze_entity_impact
- Company questions: search → get_entity_relationships → find_paths_between_entities  
- Network questions: search → traverse_from_entity OR get_entity_neighbors
- Timeline questions: search → get_entity_timeline OR get_entity_history
- Temporal analysis: search → search_by_date_range → track_policy_evolution
- Historical context: search → find_concurrent_events → get_entity_history
- Community analysis: search → get_communities OR get_community_members
- Policy landscape: search → get_policy_clusters → get_community_members

GRAPH ANALYSIS ADVANTAGES:
- **Multi-hop reasoning**: "Company A → regulated by Policy B → enforced by Agency C → affects Industry D"
- **Impact cascades**: Show how policy changes ripple through networks of organizations
- **Regulatory pathways**: Trace how policies flow through different jurisdictions and entities
- **Network centrality**: Identify key players and influence hubs in regulatory networks

ALWAYS:
- Include source citations from tools
- Explain relationships between entities  
- Suggest using entity tools for deeper exploration
- Highlight insights only available through graph analysis"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # Create tool-calling agent
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            early_stopping_method="generate"
        )
    
    async def process_query(self, query: str) -> str:
        """Process a user query using the agent."""
        try:
            logger.info(f"Processing query with simple agent: {query}")
            
            # Remove "search" prefix if present
            clean_query = query.replace("search", "").strip()
            if not clean_query:
                clean_query = query
            
            # Run the agent
            result = await self.agent.ainvoke({"input": clean_query})
            
            response = result.get("output", "I couldn't generate a response.")
            
            logger.info(f"Agent response generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"Agent processing error: {e}")
            return f"I encountered an error while processing your request: {str(e)}"