"""Individual agent implementations for multi-agent political monitoring system."""

import logging
from datetime import datetime
from typing import Any, Optional

from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .base import AgentResult, AgentRole, BaseAgent, MemoryMixin, MultiAgentState, StreamingMixin
from .prompt_loader import build_agent_context, multi_agent_prompt_loader

logger = logging.getLogger(__name__)


class QueryAnalysis(BaseModel):
    """Structured output for query analysis."""

    intent: str = Field(description="Primary intent of the query")
    confidence: float = Field(description="Confidence in analysis (0.0-1.0)")
    complexity: str = Field(description="Query complexity: simple, medium, complex")
    primary_entity: Optional[str] = Field(
        description="Main entity focus of the query, or null if query is too general",
        default="general_inquiry",
    )
    secondary_entities: list[str] = Field(description="Additional entities mentioned", default=[])
    key_relationships: list[str] = Field(
        description="Important relationship types to explore", default=[]
    )
    temporal_scope: str = Field(
        description="Time scope: current, historical, future, range", default="current"
    )
    analysis_strategy: str = Field(
        description="Recommended strategy: focused, comprehensive, temporal, network, comparative",
        default="exploratory",
    )
    search_priorities: list[dict[str, str]] = Field(
        description="Prioritized entities with reasoning", default=[]
    )
    expected_information_types: list[str] = Field(
        description="Types of information needed", default=[]
    )
    memory_insights: dict[str, str] = Field(
        description="Insights from user memory and patterns", default={}
    )


class ToolPlan(BaseModel):
    """Structured output for tool execution planning."""

    strategy_type: str = Field(description="Overall strategy type")
    estimated_execution_time: float = Field(description="Estimated time in seconds")
    tool_sequence: list[dict[str, Any]] = Field(description="Ordered sequence of tool executions")
    success_criteria: dict[str, str] = Field(
        description="Primary, secondary, and minimum success criteria"
    )
    backup_strategies: list[dict[str, Any]] = Field(
        description="Fallback strategies if primary fails"
    )
    optimization_notes: dict[str, str] = Field(
        description="Performance and optimization considerations"
    )


class ToolResult(BaseModel):
    """Structured output for individual tool execution."""

    tool_name: str = Field(description="Name of the executed tool")
    success: bool = Field(description="Whether execution was successful")
    execution_time: float = Field(description="Actual execution time in seconds")
    parameters_used: dict[str, Any] = Field(description="Parameters passed to the tool")
    output: str = Field(description="Raw output or summary from tool")
    insights: list[str] = Field(description="Key insights extracted from results")
    entities_found: list[dict[str, str]] = Field(description="Entities discovered")
    relationships_discovered: list[dict[str, str]] = Field(description="Relationships found")
    source_citations: list[str] = Field(description="Source references for information")
    temporal_aspects: list[str] = Field(description="Time-related information found")
    quality_score: float = Field(description="Quality assessment of results (0.0-1.0)")
    error: Optional[str] = Field(description="Error message if execution failed")


class ResponseSynthesis(BaseModel):
    """Structured output for response synthesis."""

    response_text: str = Field(description="Final formatted response")
    confidence_level: float = Field(description="Overall confidence in response")
    information_completeness: str = Field(description="Assessment of information completeness")
    source_count: int = Field(description="Number of sources referenced")
    key_insights_count: int = Field(description="Number of key insights provided")
    response_metadata: dict[str, Any] = Field(description="Metadata about response composition")
    follow_up_suggestions: list[dict[str, str]] = Field(description="Suggested follow-up questions")
    synthesis_notes: dict[str, str] = Field(description="Notes about synthesis process")


