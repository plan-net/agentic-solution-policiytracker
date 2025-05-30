"""Enhanced LangGraph nodes for political monitoring agent."""

import logging
import asyncio
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferWindowMemory

from .state import AgentState, QueryAnalysis, ToolPlan, ToolResult, ThinkingState
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
from ...prompts.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

# Global references (will be injected)
llm = None
graphiti_client = None
memory = None
prompt_manager = None


def initialize_nodes(llm_instance, graphiti_instance, openai_api_key: str):
    """Initialize global node dependencies."""
    global llm, graphiti_client, memory, prompt_manager
    llm = llm_instance
    graphiti_client = graphiti_instance
    memory = ConversationBufferWindowMemory(
        k=10,  # Keep last 10 exchanges
        return_messages=True,
        memory_key="chat_history"
    )
    prompt_manager = PromptManager()


async def understand_query_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 1: Understand user query using enhanced LLM analysis.
    Uses the query_analysis.md prompt for structured understanding.
    """
    logger.info(f"Understanding query: {state['original_query']}")
    
    try:
        # Load query analysis prompt
        analysis_prompt_content = await prompt_manager.get_prompt("chat/understand_query")
        
        # Get conversation context from memory
        memory_vars = memory.load_memory_variables({})
        conversation_context = memory_vars.get("chat_history", "No previous context")
        
        # Create analysis prompt
        prompt = ChatPromptTemplate.from_template(analysis_prompt_content)
        
        # Run analysis
        chain = prompt | llm | StrOutputParser()
        analysis_result = await chain.ainvoke({
            "user_query": state['original_query']  # Updated variable name
        })
        
        # Parse structured output
        query_analysis = _parse_query_analysis(analysis_result)
        
        logger.info(f"Query analysis complete - Intent: {query_analysis.intent}")
        
        return {
            "processed_query": query_analysis.primary_entity or state['original_query'],
            "query_analysis": query_analysis.model_dump(),  # Convert to dict
            "current_step": "planning",
            "thinking_state": {
                "current_phase": "understanding",
                "thinking_content": [
                    f"Looking at this question, I can see it involves {query_analysis.primary_entity or 'complex entities'}.",
                    f"This appears to be a {query_analysis.intent.lower()} query with {query_analysis.complexity.lower()} complexity.",
                    f"Since this involves regulatory relationships, I'll need graph-based analysis to uncover the full picture."
                ],
                "tool_reasoning": "",
                "synthesis_progress": ""
            }
        }
        
    except Exception as e:
        logger.error(f"Query understanding error: {e}")
        # Fallback analysis
        return {
            "processed_query": state['original_query'],
            "query_analysis": QueryAnalysis(
                intent="general_inquiry",
                complexity="medium",
                analysis_strategy="comprehensive search and analysis"
            ).model_dump(),  # Convert to dict
            "current_step": "planning"
        }


async def plan_tools_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 2: Plan tool execution sequence using tool_planning.md prompt.
    """
    query_analysis = state.get('query_analysis', {})
    logger.info(f"Planning tool execution for intent: {query_analysis.get('intent', 'unknown')}")
    
    try:
        # Load tool planning prompt
        planning_prompt_content = await prompt_manager.get_prompt("chat/plan_exploration")
        
        # Create planning prompt with query analysis results
        prompt = ChatPromptTemplate.from_template(planning_prompt_content)
        
        # Run planning
        chain = prompt | llm | StrOutputParser()
        planning_result = await chain.ainvoke({
            "query_intent": query_analysis.get('intent', 'general_inquiry'),
            "key_entities": ", ".join([query_analysis.get('primary_entity', '')] + query_analysis.get('secondary_entities', [])),
            "temporal_scope": query_analysis.get('temporal_scope', 'current')
        })
        
        # Parse planning result
        tool_plan = _parse_tool_plan(planning_result)
        
        logger.info(f"Tool plan created: {len(tool_plan.tool_sequence)} tools planned")
        
        # Update thinking state
        thinking_state = state.get('thinking_state', {
            'current_phase': 'planning',
            'thinking_content': [],
            'tool_reasoning': '',
            'synthesis_progress': ''
        })
        
        # Add new thinking content
        thinking_content = thinking_state.get('thinking_content', [])
        thinking_content.extend([
            f"My strategy will be to start with a broad search to map the landscape.",
            f"I'll then use {len(tool_plan.tool_sequence)} specialized tools: {', '.join(tool_plan.tool_sequence[:3])}{'...' if len(tool_plan.tool_sequence) > 3 else ''}.",
            f"This multi-layered approach will reveal insights that simple keyword searches would miss."
        ])
        
        return {
            "tool_plan": tool_plan.model_dump(),  # Convert to dict
            "current_step": "execution",
            "thinking_state": {
                "current_phase": "planning",
                "thinking_content": thinking_content,
                "tool_reasoning": thinking_state.get('tool_reasoning', ''),
                "synthesis_progress": thinking_state.get('synthesis_progress', '')
            }
        }
        
    except Exception as e:
        logger.error(f"Tool planning error: {e}")
        # Fallback plan
        return {
            "tool_plan": ToolPlan(
                tool_sequence=["search", "get_entity_details", "get_entity_relationships"],
                rationale="Fallback plan for comprehensive analysis",
                expected_insights="Basic entity information and relationships"
            ).model_dump(),  # Convert to dict
            "current_step": "execution"
        }


