"""Multi-agent orchestration using LangGraph for political monitoring system."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime

logger = logging.getLogger(__name__)

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, AIMessage

from .agents import (
    QueryUnderstandingAgent, ToolPlanningAgent, ToolExecutionAgent, ResponseSynthesisAgent
)
from .base import MultiAgentState, AgentRole, AgentResult
from .memory import MemoryManager
from .streaming import StreamingManager
from .quality_assessment import ResponseQualityAssessment, QualityOptimizer


class MultiAgentOrchestrator:
    """Orchestrates multi-agent workflow using LangGraph."""
    
    def __init__(
        self,
        llm: BaseLLM,
        tools: Dict[str, Callable],
        memory_store: Optional[InMemoryStore] = None,
        checkpointer: Optional[MemorySaver] = None
    ):
        self.llm = llm
        self.tools = tools
        
        # Initialize memory components
        self.memory_store = memory_store or InMemoryStore()
        self.checkpointer = checkpointer or MemorySaver()
        self.memory_manager = MemoryManager()
        self.memory_manager.store = self.memory_store
        self.memory_manager.checkpointer = self.checkpointer
        
        # Initialize streaming with enhanced capabilities
        self.streaming_manager = StreamingManager()
        
        # Import here to avoid circular imports
        from .streaming import StreamingThinkingGenerator
        self.thinking_generator = StreamingThinkingGenerator(self.streaming_manager)
        
        # Initialize quality assessment system
        self.quality_assessor = ResponseQualityAssessment()
        self.quality_optimizer = QualityOptimizer(self.quality_assessor)
        
        # Initialize tool integration manager if Graphiti client available
        self.tool_integration_manager = None
        try:
            from .tool_integration import ToolIntegrationManager
            from graphiti_core import Graphiti
            
            # Try to initialize Graphiti client for tool integration
            # In production, this would come from configuration
            # For now, we'll set it up when tools are available
            self.tool_integration_manager = None  # Will be set up later if needed
        except ImportError:
            logger.warning("Tool integration not available - some tools may not work optimally")
        
        # Initialize agents
        self.query_agent = QueryUnderstandingAgent(llm=llm)
        self.planning_agent = ToolPlanningAgent(llm=llm)
        self.execution_agent = ToolExecutionAgent(tools=tools)
        self.synthesis_agent = ResponseSynthesisAgent(llm=llm)
        
        # Set up agent memory and streaming
        self._setup_agent_capabilities()
        
        # Set up tool integration for planning and execution agents
        if self.tool_integration_manager:
            self.planning_agent.set_tool_integration_manager(self.tool_integration_manager)
            self.execution_agent.set_tool_integration_manager(self.tool_integration_manager)
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _setup_agent_capabilities(self):
        """Set up memory and streaming capabilities for all agents."""
        agents = [self.query_agent, self.planning_agent, self.execution_agent, self.synthesis_agent]
        
        for agent in agents:
            # Set memory components
            if hasattr(agent, 'set_memory_components'):
                agent.set_memory_components(self.memory_store, self.checkpointer)
            
            # Set streaming
            if hasattr(agent, 'set_stream_writer'):
                agent.set_stream_writer(self.streaming_manager.get_stream_writer())
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph."""
        
        # Create the state graph
        graph = StateGraph(MultiAgentState)
        
        # Add nodes for each agent
        graph.add_node("query_understanding", self._query_understanding_node)
        graph.add_node("tool_planning", self._tool_planning_node)
        graph.add_node("tool_execution", self._tool_execution_node)
        graph.add_node("response_synthesis", self._response_synthesis_node)
        
        # Add conditional routing node
        graph.add_node("route_next", self._route_next_agent)
        
        # Define the workflow edges
        graph.add_edge(START, "query_understanding")
        graph.add_edge("query_understanding", "route_next")
        graph.add_edge("tool_planning", "route_next")
        graph.add_edge("tool_execution", "route_next")
        graph.add_edge("response_synthesis", END)
        
        # Add conditional edges from router
        graph.add_conditional_edges(
            "route_next",
            self._determine_next_agent,
            {
                "tool_planning": "tool_planning",
                "tool_execution": "tool_execution", 
                "response_synthesis": "response_synthesis",
                "end": END
            }
        )
        
        # Compile the graph
        return graph.compile(checkpointer=self.checkpointer)
    
    async def _query_understanding_node(self, state: MultiAgentState) -> MultiAgentState:
        """Process query understanding."""
        await self.streaming_manager.emit_agent_transition("", "query_understanding", "Starting query analysis")
        
        result = await self.query_agent.process(state)
        
        if result.success:
            query_analysis = result.updated_state.get("query_analysis", {})
            confidence = query_analysis.get("confidence", 0)
            await self.streaming_manager.emit_progress(
                "query_understanding", 
                f"Query analyzed with {confidence:.0%} confidence"
            )
            return result.updated_state
        else:
            # Handle error - add to state errors
            error_state = dict(state)
            errors = error_state.get("errors", [])
            errors.append(f"Query understanding failed: {result.message}")
            error_state["errors"] = errors
            return error_state
    
    async def _tool_planning_node(self, state: MultiAgentState) -> MultiAgentState:
        """Process tool planning."""
        await self.streaming_manager.emit_agent_transition("query_understanding", "tool_planning", "Creating execution plan")
        
        result = await self.planning_agent.process(state)
        
        if result.success:
            plan = result.updated_state.get("tool_plan", {})
            await self.streaming_manager.emit_progress(
                "tool_planning",
                f"Plan ready: {plan.get('strategy_type', 'unknown')} strategy with {len(plan.get('tool_sequence', []))} tools"
            )
            return result.updated_state
        else:
            error_state = dict(state)
            errors = error_state.get("errors", [])
            errors.append(f"Tool planning failed: {result.message}")
            error_state["errors"] = errors
            return error_state
    
    async def _tool_execution_node(self, state: MultiAgentState) -> MultiAgentState:
        """Process tool execution."""
        await self.streaming_manager.emit_agent_transition("tool_planning", "tool_execution", "Executing knowledge graph queries")
        
        result = await self.execution_agent.process(state)
        
        if result.success:
            metadata = result.updated_state.get("execution_metadata", {})
            await self.streaming_manager.emit_progress(
                "tool_execution",
                f"Execution complete: {metadata.get('tools_successful', 0)} tools succeeded"
            )
            return result.updated_state
        else:
            error_state = dict(state)
            errors = error_state.get("errors", [])
            errors.append(f"Tool execution failed: {result.message}")
            error_state["errors"] = errors
            return error_state
    
    async def _response_synthesis_node(self, state: MultiAgentState) -> MultiAgentState:
        """Process response synthesis."""
        await self.streaming_manager.emit_agent_transition("tool_execution", "response_synthesis", "Synthesizing comprehensive response")
        
        result = await self.synthesis_agent.process(state)
        
        if result.success:
            response_metadata = result.updated_state.get("response_metadata", {})
            confidence = response_metadata.get("confidence_level", 0)
            await self.streaming_manager.emit_progress(
                "response_synthesis",
                f"Response complete with {confidence:.0%} confidence"
            )
            return result.updated_state
        else:
            error_state = dict(state)
            errors = error_state.get("errors", [])
            errors.append(f"Response synthesis failed: {result.message}")
            error_state["errors"] = errors
            return error_state
    
    async def _route_next_agent(self, state: MultiAgentState) -> MultiAgentState:
        """Route to next agent based on current state."""
        # This is just a pass-through node for routing logic
        return state
    
    def _determine_next_agent(self, state: MultiAgentState) -> str:
        """Determine the next agent to execute based on current state."""
        
        # Check for errors - if too many errors, end
        if len(state.get("errors", [])) >= 3:
            logger.debug(f"Too many errors ({len(state.get('errors', []))}), ending workflow")
            return "end"
        
        # Determine next based on current agent and state
        current = state.get("current_agent", "")
        logger.debug(f"Current agent: {current}, query_analysis exists: {state.get('query_analysis') is not None}")
        
        if current == "query_understanding":
            if state.get("query_analysis"):
                logger.debug("Routing from query_understanding to tool_planning")
                return "tool_planning"
            else:
                logger.debug("Query analysis failed, ending workflow")
                return "end"  # Query analysis failed
        
        elif current == "tool_planning":
            if state.get("tool_plan"):
                return "tool_execution"
            else:
                return "end"  # Planning failed
        
        elif current == "tool_execution":
            if state.get("tool_results"):
                return "response_synthesis"
            else:
                return "end"  # Execution failed
        
        elif current == "response_synthesis":
            return "end"  # Workflow complete
        
        else:
            # Default to starting the workflow
            return "tool_planning" if state.get("query_analysis") else "end"
    
    async def process_query(
        self,
        query: str,
        session_id: str = None,
        user_id: str = None,
        stream_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Process a user query through the multi-agent workflow."""
        
        # Set up streaming callback
        if stream_callback:
            self.streaming_manager.set_stream_callback(stream_callback)
        
        # Set up personalization if user_id provided
        if user_id:
            try:
                personalization = await self.memory_manager.get_personalization_recommendations(user_id)
                self.thinking_generator.set_user_preferences(personalization)
            except Exception as e:
                # Personalization failure shouldn't break the workflow
                await self.streaming_manager.emit_thinking("orchestrator", f"Personalization setup failed: {str(e)}")
        
        # Create initial state with all required defaults
        initial_state = MultiAgentState(
            original_query=query,
            processed_query="",
            query_analysis=None,
            tool_plan=None,
            tool_results=[],
            final_response="",
            current_agent="query_understanding",
            agent_sequence=[],
            execution_metadata={},
            session_id=session_id or f"session_{datetime.now().timestamp()}",
            conversation_history=[],
            user_preferences={},
            learned_patterns={},
            is_streaming=stream_callback is not None,
            thinking_updates=[],
            progress_indicators=[],
            errors=[],
            warnings=[],
            messages=[HumanMessage(content=query)]
        )
        
        # Create thread configuration
        thread_config = {
            "configurable": {
                "thread_id": session_id or f"thread_{datetime.now().timestamp()}"
            }
        }
        
        try:
            # Execute the workflow
            await self.streaming_manager.emit_thinking("orchestrator", "Starting multi-agent political analysis...")
            
            # Stream the workflow execution
            final_state = None
            async for chunk in self.graph.astream(initial_state, config=thread_config):
                if stream_callback:
                    await stream_callback({
                        "type": "workflow_update",
                        "data": chunk,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Update final state
                for node_name, node_state in chunk.items():
                    if isinstance(node_state, dict) and "original_query" in node_state:
                        final_state = node_state
            
            # If we don't have a final state, get it from the graph
            if final_state is None:
                final_state = await self.graph.aget_state(thread_config)
                final_state = final_state.values
            
            await self.streaming_manager.emit_thinking("orchestrator", "Multi-agent analysis complete!")
            
            # Assess response quality
            quality_metrics = None
            if final_state.get("final_response"):
                try:
                    await self.streaming_manager.emit_thinking("orchestrator", "Assessing response quality...")
                    quality_metrics = await self.quality_assessor.assess_response_quality(
                        response=final_state.get("final_response", ""),
                        query=query,
                        query_analysis=final_state.get("query_analysis", {}),
                        tool_results=final_state.get("tool_results", []),
                        execution_metadata=final_state.get("execution_metadata", {}),
                        response_metadata=final_state.get("response_metadata", {})
                    )
                    
                    if quality_metrics.overall_score < 0.7:
                        await self.streaming_manager.emit_thinking(
                            "orchestrator", 
                            f"Quality score {quality_metrics.overall_score:.2f} - considering improvements..."
                        )
                        
                        # Generate optimization suggestions
                        optimizations = await self.quality_optimizer.suggest_optimizations(
                            quality_metrics,
                            final_state.get("query_analysis", {}),
                            final_state.get("tool_results", [])
                        )
                        
                        # Log optimization suggestions for future improvement
                        logger.info(f"Quality optimizations suggested: {optimizations}")
                    
                except Exception as e:
                    logger.warning(f"Quality assessment failed: {e}")
            
            # Learn from this interaction
            if user_id and final_state.get("query_analysis"):
                await self._learn_from_interaction(user_id, query, final_state)
            
            # Return structured result
            return {
                "success": len(final_state.get("errors", [])) == 0,
                "response": final_state.get("final_response", ""),
                "confidence": self._calculate_overall_confidence(final_state),
                "agent_sequence": final_state.get("agent_sequence", []),
                "execution_time": self._calculate_execution_time(final_state),
                "sources": self._extract_sources(final_state),
                "errors": final_state.get("errors", []),
                "metadata": {
                    "query_analysis": final_state.get("query_analysis"),
                    "tool_plan": final_state.get("tool_plan"),
                    "execution_metadata": final_state.get("execution_metadata"),
                    "response_metadata": final_state.get("response_metadata"),
                    "quality_metrics": quality_metrics.__dict__ if quality_metrics else None
                }
            }
            
        except Exception as e:
            await self.streaming_manager.emit_error("orchestrator", f"Workflow execution failed: {str(e)}")
            
            return {
                "success": False,
                "response": f"I encountered an error while processing your query: {str(e)}",
                "confidence": 0.0,
                "agent_sequence": [],
                "execution_time": 0.0,
                "sources": [],
                "errors": [str(e)],
                "metadata": {}
            }
    
    async def _learn_from_interaction(self, user_id: str, query: str, final_state: MultiAgentState):
        """Enhanced learning from interaction with advanced pattern recognition."""
        try:
            # Extract learning data
            analysis = final_state.get("query_analysis", {})
            intent = analysis.get("intent", "unknown")
            complexity = analysis.get("complexity", "medium")
            entities = analysis.get("secondary_entities", [])
            
            # Calculate satisfaction and response time
            confidence = self._calculate_overall_confidence(final_state)
            satisfaction = min(4.5, confidence * 4.5)  # Scale to 4.5 max
            response_time = self._calculate_execution_time(final_state)
            
            # Enhanced learning with conversation patterns
            await self.memory_manager.update_user_conversation_patterns(
                user_id=user_id,
                query=query,
                intent=intent,
                complexity=complexity,
                satisfaction_rating=satisfaction,
                response_time=response_time
            )
            
            # Traditional query learning
            await self.memory_manager.learn_from_query(
                user_id=user_id,
                query=query,
                intent=intent,
                entities=entities,
                satisfaction_rating=satisfaction
            )
            
            # Learn tool and agent performance
            execution_meta = final_state.get("execution_metadata", {})
            if "agent_execution_times" in execution_meta:
                for agent, time in execution_meta["agent_execution_times"].items():
                    await self.memory_manager.update_tool_performance(
                        tool_name=agent,
                        success=True,
                        execution_time=time,
                        error=None
                    )
            
            # Update thinking generator preferences
            personalization = await self.memory_manager.get_personalization_recommendations(user_id)
            self.thinking_generator.set_user_preferences(personalization)
            
        except Exception as e:
            # Learning failure shouldn't break the workflow
            await self.streaming_manager.emit_thinking("orchestrator", f"Learning failed: {str(e)}")
    
    def _calculate_overall_confidence(self, state: MultiAgentState) -> float:
        """Calculate overall confidence from all agent results."""
        confidences = []
        
        # Query analysis confidence
        query_analysis = state.get("query_analysis", {})
        if query_analysis and "confidence" in query_analysis:
            confidences.append(query_analysis["confidence"])
        
        # Execution quality
        execution_metadata = state.get("execution_metadata", {})
        if execution_metadata and "confidence_level" in execution_metadata:
            confidences.append(execution_metadata["confidence_level"])
        
        # Response confidence
        response_metadata = state.get("response_metadata", {})
        if response_metadata and "confidence_level" in response_metadata:
            confidences.append(response_metadata["confidence_level"])
        
        # Average with penalty for errors
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            error_penalty = len(state.get("errors", [])) * 0.1
            return max(0.0, avg_confidence - error_penalty)
        
        return 0.5  # Default neutral confidence
    
    def _calculate_execution_time(self, state: MultiAgentState) -> float:
        """Calculate total execution time."""
        execution_metadata = state.get("execution_metadata", {})
        
        if execution_metadata and "total_execution_time" in execution_metadata:
            return execution_metadata["total_execution_time"]
        
        # Estimate from agent times
        if execution_metadata and "agent_execution_times" in execution_metadata:
            return sum(execution_metadata["agent_execution_times"].values())
        
        return 0.0
    
    def _extract_sources(self, state: MultiAgentState) -> List[str]:
        """Extract all sources from tool results."""
        sources = []
        
        tool_results = state.get("tool_results", [])
        if tool_results:
            for result in tool_results:
                if "source_citations" in result:
                    sources.extend(result["source_citations"])
        
        return list(set(sources))  # Remove duplicates
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        try:
            thread_config = {"configurable": {"thread_id": session_id}}
            state = await self.graph.aget_state(thread_config)
            
            if state and state.values and "messages" in state.values:
                return [
                    {
                        "role": "human" if isinstance(msg, HumanMessage) else "assistant",
                        "content": msg.content,
                        "timestamp": getattr(msg, 'timestamp', datetime.now().isoformat())
                    }
                    for msg in state.values["messages"]
                ]
            
            return []
        except Exception:
            return []
    
    async def clear_conversation(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        try:
            # This would clear the conversation in the checkpointer
            # Implementation depends on specific checkpointer capabilities
            return True
        except Exception:
            return False
    
    def get_workflow_schema(self) -> Dict[str, Any]:
        """Get the workflow schema for debugging and documentation."""
        return {
            "nodes": [
                {"name": "query_understanding", "agent": "QueryUnderstandingAgent", "role": "Analyze user query"},
                {"name": "tool_planning", "agent": "ToolPlanningAgent", "role": "Plan tool execution"}, 
                {"name": "tool_execution", "agent": "ToolExecutionAgent", "role": "Execute knowledge graph tools"},
                {"name": "response_synthesis", "agent": "ResponseSynthesisAgent", "role": "Synthesize final response"}
            ],
            "edges": [
                {"from": "START", "to": "query_understanding"},
                {"from": "query_understanding", "to": "tool_planning"},
                {"from": "tool_planning", "to": "tool_execution"},
                {"from": "tool_execution", "to": "response_synthesis"},
                {"from": "response_synthesis", "to": "END"}
            ],
            "conditional_routing": {
                "node": "route_next",
                "conditions": ["has_query_analysis", "has_tool_plan", "has_tool_results", "is_complete"]
            }
        }


class MultiAgentStreamingOrchestrator(MultiAgentOrchestrator):
    """Enhanced orchestrator with advanced streaming capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_streams = {}
    
    async def process_query_with_streaming(
        self,
        query: str,
        session_id: str = None,
        user_id: str = None
    ):
        """Process query with real-time streaming using async generator."""
        
        # Set up streaming
        stream_queue = asyncio.Queue()
        
        async def stream_callback(data):
            await stream_queue.put(data)
        
        # Start processing in background
        process_task = asyncio.create_task(
            self.process_query(query, session_id, user_id, stream_callback)
        )
        
        # Yield streaming updates
        try:
            while not process_task.done():
                try:
                    # Wait for stream data with timeout
                    data = await asyncio.wait_for(stream_queue.get(), timeout=0.1)
                    yield data
                except asyncio.TimeoutError:
                    # No data available, continue
                    continue
            
            # Get final result
            final_result = await process_task
            yield {
                "type": "final_result",
                "data": final_result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def register_stream(self, stream_id: str, callback: Callable):
        """Register a streaming callback."""
        self.active_streams[stream_id] = callback
    
    def unregister_stream(self, stream_id: str):
        """Unregister a streaming callback."""
        self.active_streams.pop(stream_id, None)