class QueryUnderstandingAgent(BaseAgent, StreamingMixin, MemoryMixin):
    """Agent responsible for analyzing and understanding user queries."""

    def __init__(self, llm: BaseLLM, name: str = "QueryUnderstanding"):
        super().__init__(AgentRole.QUERY_UNDERSTANDING, name)
        self.llm = llm
        self.output_parser = PydanticOutputParser(pydantic_object=QueryAnalysis)

    def get_prompt_template(self) -> str:
        """Get the prompt template for query understanding."""
        return "query_understanding"

    async def process(self, state: MultiAgentState) -> AgentResult:
        """Process user query to extract intent, entities, and strategy."""

        await self.stream_thinking("Analyzing query structure and extracting key information...")

        # Build context with memory and state
        context = build_agent_context(
            user_query=state.get("original_query", ""),
            session_state=state,
            memory_data=await self._get_memory_context(state.get("session_id")),
        )

        # Load and populate prompt template
        populated_prompt = await multi_agent_prompt_loader.get_agent_prompt(
            "query_understanding", context
        )

        await self.stream_thinking("Applying learned patterns and user preferences...")

        try:
            # Get LLM response
            messages = [
                SystemMessage(content=populated_prompt),
                HumanMessage(content=f"Query to analyze: {state.get('original_query', '')}"),
            ]

            logger.info(
                f"QueryUnderstandingAgent: Processing query '{state.get('original_query', '')}'"
            )
            response = await self.llm.ainvoke(messages)
            logger.info(f"QueryUnderstandingAgent: LLM response length: {len(response.content)}")

            # Parse structured output
            analysis = self.output_parser.parse(response.content)
            logger.info(
                f"QueryUnderstandingAgent: Parsed analysis - intent: {analysis.intent}, confidence: {analysis.confidence}"
            )

            await self.stream_thinking("Query analysis complete. Identified intent and strategy.")

            # Update state with analysis
            updated_state = dict(state)
            updated_state["query_analysis"] = analysis.dict()
            updated_state["processed_query"] = state.get(
                "original_query", ""
            )  # May be refined later
            updated_state["current_agent"] = "tool_planning"
            agent_sequence = updated_state.get("agent_sequence", [])
            agent_sequence.append(self.agent_role.value)
            updated_state["agent_sequence"] = agent_sequence

            logger.info(
                f"QueryUnderstandingAgent: Success - query_analysis added to state: {bool(updated_state.get('query_analysis'))}"
            )

            return AgentResult(
                success=True,
                updated_state=updated_state,
                data=analysis.dict(),
                message=f"Query analyzed with {analysis.confidence:.0%} confidence. Strategy: {analysis.analysis_strategy}",
                next_agent="tool_planning",
            )

        except Exception as e:
            logger.error(f"QueryUnderstandingAgent: Failed to process query: {str(e)}")
            await self.stream_custom(
                {"error": f"Query analysis failed: {str(e)}", "agent": self.name}
            )

            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message=f"Query analysis failed: {str(e)}",
                next_agent=None,
            )

    async def _get_memory_context(self, session_id: str) -> dict[str, Any]:
        """Get relevant memory context for query analysis."""
        # This would integrate with the actual memory system
        # For now, return mock data structure
        return {
            "user_preferences": {"detail_level": "high", "citation_style": "academic"},
            "learned_patterns": {"common_intent": "information_seeking"},
            "recent_queries": [],
            "tool_performance": {"search": {"success_rate": 0.94}},
        }