async def execute_tools_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 3: Execute planned tools in sequence.
    """
    tool_plan = state.get('tool_plan', {})
    tool_sequence = tool_plan.get('tool_sequence', [])
    logger.info(f"Executing {len(tool_sequence)} tools")
    
    # Initialize all available tools
    tools_map = _create_tools_map()
    
    tool_results = []
    executed_tools = []
    
    # Update thinking state for execution
    thinking_state = state.get('thinking_state', {
        'current_phase': 'execution',
        'thinking_content': [],
        'tool_reasoning': '',
        'synthesis_progress': ''
    })
    thinking_content = thinking_state.get('thinking_content', [])
    
    try:
        logger.info(f"Tool sequence to execute: {tool_sequence}")
        logger.info(f"Available tools: {list(tools_map.keys())}")
        
        for i, tool_name in enumerate(tool_sequence):
            if tool_name not in tools_map:
                logger.warning(f"Tool '{tool_name}' not found, skipping")
                continue
                
            tool = tools_map[tool_name]
            executed_tools.append(tool_name)
            logger.info(f"Executing tool {i+1}/{len(tool_sequence)}: {tool_name}")
            
            # Add thinking output for current tool
            thinking_content.append(
                f"Now using {tool_name} to {_get_tool_purpose(tool_name)}."
            )
            
            try:
                # Execute tool with appropriate input
                tool_input = _prepare_tool_input(tool_name, state)
                result = await tool.arun(tool_input)
                
                tool_result = ToolResult(
                    tool_name=tool_name,
                    success=True,
                    output=result,
                    insights=_extract_insights(result),
                    entities_found=_extract_entities(result)
                )
                
                logger.info(f"Tool {tool_name} executed successfully")
                
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}")
                tool_result = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=str(e)
                )
            
            tool_results.append(tool_result)
            
            # Add brief delay between tools
            await asyncio.sleep(0.5)
            
            # Limit to max 8 tools to prevent excessive execution
            if len(executed_tools) >= 8:
                break
        
        # Add completion thinking
        successful_tools = [r for r in tool_results if r.success]
        thinking_content.append(
            f"Analysis complete. I've successfully executed {len(successful_tools)} tools and gathered comprehensive information."
        )
        
        logger.info(f"Tool execution complete: {len(successful_tools)}/{len(tool_results)} successful")
        
        return {
            "executed_tools": executed_tools,
            "tool_results": [r.model_dump() for r in tool_results],  # Convert to dicts
            "current_step": "synthesis",
            "thinking_state": {
                "current_phase": "execution",
                "thinking_content": thinking_content,
                "tool_reasoning": thinking_state.get('tool_reasoning', ''),
                "synthesis_progress": thinking_state.get('synthesis_progress', '')
            }
        }
        
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            "executed_tools": executed_tools,
            "tool_results": [r.model_dump() for r in tool_results],  # Convert to dicts
            "current_step": "synthesis"
        }


async def synthesize_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 4: Synthesize final response using synthesis.md prompt.
    """
    tool_results = state.get('tool_results', [])
    logger.info(f"Synthesizing response from {len(tool_results)} tool results")
    
    try:
        # Load synthesis prompt
        synthesis_prompt_content = await prompt_manager.get_prompt("chat/format_response")
        
        # Prepare tool results for synthesis
        tool_results_text = _format_tool_results(tool_results)
        tools_used = [r['tool_name'] for r in tool_results if r.get('success')]
        
        # Create synthesis prompt
        prompt = ChatPromptTemplate.from_template(synthesis_prompt_content)
        
        # Run synthesis
        chain = prompt | llm | StrOutputParser()
        final_response = await chain.ainvoke({
            "original_query": state.get('original_query', ''),
            "all_search_results": tool_results_text,
            "confidence_level": "High" if len([r for r in tool_results if r.get('success')]) > 2 else "Medium"
        })
        
        # Update memory with this conversation
        memory.save_context(
            {"input": state.get('original_query', '')},
            {"output": final_response}
        )
        
        logger.info("Response synthesis complete")
        
        return {
            "final_response": final_response,
            "synthesis_complete": True,
            "current_step": "complete"
        }
        
    except Exception as e:
        logger.error(f"Response synthesis error: {e}")
        # Fallback response
        successful_results = [r for r in tool_results if r.get('success')]
        fallback_response = f"I found information from {len(successful_results)} sources, but encountered an error during synthesis: {str(e)}"
        
        return {
            "final_response": fallback_response,
            "synthesis_complete": True,
            "current_step": "complete"
        }


