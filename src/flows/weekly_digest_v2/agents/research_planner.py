"""
Research Planner Agent for Weekly Digest v2.

Agent 1 in the three-agent architecture. Plans research based on YAML configurations
and creates a comprehensive research plan for the ToolExecutorAgent.

This agent is purely for planning - it does NOT execute any tools.
"""

import logging
from typing import Any, Optional

import langwatch
from langchain_core.language_models import BaseLLM

from src.chat.observability.langwatch_config import langwatch_config
from src.core.config.category_config import CategoryConfig
from src.core.config.tool_plan_config import ToolPlanConfig
from src.core.observability.tracer import AgentTracer

from .base import ResearchPlanEntry, WeeklyDigestState

logger = logging.getLogger(__name__)


class ResearchPlannerAgent:
    """
    Agent 1: Plans research based on YAML configurations.

    Reads category configs and creates a comprehensive research plan
    that the ToolExecutorAgent will execute. Does NOT execute tools.

    Example:
        planner = ResearchPlannerAgent(
            category_configs={"legislative": leg_config, ...},
            tool_plan=ToolPlanConfig.from_yaml(...),
            llm=llm,
            tracer=tracer,
        )
        state_update = await planner.process(state)

    Attributes:
        category_configs: Category configurations loaded from YAML
        tool_plan: Tool plan configuration loaded from YAML
        llm: LLM (reserved for future intelligent planning)
        tracer: AgentTracer for observability
    """

    def __init__(
        self,
        category_configs: dict[str, CategoryConfig],
        tool_plan: ToolPlanConfig,
        llm: Optional[BaseLLM] = None,
        tracer: Optional[AgentTracer] = None,
    ):
        """
        Initialize the research planner agent.

        Args:
            category_configs: Category configurations from YAML files
            tool_plan: Tool plan configuration from YAML
            llm: Optional LLM for intelligent planning (future enhancement)
            tracer: Optional tracer for observability
        """
        self.category_configs = category_configs
        self.tool_plan = tool_plan
        self.llm = llm
        self.tracer = tracer

    async def process(self, state: WeeklyDigestState) -> dict[str, Any]:
        """
        Create research plan for all enabled categories.

        Reads YAML category configs and tool plan, then creates a structured
        research plan that the ToolExecutorAgent will execute.

        Args:
            state: Current workflow state with date information

        Returns:
            State update dict with research_plan:
            {
                "research_plan": {
                    "legislative": {
                        "display_name": "Legislative Updates",
                        "queries": ["DSA DMA...", "new regulation..."],
                        "search_type": "comprehensive",
                        "entity_types": ["REGULATION", "LAW"],
                        "system_prompt": "...",
                        "max_findings": 10,
                        "tool_sequence": [...]
                    },
                    ...
                },
                "current_stage": "planning_complete",
                "current_agent": "tool_executor"
            }
        """
        logger.info(
            f"=== RESEARCH PLANNER START === "
            f"Categories: {len(self.category_configs)}, "
            f"Tool Plan: {self.tool_plan.name}"
        )

        if self.tracer:
            await self.tracer.markdown("### Planning Research Strategy\n")
            await self.tracer.markdown(
                f"**Categories:** {len(self.category_configs)} enabled\n"
                f"**Tool Plan:** {self.tool_plan.name}\n"
            )

        # Get week context for temporal queries
        week_start = state.get("week_start")
        year = state.get("year", 2025)

        # Build research plan from YAML configs
        research_plan: dict[str, ResearchPlanEntry] = {}
        include_events = state.get("include_events", True)

        # Sort categories by priority
        sorted_categories = sorted(
            self.category_configs.values(),
            key=lambda c: c.priority,
        )

        for config in sorted_categories:
            # Skip disabled categories
            if not config.enabled:
                logger.debug(f"Skipping disabled category: {config.name}")
                continue

            # Skip events if not requested
            if config.name == "events" and not include_events:
                logger.debug("Skipping events category (not requested)")
                continue

            # Build temporal-aware queries
            temporal_queries = []
            for query in config.search_queries:
                temporal_query = config.get_temporal_query(query, year)
                temporal_queries.append(temporal_query)

            # Create plan entry for this category
            plan_entry: ResearchPlanEntry = {
                "display_name": config.display_name,
                "queries": temporal_queries,
                "search_type": config.search_type.value,
                "entity_types": config.entity_types,
                "system_prompt": config.system_prompt,
                "max_findings": config.max_findings,
                "temporal_filter_strategy": config.temporal_filter_strategy,
                "skip_llm_extraction": config.skip_llm_extraction,
                "tool_sequence": [
                    {
                        "tool_name": spec.tool_name,
                        "description": spec.description,
                        "limit": spec.limit,
                        "search_type": (
                            config.search_type.value
                            if spec.search_type == "from_category"
                            else spec.search_type
                        ),
                        "timeout_seconds": spec.timeout_seconds,
                        "required": spec.required,
                        "conditional": spec.conditional,
                    }
                    for spec in self.tool_plan.tool_sequence
                ],
            }

            research_plan[config.name] = plan_entry

            logger.info(
                f"Planned category: {config.name} "
                f"({len(temporal_queries)} queries, "
                f"search_type: {config.search_type.value})"
            )

        if self.tracer:
            await self.tracer.markdown(
                f"**Research Plan Created:**\n"
                f"- Categories: {', '.join(research_plan.keys())}\n"
                f"- Total queries: {sum(len(p['queries']) for p in research_plan.values())}\n"
            )

        logger.info(
            f"=== RESEARCH PLANNER COMPLETE === "
            f"Planned {len(research_plan)} categories"
        )

        # Capture planning completion in LangWatch
        langwatch_config.capture_tool_execution(
            tool_name="research_planning",
            tool_input={
                "categories_count": len(self.category_configs),
                "tool_plan": self.tool_plan.name,
            },
            tool_output={
                "planned_categories": len(research_plan),
                "total_queries": sum(len(p["queries"]) for p in research_plan.values()),
            },
            execution_time=0.0,  # Planning is fast
            success=True,
        )

        return {
            "research_plan": research_plan,
            "current_stage": "planning_complete",
            "current_agent": "tool_executor",
        }
