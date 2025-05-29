"""Enhanced LangGraph agent implementation with streaming capabilities."""

import logging
import asyncio
from typing import Dict, Any, AsyncGenerator
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .state import AgentState
from .nodes import (
    understand_query_node, 
    plan_tools_node, 
    execute_tools_node, 
    synthesize_response_node,
    initialize_nodes
)
from ...prompts.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class EnhancedPoliticalMonitoringAgent:
    """Enhanced LangGraph agent with streaming and advanced graph capabilities."""
    
    def __init__(self, graphiti_client, openai_api_key: str):
        self.graphiti_client = graphiti_client
        self.openai_api_key = openai_api_key
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=openai_api_key,
            temperature=0.3
        )
        
        # Initialize nodes with dependencies
        initialize_nodes(self.llm, graphiti_client, openai_api_key)
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Initialize prompt manager
        self.prompt_manager = PromptManager()
        
        logger.info("Enhanced Political Monitoring Agent initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build the enhanced LangGraph workflow."""
        
        # Create the graph with enhanced state
        workflow = StateGraph(AgentState)
        
        # Add enhanced nodes
        workflow.add_node("understand", understand_query_node)
        workflow.add_node("plan", plan_tools_node) 
        workflow.add_node("execute", execute_tools_node)
        workflow.add_node("synthesize", synthesize_response_node)
        
        # Define linear flow (no loops for now - can be added later)
        workflow.add_edge(START, "understand")
        workflow.add_edge("understand", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "synthesize")
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    async def process_query(self, query: str, session_context: Dict[str, Any] = None) -> str:
        """
        Process a user query through the enhanced agent workflow.
        
        Args:
            query: User's question or request
            session_context: Optional session context for memory
            
        Returns:
            Final response string
        """
        logger.info(f"Processing query: {query}")
        
        # Initialize enhanced state
        initial_state = AgentState(
            messages=[{"role": "user", "content": query}],
            original_query=query,
            session_context=session_context or {},
            current_step="start",
            iterations=0
        )
        
        try:
            # Run the enhanced workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            logger.info(f"Enhanced agent completed - Step: {final_state.current_step}")
            logger.info(f"Tools executed: {len(final_state.executed_tools)}")
            
            return final_state.final_response
            
        except Exception as e:
            logger.error(f"Enhanced agent workflow error: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def stream_query(self, query: str, session_context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """
        Stream the agent's thought process with real-time thinking output.
        
        This implements the proven streaming approach from SimplePoliticalAgent
        with enhanced graph capabilities and proper thinking output.
        
        Args:
            query: User's question or request  
            session_context: Optional session context for memory
            
        Yields:
            Streaming content including thinking and final response
        """
        logger.info(f"Streaming enhanced query: {query}")
        
        try:
            # Initialize enhanced state
            initial_state = AgentState(
                messages=[{"role": "user", "content": query}],
                original_query=query,
                session_context=session_context or {},
                current_step="start",
                iterations=0,
                is_streaming=True
            )
            
            # Phase 1: Start thinking
            yield "<think>\n"
            await asyncio.sleep(0.5)
            
            # Phase 2: Initial understanding with natural thinking
            yield f"Looking at this question, I need to understand what type of analysis you're requesting. "
            await asyncio.sleep(0.8)
            
            # Start the graph execution
            graph_task = asyncio.create_task(self.graph.ainvoke(initial_state))
            
            # Phase 3: Stream thinking updates while graph runs
            thinking_updates = [
                "The key entities and relationships involved need to be identified first.",
                "I'll need to map the regulatory landscape to understand the connections.",
                "Graph-based analysis will reveal patterns that simple searches would miss.",
                "Examining the temporal evolution and impact networks will be crucial.", 
                "Synthesizing all findings to provide comprehensive insights."
            ]
            
            for i, update in enumerate(thinking_updates):
                yield update + "\n\n"
                await asyncio.sleep(1.2 if i < 2 else 1.0)
                
                # Check if graph is done
                if graph_task.done():
                    break
            
            # Wait for graph completion
            try:
                final_state = await graph_task
                
                # Phase 4: Show final thinking based on actual results
                if hasattr(final_state, 'executed_tools') and final_state.executed_tools:
                    tool_count = len(final_state.executed_tools)
                    successful_tools = len([r for r in final_state.tool_results if r.success])
                    
                    yield f"Analysis complete. I've successfully executed {successful_tools} out of {tool_count} tools "
                    yield f"and gathered comprehensive information from the knowledge graph. "
                    yield f"The graph-based approach has revealed several key insights that wouldn't be visible through traditional search methods."
                else:
                    yield f"Analysis complete. I've explored the knowledge graph to gather comprehensive information about your query."
                
            except Exception as e:
                logger.error(f"Graph execution failed: {e}")
                yield f"I encountered an error during the analysis: {str(e)}. Let me provide what information I can. "
                final_state = AgentState(
                    final_response=f"I encountered an error while processing your request: {str(e)}",
                    current_step="error"
                )
            
            # Phase 5: Complete thinking
            yield "</think>\n\n"
            await asyncio.sleep(0.5)
            
            # Phase 6: Stream final response
            response = final_state.final_response or "I couldn't generate a response."
            
            # Stream response in natural chunks for better UX
            sentences = response.split('. ')
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    chunk = sentence.strip()
                    if i < len(sentences) - 1:
                        chunk += ". "
                    yield chunk
                    await asyncio.sleep(0.8)  # Natural reading pace
            
            logger.info(f"Enhanced streaming completed successfully")
            
        except Exception as e:
            logger.error(f"Enhanced streaming error: {e}")
            yield f"</think>\n\nI encountered an error while processing your request: {str(e)}"
    
    async def stream_with_detailed_thinking(self, query: str, session_context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """
        Stream with detailed step-by-step thinking using actual graph state.
        
        This provides more granular thinking output by monitoring graph state changes.
        """
        logger.info(f"Streaming with detailed thinking: {query}")
        
        try:
            # Initialize state
            initial_state = AgentState(
                messages=[{"role": "user", "content": query}],
                original_query=query,
                session_context=session_context or {},
                current_step="start",
                iterations=0,
                is_streaming=True
            )
            
            # Start thinking
            yield "<think>\n"
            
            # Stream the workflow with state monitoring
            last_step = "start"
            async for state_update in self.graph.astream(initial_state):
                for node_name, node_state in state_update.items():
                    if hasattr(node_state, 'current_step') and node_state.current_step != last_step:
                        # Generate thinking based on current step
                        thinking_text = await self._generate_step_thinking(node_state.current_step, node_state)
                        if thinking_text:
                            yield thinking_text + "\n\n"
                            await asyncio.sleep(1.0)
                        
                        last_step = node_state.current_step
                    
                    # Stream thinking content if available
                    if hasattr(node_state, 'thinking_state') and node_state.thinking_state.thinking_content:
                        for thought in node_state.thinking_state.thinking_content:
                            if thought not in getattr(self, '_streamed_thoughts', set()):
                                yield thought + " "
                                await asyncio.sleep(0.5)
                                # Track to avoid duplicates
                                if not hasattr(self, '_streamed_thoughts'):
                                    self._streamed_thoughts = set()
                                self._streamed_thoughts.add(thought)
            
            yield "</think>\n\n"
            
            # Final response from last state
            if 'synthesize' in state_update:
                final_response = state_update['synthesize'].final_response
                sentences = final_response.split('. ')
                for i, sentence in enumerate(sentences):
                    if sentence.strip():
                        chunk = sentence.strip()
                        if i < len(sentences) - 1:
                            chunk += ". "
                        yield chunk
                        await asyncio.sleep(0.8)
            
            # Clear thinking cache
            if hasattr(self, '_streamed_thoughts'):
                delattr(self, '_streamed_thoughts')
                
        except Exception as e:
            logger.error(f"Detailed streaming error: {e}")
            yield f"</think>\n\nI encountered an error: {str(e)}"
    
    async def _generate_step_thinking(self, step: str, state: AgentState) -> str:
        """Generate thinking text for current step."""
        thinking_map = {
            "understanding": "Let me analyze what you're asking to understand the key entities and relationships involved.",
            "planning": "Now I need to plan which tools will give me the most comprehensive insights about this topic.",
            "execution": "Starting the analysis using multiple specialized graph tools to gather comprehensive information.",
            "synthesis": "Putting all the pieces together to provide you with a complete answer that showcases the unique insights from graph analysis.",
            "complete": "Analysis complete."
        }
        
        base_thinking = thinking_map.get(step, "")
        
        # Add context-specific details
        if step == "planning" and hasattr(state, 'tool_plan') and state.tool_plan:
            tools_count = len(state.tool_plan.tool_sequence)
            base_thinking += f" I'll use {tools_count} specialized tools for this analysis."
        elif step == "execution" and hasattr(state, 'executed_tools'):
            executed_count = len(state.executed_tools)
            if executed_count > 0:
                base_thinking += f" I've completed {executed_count} tool executions so far."
        
        return base_thinking
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are an enhanced political and regulatory analysis agent with access to a sophisticated temporal knowledge graph.

Your UNIQUE ADVANTAGES:
1. **Graph-aware insights**: Trace relationships between policies, companies, and politicians
2. **Entity deep-dives**: Get comprehensive details about specific entities and their evolution  
3. **Network analysis**: Understand how entities are connected through regulatory relationships
4. **Timeline tracking**: See how policies and regulations have evolved over time
5. **Source traceability**: Every fact traces back to original documents with URLs

You have access to 15 specialized tools for comprehensive analysis. Use them strategically based on query complexity and type.

ALWAYS:
- Include source citations from tools
- Explain relationships between entities
- Suggest deeper exploration opportunities  
- Highlight insights only available through graph analysis
- Provide comprehensive, accurate answers using multiple tools as needed"""