# Helper functions

def _parse_query_analysis(analysis_text: str) -> QueryAnalysis:
    """Parse LLM analysis output into QueryAnalysis object."""
    lines = analysis_text.strip().split('\n')
    parsed = {}
    entities = []
    
    for line in lines:
        if ':' in line:
            # Remove markdown formatting
            clean_line = line.replace('**', '').strip()
            if clean_line.startswith('- '):
                # This is an entity line
                entity_name = clean_line.split(':')[0].replace('- ', '').strip()
                entities.append(entity_name)
            else:
                # Regular key:value line
                key, value = clean_line.split(':', 1)
                key_normalized = key.strip().lower().replace(' ', '_')
                parsed[key_normalized] = value.strip()
    
    # Extract primary entity from entities list or parsed data
    primary_entity = None
    if entities:
        primary_entity = entities[0]
    elif 'primary_entity' in parsed:
        primary_entity = parsed['primary_entity']
    
    return QueryAnalysis(
        intent=parsed.get('intent', 'general_inquiry'),
        complexity=parsed.get('complexity', 'medium'),
        primary_entity=primary_entity,
        secondary_entities=entities[1:] if len(entities) > 1 else [],
        key_relationships=parsed.get('key_relationships', '').split(', ') if parsed.get('key_relationships') else [],
        temporal_scope=parsed.get('temporal_scope', 'current'),
        analysis_strategy=parsed.get('search_strategy', parsed.get('analysis_strategy', 'comprehensive exploration'))
    )


def _parse_tool_plan(planning_text: str) -> ToolPlan:
    """Parse tool planning output into ToolPlan object."""
    lines = planning_text.strip().split('\n')
    
    tool_sequence = []
    rationale = ""
    expected_insights = ""
    
    for line in lines:
        if line.startswith('**Tool Sequence**:'):
            # Extract tool list from line
            tools_part = line.split(':', 1)[1].strip()
            # Simple parsing - look for tool names in brackets or comma-separated
            if '[' in tools_part and ']' in tools_part:
                tools_text = tools_part.split('[')[1].split(']')[0]
                tool_sequence = [t.strip() for t in tools_text.split(',')]
        elif line.startswith('**Rationale**:'):
            rationale = line.split(':', 1)[1].strip()
        elif line.startswith('**Expected Insights**:'):
            expected_insights = line.split(':', 1)[1].strip()
    
    # Fallback tool sequence if parsing failed
    if not tool_sequence:
        tool_sequence = ["search", "get_entity_details", "get_entity_relationships"]
    
    return ToolPlan(
        tool_sequence=tool_sequence,
        rationale=rationale,
        expected_insights=expected_insights
    )


