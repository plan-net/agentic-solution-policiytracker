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


async def understand_query_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: Understand user query using enhanced LLM analysis.
    Uses the query_analysis.md prompt for structured understanding.
    """
    logger.info(f"Understanding query: {state.original_query}")
    
    try:
        # Load query analysis prompt
        analysis_prompt_content = await prompt_manager.get_prompt("query_analysis")
        
        # Get conversation context from memory
        memory_vars = memory.load_memory_variables({})
        conversation_context = memory_vars.get("chat_history", "No previous context")
        
        # Create analysis prompt
        prompt = ChatPromptTemplate.from_template(analysis_prompt_content)
        
        # Run analysis
        chain = prompt | llm | StrOutputParser()
        analysis_result = await chain.ainvoke({
            "query": state.original_query,
            "conversation_context": str(conversation_context)
        })
        
        # Parse structured output
        query_analysis = _parse_query_analysis(analysis_result)
        
        logger.info(f"Query analysis complete - Intent: {query_analysis.intent}")
        
        return {
            "processed_query": query_analysis.primary_entity or state.original_query,
            "query_analysis": query_analysis,
            "current_step": "planning",
            "thinking_state": ThinkingState(
                current_phase="understanding",
                thinking_content=[
                    f"Looking at this question, I can see it involves {query_analysis.primary_entity or 'complex entities'}.",
                    f"This appears to be a {query_analysis.intent.lower()} query with {query_analysis.complexity.lower()} complexity.",
                    f"Since this involves regulatory relationships, I'll need graph-based analysis to uncover the full picture."
                ]
            )
        }
        
    except Exception as e:
        logger.error(f"Query understanding error: {e}")
        # Fallback analysis
        return {
            "processed_query": state.original_query,
            "query_analysis": QueryAnalysis(
                intent="general_inquiry",
                complexity="medium",
                analysis_strategy="comprehensive search and analysis"
            ),
            "current_step": "planning"
        }


async def plan_tools_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: Plan tool execution sequence using tool_planning.md prompt.
    """
    logger.info(f"Planning tool execution for intent: {state.query_analysis.intent}")
    
    try:
        # Load tool planning prompt
        planning_prompt_content = await prompt_manager.get_prompt("tool_planning")
        
        # Create planning prompt with query analysis results
        prompt = ChatPromptTemplate.from_template(planning_prompt_content)
        
        # Run planning
        chain = prompt | llm | StrOutputParser()
        planning_result = await chain.ainvoke({
            "intent": state.query_analysis.intent,
            "complexity": state.query_analysis.complexity,
            "primary_entity": state.query_analysis.primary_entity or "Unknown",
            "secondary_entities": ", ".join(state.query_analysis.secondary_entities),
            "strategy": state.query_analysis.analysis_strategy
        })
        
        # Parse planning result
        tool_plan = _parse_tool_plan(planning_result)
        
        logger.info(f"Tool plan created: {len(tool_plan.tool_sequence)} tools planned")
        
        # Update thinking state
        new_thinking = state.thinking_state
        new_thinking.current_phase = "planning"
        new_thinking.thinking_content.extend([
            f"My strategy will be to start with a broad search to map the landscape.",
            f"I'll then use {len(tool_plan.tool_sequence)} specialized tools: {', '.join(tool_plan.tool_sequence[:3])}{'...' if len(tool_plan.tool_sequence) > 3 else ''}.",
            f"This multi-layered approach will reveal insights that simple keyword searches would miss."
        ])
        
        return {
            "tool_plan": tool_plan,
            "current_step": "execution",
            "thinking_state": new_thinking
        }
        
    except Exception as e:
        logger.error(f"Tool planning error: {e}")
        # Fallback plan
        return {
            "tool_plan": ToolPlan(
                tool_sequence=["search", "get_entity_details", "get_entity_relationships"],
                rationale="Fallback plan for comprehensive analysis",
                expected_insights="Basic entity information and relationships"
            ),
            "current_step": "execution"
        }