class ToolPlanningAgent(BaseAgent, StreamingMixin, MemoryMixin):
    """Agent responsible for planning optimal tool execution strategy."""

    def __init__(self, llm: BaseLLM, name: str = "ToolPlanning"):
        super().__init__(AgentRole.TOOL_PLANNING, name)
        self.llm = llm
        self.output_parser = PydanticOutputParser(pydantic_object=ToolPlan)
        self.tool_integration_manager = None

    def set_tool_integration_manager(self, manager):
        """Set the tool integration manager for intelligent tool planning."""
        self.tool_integration_manager = manager

    def get_prompt_template(self) -> str:
        """Get the prompt template for tool planning."""
        return "tool_planning"

    async def process(self, state: MultiAgentState) -> AgentResult:
        """Plan optimal tool execution strategy based on query analysis."""

        await self.stream_thinking("Designing optimal tool execution sequence...")

        if not state.get("query_analysis"):
            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message="No query analysis available for planning",
                next_agent=None,
            )

        query_analysis = state.get("query_analysis", {})

        # Get intelligent tool recommendations if available
        if self.tool_integration_manager:
            await self.stream_thinking(
                "Using intelligent tool selection based on query analysis..."
            )

            # Combine primary and secondary entities
            primary_entity = query_analysis.get("primary_entity")
            secondary_entities = query_analysis.get("secondary_entities", [])
            all_entities = [primary_entity] if primary_entity else []
            all_entities.extend(secondary_entities)

            recommendations = self.tool_integration_manager.get_tool_recommendations(
                intent=query_analysis.get("intent", "information_seeking"),
                entities=all_entities,
                complexity=query_analysis.get("complexity", "medium"),
                strategy_type=query_analysis.get("analysis_strategy", "focused"),
            )

            if recommendations:
                # Use AI-generated recommendations as the tool sequence
                plan = ToolPlan(
                    strategy_type=query_analysis.get("analysis_strategy", "focused"),
                    estimated_execution_time=sum(r["estimated_time"] for r in recommendations),
                    tool_sequence=recommendations,
                    success_criteria={
                        "primary": f"Complete {query_analysis.get('intent', 'analysis')} for {query_analysis.get('primary_entity', 'entities')}",
                        "secondary": "Gather comprehensive context and relationships",
                        "minimum": "At least one successful tool execution",
                    },
                    backup_strategies=[
                        {
                            "name": "fallback_search",
                            "description": "Use basic search if specific tools fail",
                            "tools": ["search"],
                        }
                    ],
                    optimization_notes={
                        "strategy": "AI-optimized based on query analysis",
                        "confidence": str(query_analysis.get("confidence", 0.8)),
                    },
                )

                await self.stream_thinking(
                    f"Generated {len(recommendations)} tool recommendations using AI analysis"
                )

                # Update state with plan
                updated_state = dict(state)
                updated_state["tool_plan"] = plan.dict()
                updated_state["current_agent"] = "tool_execution"
                agent_sequence = updated_state.get("agent_sequence", [])
                agent_sequence.append(self.agent_role.value)
                updated_state["agent_sequence"] = agent_sequence

                return AgentResult(
                    success=True,
                    updated_state=updated_state,
                    data=plan.dict(),
                    message=f"AI-optimized execution plan ready: {plan.strategy_type} strategy with {len(plan.tool_sequence)} tools",
                    next_agent="tool_execution",
                )

        # Fallback to LLM-based planning
        await self.stream_thinking("Using LLM-based tool planning...")

        # Build context with query analysis and memory
        context = build_agent_context(
            user_query=state.get("original_query", ""),
            session_state=state,
            memory_data=await self._get_memory_context(state.get("session_id")),
        )

        # Load and populate prompt template
        populated_prompt = await multi_agent_prompt_loader.get_agent_prompt(
            "tool_planning", context
        )

        await self.stream_thinking("Evaluating tool options and optimizing sequence...")

        try:
            # Get LLM response
            messages = [
                SystemMessage(content=populated_prompt),
                HumanMessage(
                    content=f"Create execution plan for: {state.get('original_query', '')}"
                ),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse structured output
            plan = self.output_parser.parse(response.content)

            await self.stream_thinking(
                f"Execution plan ready. Strategy: {plan.strategy_type}, estimated time: {plan.estimated_execution_time}s"
            )

            # Update state with plan
            updated_state = dict(state)
            updated_state["tool_plan"] = plan.dict()
            updated_state["current_agent"] = "tool_execution"
            agent_sequence = updated_state.get("agent_sequence", [])
            agent_sequence.append(self.agent_role.value)
            updated_state["agent_sequence"] = agent_sequence

            return AgentResult(
                success=True,
                updated_state=updated_state,
                data=plan.dict(),
                message=f"Execution plan ready: {plan.strategy_type} strategy with {len(plan.tool_sequence)} tools",
                next_agent="tool_execution",
            )

        except Exception as e:
            await self.stream_custom(
                {"error": f"Tool planning failed: {str(e)}", "agent": self.name}
            )

            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message=f"Tool planning failed: {str(e)}",
                next_agent=None,
            )

    async def _get_memory_context(self, session_id: str) -> dict[str, Any]:
        """Get relevant memory context for tool planning."""
        return {
            "tool_performance_history": {
                "search": {"success_rate": 0.94, "avg_time": 0.12},
                "entity_lookup": {"success_rate": 0.98, "avg_time": 0.05},
            },
            "successful_strategies": {"information_seeking": "focused"},
            "user_preferences": {"speed_vs_accuracy": "accuracy"},
        }


