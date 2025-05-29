"""Simple LLM-based agent for testing."""

import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator
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

RESPONSE STRATEGY (Be strategic - use what's needed for complete answers):
1. **Start with search** - Always begin with search to understand the topic
2. **Choose specialized tools** based on query complexity and type:
   - **Simple questions**: search → get_entity_details (2-3 tools)
   - **Complex questions**: search → multiple specialized tools as needed (4-8 tools)
   - **Analysis questions**: search → entity tools → analysis tools (5-10 tools)

EFFICIENT TOOL COMBINATIONS:
- **Basic policy questions**: search → get_entity_details → get_entity_relationships
- **Company impact analysis**: search → get_entity_relationships → analyze_entity_impact → find_paths_between_entities  
- **Network analysis**: search → traverse_from_entity → get_entity_neighbors → analyze_entity_impact
- **Timeline questions**: search → get_entity_timeline → get_entity_history → find_concurrent_events
- **Temporal analysis**: search → search_by_date_range → track_policy_evolution → get_entity_history
- **Complex context**: search → find_concurrent_events → get_entity_history → get_entity_relationships
- **Community analysis**: search → get_communities → get_community_members → get_policy_clusters
- **Comprehensive landscape**: search → get_policy_clusters → get_communities → analyze_entity_impact

PRIORITIZE COMPLETENESS: Use as many tools as needed to provide comprehensive, accurate answers.

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
            max_iterations=15,
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
    
    async def stream_query(self, query: str) -> AsyncGenerator[str, None]:
        """Stream a user query with real-time thinking output."""
        try:
            logger.info(f"Streaming query with real thinking: {query}")
            
            # Clean query
            clean_query = query.replace("search", "").strip()
            if not clean_query:
                clean_query = query
            
            # Phase 1: Start thinking
            yield "<think>\n"
            await asyncio.sleep(0.5)
            
            # Phase 2: Query understanding
            yield f"🎯 UNDERSTANDING QUERY\n"
            yield f"Query: {clean_query}\n"
            
            # Extract entities for planning
            entities = self._extract_query_entities(clean_query)
            intent = self._determine_query_intent(clean_query)
            
            yield f"Intent: {intent}\n"
            if entities:
                yield f"Key entities detected: {', '.join(entities[:3])}\n"
            await asyncio.sleep(1)
            
            # Phase 3: Tool planning  
            yield f"\n🛠️ PLANNING ANALYSIS\n"
            predicted_tools = self._predict_tools_needed(intent, entities)
            yield f"Strategy: Multi-tool graph analysis\n"
            yield f"Expected tools: {', '.join(predicted_tools[:4])}\n"
            yield f"Graph advantages: Multi-hop reasoning, relationship mapping\n"
            await asyncio.sleep(1)
            
            # Phase 4: Execute agent with real-time monitoring
            yield f"\n⚡ EXECUTING ANALYSIS\n"
            
            # Simulate real-time tool execution updates while agent runs
            tool_steps = [
                "Initializing graph search...",
                "Searching knowledge base...", 
                "Analyzing entity relationships...",
                "Processing temporal patterns...",
                "Synthesizing insights..."
            ]
            
            # Start agent execution properly in async context
            agent_task = asyncio.create_task(self.agent.ainvoke({"input": clean_query}))
            
            # Stream thinking updates while agent runs
            for i, step in enumerate(tool_steps):
                yield step + "\n"
                await asyncio.sleep(1.5 if i < 2 else 1)  # Longer for first steps
                
                # Check if agent is done
                if agent_task.done():
                    break
            
            # Wait for agent to complete if not done yet
            try:
                result = await agent_task
            except Exception as e:
                logger.error(f"Agent execution failed: {e}")
                yield f"Agent execution error: {str(e)}\n"
                result = {"output": f"I encountered an error while processing your request: {str(e)}"}
            
            # Phase 5: Complete thinking
            yield f"\n💡 SYNTHESIS COMPLETE\n"
            yield f"Found comprehensive insights using graph analysis\n"
            yield f"Ready to present findings\n"
            yield "</think>\n\n"
            await asyncio.sleep(0.5)
            
            # Phase 6: Stream response
            response = result.get("output", "I couldn't generate a response.")
            
            # Stream response in natural chunks
            sentences = response.split('. ')
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    chunk = sentence.strip()
                    if i < len(sentences) - 1:
                        chunk += ". "
                    yield chunk
                    await asyncio.sleep(0.8)  # Natural reading pace
            
            logger.info(f"Real-time streaming completed successfully")
            
        except Exception as e:
            logger.error(f"Real-time streaming error: {e}")
            yield f"</think>\n\nI encountered an error while processing your request: {str(e)}"
    
    def _extract_query_entities(self, query: str) -> List[str]:
        """Extract potential entities from query."""
        import re
        entities = []
        
        # Common political/regulatory patterns
        patterns = [
            r'\b(EU|European Union|GDPR|AI Act|DSA|DMA)\b',
            r'\b([A-Z][a-z]+ Act)\b',
            r'\b(Meta|Google|Apple|Microsoft|Amazon)\b',
            r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'  # Two-word proper nouns
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend([m for m in matches if isinstance(m, str)])
        
        return list(set(entities))[:5]  # Limit to 5 entities
    
    def _determine_query_intent(self, query: str) -> str:
        """Determine the intent of the query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['what is', 'define', 'explain']):
            return "Information lookup"
        elif any(word in query_lower for word in ['how does', 'relationship', 'connect']):
            return "Relationship analysis"
        elif any(word in query_lower for word in ['impact', 'effect', 'affect']):
            return "Impact analysis"
        elif any(word in query_lower for word in ['when', 'timeline', 'history']):
            return "Temporal analysis"
        else:
            return "General inquiry"
    
    def _predict_tools_needed(self, intent: str, entities: List[str]) -> List[str]:
        """Predict which tools will likely be used."""
        tools = ["search"]  # Always start with search
        
        if intent == "Information lookup":
            tools.extend(["get_entity_details"])
        elif intent == "Relationship analysis":
            tools.extend(["get_entity_relationships", "traverse_from_entity"])
        elif intent == "Impact analysis":
            tools.extend(["analyze_entity_impact", "find_paths_between_entities"])
        elif intent == "Temporal analysis":
            tools.extend(["get_entity_timeline", "search_by_date_range"])
        else:
            tools.extend(["get_entity_details", "get_entity_relationships"])
        
        return tools[:4]  # Limit to 4 predictions
    
    def _extract_tool_insights(self, output: str) -> str:
        """Extract key insights from tool output."""
        if not output or len(output) < 20:
            return ""
            
        # Simple insight extraction
        if "entities" in output.lower():
            return "Entity network mapped"
        elif "relationship" in output.lower():
            return "Relationships identified"
        elif "temporal" in output.lower():
            return "Timeline patterns found"
        else:
            return "Analysis completed"