async def execute_tools_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 3: Execute planned tools in sequence.
    """
    logger.info(f"Executing {len(state.tool_plan.tool_sequence)} tools")
    
    # Initialize all available tools
    tools_map = _create_tools_map()
    
    tool_results = []
    executed_tools = []
    
    # Update thinking state for execution
    new_thinking = state.thinking_state
    new_thinking.current_phase = "execution"
    
    try:
        for i, tool_name in enumerate(state.tool_plan.tool_sequence):
            if tool_name not in tools_map:
                logger.warning(f"Tool '{tool_name}' not found, skipping")
                continue
                
            tool = tools_map[tool_name]
            executed_tools.append(tool_name)
            
            # Add thinking output for current tool
            new_thinking.thinking_content.append(
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
        new_thinking.thinking_content.append(
            f"Analysis complete. I've successfully executed {len(successful_tools)} tools and gathered comprehensive information."
        )
        
        logger.info(f"Tool execution complete: {len(successful_tools)}/{len(tool_results)} successful")
        
        return {
            "executed_tools": executed_tools,
            "tool_results": tool_results,
            "current_step": "synthesis",
            "thinking_state": new_thinking
        }
        
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            "executed_tools": executed_tools,
            "tool_results": tool_results,
            "current_step": "synthesis"
        }


async def synthesize_response_node(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: Synthesize final response using synthesis.md prompt.
    """
    logger.info(f"Synthesizing response from {len(state.tool_results)} tool results")
    
    try:
        # Load synthesis prompt
        synthesis_prompt_content = await prompt_manager.get_prompt("synthesis")
        
        # Prepare tool results for synthesis
        tool_results_text = _format_tool_results(state.tool_results)
        tools_used = [r.tool_name for r in state.tool_results if r.success]
        
        # Create synthesis prompt
        prompt = ChatPromptTemplate.from_template(synthesis_prompt_content)
        
        # Run synthesis
        chain = prompt | llm | StrOutputParser()
        final_response = await chain.ainvoke({
            "query": state.original_query,
            "intent": state.query_analysis.intent,
            "tools_used": ", ".join(tools_used),
            "tool_results": tool_results_text
        })
        
        # Update memory with this conversation
        memory.save_context(
            {"input": state.original_query},
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
        successful_results = [r for r in state.tool_results if r.success]
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
    
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            parsed[key.strip().lower().replace(' ', '_')] = value.strip()
    
    return QueryAnalysis(
        intent=parsed.get('intent', 'general_inquiry'),
        complexity=parsed.get('complexity', 'medium'),
        primary_entity=parsed.get('primary_entity'),
        secondary_entities=parsed.get('secondary_entities', '').split(', ') if parsed.get('secondary_entities') else [],
        key_relationships=parsed.get('key_relationships', '').split(', ') if parsed.get('key_relationships') else [],
        temporal_scope=parsed.get('temporal_scope', 'current'),
        analysis_strategy=parsed.get('analysis_strategy', 'comprehensive exploration')
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
        return {}
    
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


def _prepare_tool_input(tool_name: str, state: AgentState) -> str:
    """Prepare appropriate input for each tool."""
    query = state.processed_query
    
    # Use primary entity if available for entity-specific tools
    if state.query_analysis and state.query_analysis.primary_entity:
        entity_tools = [
            "get_entity_details", "get_entity_relationships", "get_entity_timeline",
            "find_similar_entities", "traverse_from_entity", "get_entity_neighbors",
            "analyze_entity_impact", "get_entity_history"
        ]
        if tool_name in entity_tools:
            return state.query_analysis.primary_entity
    
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


def _format_tool_results(tool_results: List[ToolResult]) -> str:
    """Format tool results for synthesis prompt."""
    formatted = []
    
    for result in tool_results:
        if result.success and result.output:
            formatted.append(f"**{result.tool_name}**: {result.output[:500]}...")
        elif not result.success:
            formatted.append(f"**{result.tool_name}**: Failed - {result.error}")
    
    return "\n\n".join(formatted)