def _create_tools_map() -> Dict[str, Any]:
    """Create mapping of tool names to tool instances."""
    if not graphiti_client:
        logger.error("ERROR: graphiti_client is None! Tools cannot be initialized.")
        return {}
    
    logger.info(f"Creating tools map with graphiti_client: {graphiti_client}")
    return {
        "search": GraphitiSearchTool(graphiti_client),
        "get_entity_details": EntityDetailsTool(graphiti_client),
        "get_entity_relationships": EntityRelationshipsTool(graphiti_client),
        "get_entity_timeline": EntityTimelineTool(graphiti_client),
        "find_similar_entities": SimilarEntitesTool(graphiti_client),
        "traverse_from_entity": TraverseFromEntityTool(graphiti_client),
        "find_paths_between_entities": FindPathsTool(graphiti_client),
        "get_entity_neighbors": GetNeighborsTool(graphiti_client),
        "analyze_entity_impact": ImpactAnalysisTool(graphiti_client),
        "search_by_date_range": DateRangeSearchTool(graphiti_client),
        "get_entity_history": EntityHistoryTool(graphiti_client),
        "find_concurrent_events": ConcurrentEventsTool(graphiti_client),
        "track_policy_evolution": PolicyEvolutionTool(graphiti_client),
        "get_communities": GetCommunitiesTool(graphiti_client),
        "get_community_members": CommunityMembersTool(graphiti_client),
        "get_policy_clusters": PolicyClustersTool(graphiti_client)
    }


def _get_tool_purpose(tool_name: str) -> str:
    """Get human-readable purpose for tool."""
    purposes = {
        "search": "find relevant facts and entities",
        "get_entity_details": "get comprehensive entity information",
        "get_entity_relationships": "explore entity connections",
        "get_entity_timeline": "track entity evolution over time",
        "find_similar_entities": "find related entities",
        "traverse_from_entity": "explore multi-hop relationships",
        "find_paths_between_entities": "find connection paths",
        "get_entity_neighbors": "get immediate neighbors",
        "analyze_entity_impact": "analyze impact networks",
        "search_by_date_range": "search temporal events",
        "get_entity_history": "track historical changes",
        "find_concurrent_events": "find concurrent events",
        "track_policy_evolution": "track policy changes",
        "get_communities": "discover entity communities",
        "get_community_members": "get community members",
        "get_policy_clusters": "identify policy clusters"
    }
    return purposes.get(tool_name, "perform analysis")


def _prepare_tool_input(tool_name: str, state: Dict[str, Any]) -> str:
    """Prepare appropriate input for each tool."""
    query = state.get('processed_query', state.get('original_query', ''))
    
    # Use primary entity if available for entity-specific tools
    query_analysis = state.get('query_analysis', {})
    primary_entity = query_analysis.get('primary_entity')
    
    if primary_entity:
        entity_tools = [
            "get_entity_details", "get_entity_relationships", "get_entity_timeline",
            "find_similar_entities", "traverse_from_entity", "get_entity_neighbors",
            "analyze_entity_impact", "get_entity_history"
        ]
        if tool_name in entity_tools:
            return primary_entity
    
    return query


def _extract_insights(result: str) -> List[str]:
    """Extract key insights from tool result."""
    if not result or len(result) < 20:
        return []
    
    insights = []
    if "entities" in result.lower():
        insights.append("Entity network identified")
    if "relationship" in result.lower():
        insights.append("Relationships mapped")
    if "impact" in result.lower():
        insights.append("Impact patterns found")
    if "temporal" in result.lower() or "timeline" in result.lower():
        insights.append("Temporal patterns discovered")
    
    return insights[:3]  # Limit to top 3 insights


def _extract_entities(result: str) -> List[str]:
    """Extract entity names from tool result."""
    import re
    if not result:
        return []
    
    # Simple entity extraction using common patterns
    entity_patterns = [
        r'\b(EU|European Union|GDPR|AI Act|DSA|DMA)\b',
        r'\b([A-Z][a-z]+ Act)\b',
        r'\b(Meta|Google|Apple|Microsoft|Amazon)\b'
    ]
    
    entities = []
    for pattern in entity_patterns:
        matches = re.findall(pattern, result)
        entities.extend([m for m in matches if isinstance(m, str)])
    
    return list(set(entities))[:5]  # Limit and deduplicate


def _format_tool_results(tool_results: List[Dict[str, Any]]) -> str:
    """Format tool results for synthesis prompt."""
    formatted = []
    
    for result in tool_results:
        if result.get('success') and result.get('output'):
            formatted.append(f"**{result['tool_name']}**: {result['output'][:500]}...")
        elif not result.get('success'):
            formatted.append(f"**{result['tool_name']}**: Failed - {result.get('error', 'Unknown error')}")
    
    return "\n\n".join(formatted)