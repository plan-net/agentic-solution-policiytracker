"""Main LangGraph agent implementation."""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from graphiti_core import Graphiti

from .state import AgentState
from .nodes import understand_query, plan_exploration, search_knowledge, evaluate_results

logger = logging.getLogger(__name__)


class PoliticalMonitoringAgent:
    """LangGraph agent for exploring political knowledge graph."""
    
    def __init__(self, graphiti_client: Graphiti):
        self.graphiti_client = graphiti_client
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("understand", understand_query)
        workflow.add_node("plan", plan_exploration)
        workflow.add_node("search", self._search_with_client)
        workflow.add_node("evaluate", evaluate_results)
        
        # Define the flow
        workflow.add_edge(START, "understand")
        workflow.add_edge("understand", "plan")
        workflow.add_edge("plan", "search")
        workflow.add_edge("search", "evaluate")
        
        # Conditional edges from evaluate
        workflow.add_conditional_edges(
            "evaluate",
            self._should_continue,
            {
                "continue": "plan",  # Loop back for more searching
                "finish": END
            }
        )
        
        return workflow.compile()
    
    async def _search_with_client(self, state: AgentState) -> Dict[str, Any]:
        """Wrapper to inject Graphiti client into search node."""
        return await search_knowledge(state, self.graphiti_client)
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if the agent should continue searching or finish."""
        
        # Stop if satisfied
        if state.is_satisfied:
            return "finish"
        
        # Stop if max iterations reached
        if state.iterations >= state.max_iterations:
            logger.warning(f"Max iterations ({state.max_iterations}) reached")
            return "finish"
        
        # Continue if we need more information
        return "continue"
    
    async def process_query(self, query: str, session_context: Dict[str, Any] = None) -> str:
        """
        Process a user query through the agent workflow.
        
        Args:
            query: User's question or request
            session_context: Optional session context for memory
            
        Returns:
            Final response string
        """
        logger.info(f"Processing query: {query}")
        
        # Initialize state
        initial_state = AgentState(
            messages=[{"role": "user", "content": query}],
            original_query=query,
            session_context=session_context or {},
            iterations=0
        )
        
        try:
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info(f"Agent completed in {final_state.iterations} iterations")
            logger.info(f"Final confidence: {final_state.confidence_score}")
            
            return final_state.final_response
            
        except Exception as e:
            logger.error(f"Agent workflow error: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def stream_query(self, query: str, session_context: Dict[str, Any] = None):
        """
        Stream the agent's thought process (for debugging/transparency).
        
        Args:
            query: User's question or request
            session_context: Optional session context for memory
            
        Yields:
            State updates as the agent processes
        """
        logger.info(f"Streaming query: {query}")
        
        # Initialize state
        initial_state = AgentState(
            messages=[{"role": "user", "content": query}],
            original_query=query,
            session_context=session_context or {},
            iterations=0
        )
        
        try:
            # Stream the workflow
            async for state in self.graph.astream(initial_state):
                yield state
                
        except Exception as e:
            logger.error(f"Agent streaming error: {e}")
            yield {"error": str(e)}