class ToolExecutionAgent(BaseAgent, StreamingMixin, MemoryMixin):
    """Agent responsible for executing tools and collecting results."""

    def __init__(self, tools: dict[str, Any], name: str = "ToolExecution"):
        super().__init__(AgentRole.TOOL_EXECUTION, name)
        self.tools = tools
        self.tool_integration_manager = None

    def set_tool_integration_manager(self, manager):
        """Set the tool integration manager for enhanced tool execution."""
        self.tool_integration_manager = manager

    def get_prompt_template(self) -> str:
        """Get the prompt template for tool execution."""
        return "tool_execution"

    async def process(self, state: MultiAgentState) -> AgentResult:
        """Execute planned tools and collect structured results."""

        await self.stream_thinking("Beginning tool execution sequence...")

        if not state.get("tool_plan"):
            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message="No tool plan available for execution",
                next_agent=None,
            )

        tool_plan = state.get("tool_plan", {})
        tool_results = []
        executed_tools = []
        total_execution_time = 0.0

        try:
            # Use enhanced tool integration if available
            if self.tool_integration_manager:
                await self.stream_thinking(
                    "Using enhanced tool integration for intelligent execution..."
                )

                async def tool_progress_callback(data):
                    await self.stream_custom(data)

                enhanced_results = await self.tool_integration_manager.execute_tool_sequence(
                    tool_plan["tool_sequence"], progress_callback=tool_progress_callback
                )

                tool_results = enhanced_results
                executed_tools = [result["tool_name"] for result in enhanced_results]
                total_execution_time = sum(result["execution_time"] for result in enhanced_results)

            else:
                # Fallback to basic tool execution
                await self.stream_thinking(
                    "Using basic tool execution (enhanced integration not available)..."
                )

                for step in tool_plan["tool_sequence"]:
                    tool_name = step["tool_name"]
                    parameters = step["parameters"]

                    await self.stream_custom(
                        {
                            "tool_execution": f"Executing {tool_name}...",
                            "agent": self.name,
                            "tool_name": tool_name,
                        }
                    )

                    start_time = datetime.now()

                    # Execute tool
                    if tool_name in self.tools:
                        tool_func = self.tools[tool_name]
                        raw_result = await tool_func(**parameters)
                        success = True
                        error = None
                    else:
                        raw_result = {}
                        success = False
                        error = f"Tool {tool_name} not available"

                    execution_time = (datetime.now() - start_time).total_seconds()
                    total_execution_time += execution_time

                    # Structure the result
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=success,
                        execution_time=execution_time,
                        parameters_used=parameters,
                        output=str(raw_result),
                        insights=self._extract_insights(raw_result, tool_name),
                        entities_found=self._extract_entities(raw_result),
                        relationships_discovered=self._extract_relationships(raw_result),
                        source_citations=self._extract_citations(raw_result),
                        temporal_aspects=self._extract_temporal_info(raw_result),
                        quality_score=self._assess_quality(raw_result, success),
                        error=error,
                    )

                    tool_results.append(tool_result.dict())
                    executed_tools.append(tool_name)

                    await self.stream_custom(
                        {
                            "tool_execution": f"Completed {tool_name}: {'✓' if success else '✗'}",
                            "agent": self.name,
                            "tool_name": tool_name,
                            "success": success,
                        }
                    )

                    # Break if critical tool fails and no backup strategy
                    if not success and step.get("critical", False):
                        await self.stream_custom(
                            {
                                "error": f"Critical tool {tool_name} failed, stopping execution",
                                "agent": self.name,
                            }
                        )
                        break

            await self.stream_thinking("Tool execution complete. Processing results...")

            # Update state with execution results
            updated_state = dict(state)
            updated_state["tool_results"] = tool_results
            updated_state["executed_tools"] = executed_tools
            updated_state["current_agent"] = "response_synthesis"
            agent_sequence = updated_state.get("agent_sequence", [])
            agent_sequence.append(self.agent_role.value)
            updated_state["agent_sequence"] = agent_sequence
            updated_state["execution_metadata"] = {
                "total_execution_time": total_execution_time,
                "tools_successful": sum(1 for r in tool_results if r["success"]),
                "tools_failed": sum(1 for r in tool_results if not r["success"]),
                "information_quality": self._assess_overall_quality(tool_results),
            }

            successful_tools = len([r for r in tool_results if r["success"]])

            return AgentResult(
                success=successful_tools > 0,
                updated_state=updated_state,
                data={"tool_results": tool_results, "execution_time": total_execution_time},
                message=f"Executed {len(tool_results)} tools ({successful_tools} successful)",
                next_agent="response_synthesis",
            )

        except Exception as e:
            await self.stream_custom(
                {"error": f"Tool execution failed: {str(e)}", "agent": self.name}
            )

            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message=f"Tool execution failed: {str(e)}",
                next_agent=None,
            )

    def _extract_insights(self, result: Any, tool_name: str) -> list[str]:
        """Extract key insights from tool result."""
        # Mock implementation - would parse actual tool results
        return [f"Insight from {tool_name}: {str(result)[:100]}..."]

    def _extract_entities(self, result: Any) -> list[dict[str, str]]:
        """Extract entities from tool result."""
        return [{"name": "Sample Entity", "type": "Policy", "relevance": "high"}]

    def _extract_relationships(self, result: Any) -> list[dict[str, str]]:
        """Extract relationships from tool result."""
        return [{"source": "Entity A", "target": "Entity B", "relationship": "REGULATES"}]

    def _extract_citations(self, result: Any) -> list[str]:
        """Extract source citations from tool result."""
        return ["Sample citation"]

    def _extract_temporal_info(self, result: Any) -> list[str]:
        """Extract temporal information from tool result."""
        return ["Current regulation status"]

    def _assess_quality(self, result: Any, success: bool) -> float:
        """Assess quality of tool result."""
        return 0.9 if success else 0.0

    def _assess_overall_quality(self, tool_results: list[dict]) -> str:
        """Assess overall information quality."""
        avg_quality = sum(r["quality_score"] for r in tool_results) / len(tool_results)
        if avg_quality > 0.8:
            return "high"
        elif avg_quality > 0.6:
            return "medium"
        else:
            return "low"


