"""LLM-driven agent nodes for LangGraph workflow."""

import logging
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .state import AgentState, ExplorationPlan, SearchResult
from ..tools.search import GraphitiSearchTool

logger = logging.getLogger(__name__)

# Initialize LLM (will be injected from outside)
llm = None


async def understand_query(state: AgentState) -> Dict[str, Any]:
    """
    Node 1: LLM-driven query understanding and analysis.
    
    Uses LLM to extract intent, entities, and prepare search strategy.
    """
    logger.info(f"Understanding query with LLM: {state.original_query}")
    
    # Get the latest user message
    if state.messages:
        latest_message = state.messages[-1]
        if hasattr(latest_message, 'content'):
            query = latest_message.content
        else:
            query = str(latest_message)
    else:
        query = state.original_query
    
    # Load prompt template (simplified for now - will use prompt manager later)
    understand_prompt = ChatPromptTemplate.from_template("""
    Analyze this user query for political/regulatory knowledge exploration:
    
    Query: {user_query}
    
    Extract and provide:
    1. Primary Intent (information_seeking, relationship_exploration, temporal_analysis, compliance_research, impact_assessment)
    2. Key Entities (organizations, policies, people, jurisdictions, topics)
    3. Temporal Scope (time period if relevant)
    4. Search Strategy (recommended approach)
    
    Respond in structured format:
    Intent: [intent]
    Entities: [comma-separated list]
    Temporal: [time scope or 'none']
    Strategy: [brief strategy description]
    ProcessedQuery: [cleaned query for search]
    """)
    
    # Run LLM analysis
    chain = understand_prompt | llm | StrOutputParser()
    
    try:
        analysis = await chain.ainvoke({"user_query": query})
        
        # Parse LLM response (simple parsing for now)
        lines = analysis.strip().split('\n')
        parsed = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                parsed[key.strip().lower()] = value.strip()
        
        intent = parsed.get('intent', 'general_inquiry')
        processed_query = parsed.get('processedquery', query)
        
        logger.info(f"LLM analysis - Intent: {intent}, Processed: {processed_query}")
        
        return {
            "original_query": query,
            "processed_query": processed_query,
            "query_intent": intent,
            "iterations": state.iterations + 1
        }
        
    except Exception as e:
        logger.error(f"LLM understanding error: {e}")
        # Fallback to simple processing
        return {
            "original_query": query,
            "processed_query": query.replace("search", "").strip(),
            "query_intent": "general_inquiry",
            "iterations": state.iterations + 1
        }


async def plan_exploration(state: AgentState) -> Dict[str, Any]:
    """
    Node 2: Plan how to explore the knowledge graph.
    
    Creates a strategy for searching based on the understood query.
    """
    logger.info(f"Planning exploration for: {state.processed_query}")
    
    # Create exploration plan based on intent
    if state.query_intent == "search_knowledge":
        strategy = "direct_search"
        tools = ["basic_search"]
        depth = 1
    elif state.query_intent == "information_request":
        strategy = "entity_focused"
        tools = ["basic_search", "entity_lookup"]
        depth = 2
    else:
        strategy = "broad_search"
        tools = ["basic_search"]
        depth = 1
    
    # Extract potential entities from query (simple keyword extraction)
    entities = []
    for word in state.processed_query.split():
        if len(word) > 3 and word.upper() == word:  # Likely acronym
            entities.append(word)
        elif word.title() == word and len(word) > 3:  # Likely proper noun
            entities.append(word)
    
    plan = ExplorationPlan(
        query_intent=state.query_intent,
        search_strategy=strategy,
        tools_to_use=tools,
        search_depth=depth,
        expected_entities=entities
    )
    
    logger.info(f"Created plan: {plan.search_strategy} with tools: {plan.tools_to_use}")
    
    return {
        "exploration_plan": plan
    }


async def search_knowledge(state: AgentState, graphiti_client) -> Dict[str, Any]:
    """
    Node 3: Execute searches against the knowledge graph.
    
    Uses the exploration plan to search and collect results.
    """
    logger.info(f"Searching knowledge graph: {state.processed_query}")
    
    search_results = []
    total_found = 0
    
    try:
        # Execute basic search
        if "basic_search" in state.exploration_plan.tools_to_use:
            results = await graphiti_client.search(state.processed_query)
            
            if results:
                total_found = len(results)
                # Convert to our SearchResult format
                for result in results[:5]:  # Limit to top 5 for now
                    search_result = SearchResult(
                        fact=result.fact,
                        relationship=getattr(result, 'name', None),
                        confidence=0.8  # Default confidence
                    )
                    search_results.append(search_result)
                
                logger.info(f"Found {total_found} results, processed {len(search_results)}")
            else:
                logger.info("No results found")
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        # Add error information to state if needed
    
    # Update previous searches
    previous = state.previous_searches.copy()
    previous.append(state.processed_query)
    
    return {
        "search_results": search_results,
        "total_results_found": total_found,
        "previous_searches": previous
    }


async def evaluate_results(state: AgentState) -> Dict[str, Any]:
    """
    Node 4: Evaluate if we have sufficient information to respond.
    
    Determines if more searches are needed or if we can provide a final answer.
    """
    logger.info(f"Evaluating results: {len(state.search_results)} results found")
    
    # Simple evaluation logic
    has_results = len(state.search_results) > 0
    within_iterations = state.iterations < state.max_iterations
    
    # Determine if satisfied
    if has_results and state.total_results_found > 0:
        is_satisfied = True
        confidence = min(0.9, 0.5 + (len(state.search_results) * 0.1))
    else:
        is_satisfied = False
        confidence = 0.1
    
    # Generate final response
    if is_satisfied:
        response = f"Found {state.total_results_found} facts related to '{state.processed_query}'"
        if len(state.search_results) < state.total_results_found:
            response += f" (showing top {len(state.search_results)})"
        response += ":\n\n"
        
        for i, result in enumerate(state.search_results, 1):
            response += f"{i}. {result.fact}\n"
            if result.relationship:
                response += f"   Relationship: {result.relationship}\n"
            response += "\n"
            
        if state.total_results_found > len(state.search_results):
            remaining = state.total_results_found - len(state.search_results)
            response += f"... and {remaining} more facts available."
    else:
        response = f"I couldn't find specific information about '{state.processed_query}'. Try being more specific or search for related terms."
    
    logger.info(f"Evaluation complete. Satisfied: {is_satisfied}, Confidence: {confidence}")
    
    return {
        "is_satisfied": is_satisfied,
        "confidence_score": confidence,
        "final_response": response
    }