class ResponseSynthesisAgent(BaseAgent, StreamingMixin, MemoryMixin):
    """Agent responsible for synthesizing final response from tool results."""

    def __init__(self, llm: BaseLLM, name: str = "ResponseSynthesis"):
        super().__init__(AgentRole.RESPONSE_SYNTHESIS, name)
        self.llm = llm
        self.output_parser = PydanticOutputParser(pydantic_object=ResponseSynthesis)

    def get_prompt_template(self) -> str:
        """Get the prompt template for response synthesis."""
        return "response_synthesis"

    async def process(self, state: MultiAgentState) -> AgentResult:
        """Synthesize comprehensive response from all collected information."""

        await self.stream_thinking("Synthesizing findings into comprehensive response...")

        if not state.get("tool_results"):
            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message="No tool results available for synthesis",
                next_agent=None,
            )

        # Build context with all collected information
        context = build_agent_context(
            user_query=state.get("original_query", ""),
            session_state=state,
            memory_data=await self._get_memory_context(state.get("session_id")),
        )

        # Load and populate prompt template
        populated_prompt = await multi_agent_prompt_loader.get_agent_prompt(
            "response_synthesis", context
        )

        await self.stream_thinking("Formatting response with proper citations and structure...")

        try:
            # Prepare comprehensive context for synthesis
            synthesis_context = self._prepare_synthesis_context(state)

            # Get LLM response
            messages = [
                SystemMessage(content=populated_prompt),
                HumanMessage(
                    content=f"Synthesize response for: {state.get('original_query', '')}\n\nContext: {synthesis_context}"
                ),
            ]

            response = await self.llm.ainvoke(messages)

            # Parse structured output
            synthesis = self.output_parser.parse(response.content)

            await self.stream_thinking("Response synthesis complete. Final answer ready.")

            # Update state with final response
            updated_state = dict(state)
            updated_state["synthesis_complete"] = True
            updated_state["final_response"] = synthesis.response_text
            updated_state["response_metadata"] = synthesis.response_metadata
            updated_state["current_agent"] = "response_synthesis"  # Mark as complete
            agent_sequence = updated_state.get("agent_sequence", [])
            agent_sequence.append(self.agent_role.value)
            updated_state["agent_sequence"] = agent_sequence

            return AgentResult(
                success=True,
                updated_state=updated_state,
                data=synthesis.dict(),
                message=f"Response synthesized with {synthesis.confidence_level:.0%} confidence",
                next_agent=None,  # End of workflow
            )

        except Exception as e:
            await self.stream_custom(
                {"error": f"Response synthesis failed: {str(e)}", "agent": self.name}
            )

            return AgentResult(
                success=False,
                updated_state=state,
                data={},
                message=f"Response synthesis failed: {str(e)}",
                next_agent=None,
            )

    def _prepare_synthesis_context(self, state: MultiAgentState) -> str:
        """Prepare comprehensive context for synthesis."""
        context_parts = []

        # Add query analysis
        query_analysis = state.get("query_analysis")
        if query_analysis:
            context_parts.append(f"Query Analysis: {query_analysis}")

        # Add tool results summary
        tool_results = state.get("tool_results", [])
        if tool_results:
            context_parts.append(f"Tool Results: {len(tool_results)} tools executed")
            for result in tool_results:
                if result["success"]:
                    context_parts.append(f"- {result['tool_name']}: {result['raw_output'][:200]}")

        # Add execution metadata
        execution_metadata = state.get("execution_metadata")
        if execution_metadata:
            context_parts.append(f"Execution Metadata: {execution_metadata}")

        return "\n".join(context_parts)

    async def _get_memory_context(self, session_id: str) -> dict[str, Any]:
        """Get relevant memory context for response synthesis."""
        return {
            "user_preferences": {"citation_style": "academic", "response_format": "structured"},
            "response_patterns": {"preferred_length": "comprehensive"},
            "follow_up_patterns": {"information_seeking": ["implementation", "enforcement"]},
        }
