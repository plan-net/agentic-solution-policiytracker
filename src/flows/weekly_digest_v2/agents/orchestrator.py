"""
Report Orchestrator for Weekly Digest v2.

LangGraph-based workflow orchestrator implementing a 3-agent architecture:
1. ResearchPlannerAgent - Plans research based on YAML configs
2. ToolExecutorAgent - Executes all tool calls and extracts findings
3. ReportSynthesizerAgent - Generates executive summary and renders report

This architecture ensures each agent appears as a distinct span in LangWatch,
matching the chat implementation's observability pattern.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import langwatch
from graphiti_core import Graphiti
from kodosumi.core import Tracer
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from src.chat.observability.langwatch_config import langwatch_config
from src.core.config.category_config import CategoryConfig
from src.core.config.report_config import ReportConfig
from src.core.config.tool_plan_config import ToolPlanConfig
from src.core.observability.tracer import AgentTracer
from src.core.renderers.markdown_renderer import MarkdownRenderer
from src.core.visualization.graph_link_builder import GraphLinkBuilder
from src.flows.weekly_digest_v2.date_resolver import resolve_week_input

from .research_planner import ResearchPlannerAgent
from .report_synthesizer import ReportSynthesizer
from .tool_executor import ToolExecutorAgent

logger = logging.getLogger(__name__)


class ReportOrchestrator:
    """
    LangGraph-based workflow orchestrator for Weekly Digest v2.

    Implements a 3-agent architecture with clear separation of concerns:
    - ResearchPlannerAgent: Plans research based on YAML configurations
    - ToolExecutorAgent: Executes all tool calls and extracts findings
    - ReportSynthesizerAgent: Generates executive summary and renders report

    Each agent appears as a distinct span in LangWatch for observability.

    Example:
        orchestrator = ReportOrchestrator(
            report_config=ReportConfig.load(Path("config/weekly_digest.yaml")),
            tracer=kodosumi_tracer,
        )
        final_report = await orchestrator.run(week_input="KW48")

    Attributes:
        report_config: Master report configuration
        tracer: Kodosumi tracer for UI updates
        agent_tracer: Unified tracer for observability
    """

    def __init__(
        self,
        report_config: ReportConfig,
        tracer: Tracer,
        config_dir: Optional[Path] = None,
    ):
        """
        Initialize the report orchestrator.

        Args:
            report_config: Master report configuration
            tracer: Kodosumi tracer for UI updates
            config_dir: Directory containing config files
        """
        self.report_config = report_config
        self.tracer = tracer

        # Initialize LangWatch observability FIRST (before any instrumented code)
        langwatch_config.initialize()
        logger.info("LangWatch initialized in ReportOrchestrator")

        # Determine config directory
        if config_dir is None:
            # Default: src/flows/weekly_digest_v2/config
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = config_dir

        # Create unified agent tracer
        self.agent_tracer = AgentTracer(kodosumi_tracer=tracer)

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Will be initialized during run
        self.graphiti_client: Optional[Graphiti] = None
        self.category_configs: dict[str, CategoryConfig] = {}
        self.tool_plans: dict[str, ToolPlanConfig] = {}

        # Graph will be built during run
        self.graph = None

    async def _init_graphiti(self) -> Graphiti:
        """Initialize Graphiti client with proper embedder configuration."""
        try:
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

            # Configure embedder with 1536 dimensions to match existing entity embeddings
            embedder_config = OpenAIEmbedderConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                embedding_dim=int(os.getenv("EMBEDDING_DIM", "1536")),
            )
            embedder = OpenAIEmbedder(config=embedder_config)

            client = Graphiti(
                neo4j_uri,
                neo4j_user,
                neo4j_password,
                embedder=embedder,
            )
            await client.build_indices_and_constraints()
            return client

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise

    def _load_configs(self) -> None:
        """Load category and tool plan configurations from YAML files."""
        # Load category configs
        categories_dir = self.config_dir / "categories"
        for category_file in self.report_config.categories:
            category_path = categories_dir / category_file
            if category_path.exists():
                config = CategoryConfig.from_yaml(category_path)
                self.category_configs[config.name] = config
                logger.info(f"Loaded category config: {config.name}")
            else:
                logger.warning(f"Category config not found: {category_path}")

        # Load tool plan configs
        tool_plans_dir = self.config_dir / "tool_plans"
        for plan_file in tool_plans_dir.glob("*.yaml"):
            plan = ToolPlanConfig.from_yaml(plan_file)
            self.tool_plans[plan.name] = plan
            logger.info(f"Loaded tool plan: {plan.name}")

    def _build_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow with 3-agent architecture.

        Architecture:
        START -> resolve_dates -> research_planner -> tool_executor -> report_synthesizer -> render_report -> END

        Each agent node is wrapped in a LangWatch trace for observability.
        """
        graph = StateGraph(dict)

        # Add nodes - 3 distinct agents + utility nodes
        graph.add_node("resolve_dates", self._resolve_dates_node)
        graph.add_node("research_planner", self._research_planner_node)
        graph.add_node("tool_executor", self._tool_executor_node)
        graph.add_node("report_synthesizer", self._report_synthesizer_node)
        graph.add_node("render_report", self._render_report_node)

        # Build edges - sequential flow
        graph.add_edge(START, "resolve_dates")
        graph.add_edge("resolve_dates", "research_planner")
        graph.add_edge("research_planner", "tool_executor")
        graph.add_edge("tool_executor", "report_synthesizer")
        graph.add_edge("report_synthesizer", "render_report")
        graph.add_edge("render_report", END)

        return graph.compile()

    async def _resolve_dates_node(self, state: dict) -> dict:
        """Resolve week input to date range."""
        with langwatch.trace(
            name="resolve_dates",
            metadata={"week_input": state.get("week_input", "")},
        ):
            await self.tracer.markdown("### Resolving Week Dates\n")

            week_input = state.get("week_input", "")

            try:
                # Check if dates were pre-resolved
                if state.get("resolved_week_start"):
                    week_start = datetime.fromisoformat(state["resolved_week_start"])
                    week_end = datetime.fromisoformat(state["resolved_week_end"])
                    week_label = state["resolved_week_label"]
                    week_number = state["resolved_week_number"]
                    year = state["resolved_year"]
                else:
                    resolved = resolve_week_input(week_input)
                    week_start = resolved["week_start"]
                    week_end = resolved["week_end"]
                    week_label = resolved["week_label"]
                    week_number = resolved["week_number"]
                    year = resolved["year"]

                await self.tracer.markdown(
                    f"**Report Period:** {week_label}\n"
                    f"- Start: {week_start.strftime('%A, %d %B %Y')}\n"
                    f"- End: {week_end.strftime('%A, %d %B %Y')}\n"
                )

                return {
                    **state,
                    "week_start": week_start,
                    "week_end": week_end,
                    "week_label": week_label,
                    "week_number": week_number,
                    "year": year,
                    "current_stage": "date_resolved",
                }

            except Exception as e:
                logger.error(f"Date resolution failed: {e}")
                await self.tracer.markdown(f"**Error:** Date resolution failed - {e}\n")
                return {
                    **state,
                    "errors": state.get("errors", []) + [str(e)],
                    "current_stage": "error",
                }

    async def _research_planner_node(self, state: dict) -> dict:
        """
        Agent 1: Plan research based on YAML configurations.

        Creates a comprehensive research plan for all enabled categories.
        """
        with langwatch.trace(
            name="research_planner_agent",
            metadata={
                "categories_count": len(self.category_configs),
                "tool_plan": self.report_config.default_tool_plan,
            },
        ):
            await self.tracer.markdown("### Research Planner Agent\n")

            try:
                # Get the default tool plan
                plan_name = self.report_config.default_tool_plan
                tool_plan = self.tool_plans.get(plan_name)

                if not tool_plan:
                    logger.warning(f"Tool plan {plan_name} not found, using first available")
                    tool_plan = next(iter(self.tool_plans.values()))

                # Create and run the research planner agent
                planner = ResearchPlannerAgent(
                    category_configs=self.category_configs,
                    tool_plan=tool_plan,
                    llm=self.llm,
                    tracer=self.agent_tracer,
                )

                result = await planner.process(state)
                return {**state, **result}

            except Exception as e:
                logger.error(f"Research planner failed: {e}")
                await self.tracer.markdown(f"**Error:** Research planning failed - {e}\n")
                return {
                    **state,
                    "errors": state.get("errors", []) + [str(e)],
                    "current_stage": "error",
                }

    async def _tool_executor_node(self, state: dict) -> dict:
        """
        Agent 2: Execute all tool calls based on research plan.

        Executes Graphiti searches for all categories and extracts findings.
        """
        with langwatch.trace(
            name="tool_executor_agent",
            metadata={
                "research_plan_categories": len(state.get("research_plan", {})),
            },
        ):
            await self.tracer.markdown("### Tool Executor Agent\n")

            try:
                # Create and run the tool executor agent
                executor = ToolExecutorAgent(
                    graphiti_client=self.graphiti_client,
                    llm=self.llm,
                    tracer=self.agent_tracer,
                )

                result = await executor.process(state)
                return {**state, **result}

            except Exception as e:
                logger.error(f"Tool executor failed: {e}")
                await self.tracer.markdown(f"**Error:** Tool execution failed - {e}\n")
                return {
                    **state,
                    "errors": state.get("errors", []) + [str(e)],
                    "current_stage": "error",
                }

    async def _report_synthesizer_node(self, state: dict) -> dict:
        """
        Agent 3: Synthesize findings into executive summary.

        Generates executive summary from all category findings.
        """
        with langwatch.trace(
            name="report_synthesizer_agent",
            metadata={
                "categories_with_findings": len(state.get("findings_by_category", {})),
                "total_findings": sum(
                    len(f) for f in state.get("findings_by_category", {}).values()
                ),
            },
        ):
            await self.tracer.markdown("### Report Synthesizer Agent\n")

            try:
                synthesizer = ReportSynthesizer(
                    llm=self.llm,
                    tracer=self.agent_tracer,
                )

                # Adapt state to synthesizer's expected format
                # The tool_executor already provides findings_by_category and summaries
                result = await synthesizer.synthesize_from_state(state)

                # Build graph visualization link if enabled
                graph_link = ""
                if self.report_config.include_graph_visualization:
                    link_builder = GraphLinkBuilder()
                    week_label = state.get("week_label", "unknown")
                    all_entities = state.get("all_entities", [])
                    graph_link = link_builder.build_report_link(
                        report_id=f"weekly-{week_label}",
                        entities=all_entities[:50],  # Limit for URL length
                    )

                return {
                    **state,
                    **result,
                    "graph_visualization_link": graph_link,
                    "current_stage": "synthesized",
                }

            except Exception as e:
                logger.error(f"Report synthesis failed: {e}")
                await self.tracer.markdown(f"**Error:** Synthesis failed - {e}\n")
                return {
                    **state,
                    "errors": state.get("errors", []) + [str(e)],
                    "current_stage": "error",
                }

    async def _render_report_node(self, state: dict) -> dict:
        """Render the final markdown report."""
        with langwatch.trace(name="render_report"):
            await self.tracer.markdown("### Rendering Report\n")

            try:
                # Get template directory
                template_dir = self.config_dir.parent / "templates"

                renderer = MarkdownRenderer(template_dir=template_dir)

                # Build template context
                context = {
                    "week_label": state.get("week_label", ""),
                    "week_start": state.get("week_start"),
                    "week_end": state.get("week_end"),
                    "executive_summary": state.get("executive_summary", ""),
                    "findings_by_category": state.get("findings_by_category", {}),
                    "summaries": state.get("summaries", {}),
                    "graph_visualization_link": state.get("graph_visualization_link", ""),
                    "entities_count": len(state.get("all_entities", [])),
                    "generated_at": datetime.now(),
                }

                # Render using template
                final_report = await renderer.render(
                    template_context=context,
                    template_name="weekly_digest.md.j2",
                )

                await self.tracer.markdown("**Report rendered successfully!**\n")

                return {
                    **state,
                    "final_report": final_report,
                    "current_stage": "complete",
                }

            except Exception as e:
                logger.error(f"Report rendering failed: {e}")
                await self.tracer.markdown(f"**Error:** Rendering failed - {e}\n")
                return {
                    **state,
                    "errors": state.get("errors", []) + [str(e)],
                    "current_stage": "error",
                }

    async def run(
        self,
        week_input: str = "",
        include_events: bool = True,
        resolved_dates: Optional[dict] = None,
    ) -> str:
        """
        Execute the weekly digest workflow.

        Args:
            week_input: User input (KW48 or 2025-11-25)
            include_events: Whether to include events category
            resolved_dates: Pre-resolved dates from app.py validation

        Returns:
            Final rendered markdown report
        """
        # Wrap entire workflow in LangWatch trace context for proper span nesting
        with langwatch.trace(
            name="weekly_digest_v2_execution",
            metadata={
                "week_input": week_input,
                "include_events": include_events,
            },
        ):
            await self.tracer.markdown("## Weekly Regulatory Intelligence Digest v2\n")
            await self.tracer.markdown(
                f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

            try:
                # Initialize Graphiti
                with langwatch.trace(name="init_graphiti"):
                    await self.tracer.markdown("### Initializing Knowledge Graph\n")
                    self.graphiti_client = await self._init_graphiti()
                    await self.tracer.markdown("**Connected to Graphiti**\n")

                # Load configurations
                with langwatch.trace(name="load_configs"):
                    await self.tracer.markdown("### Loading Configurations\n")
                    self._load_configs()
                    await self.tracer.markdown(
                        f"**Loaded {len(self.category_configs)} categories, "
                        f"{len(self.tool_plans)} tool plans**\n"
                    )

                # Build workflow
                self.graph = self._build_workflow()

                # Prepare initial state
                initial_state: dict[str, Any] = {
                    "week_input": week_input,
                    "include_events": include_events,
                    "current_stage": "init",
                    "errors": [],
                    "warnings": [],
                }

                # Add pre-resolved dates if provided
                if resolved_dates:
                    initial_state.update({
                        "resolved_week_start": resolved_dates.get("week_start"),
                        "resolved_week_end": resolved_dates.get("week_end"),
                        "resolved_week_label": resolved_dates.get("week_label"),
                        "resolved_week_number": resolved_dates.get("week_number"),
                        "resolved_year": resolved_dates.get("year"),
                    })

                # Execute workflow
                await self.tracer.markdown("### Executing Workflow\n")

                final_state = None
                async for chunk in self.graph.astream(initial_state):
                    for node_name, node_output in chunk.items():
                        logger.info(f"Completed node: {node_name}")
                        if isinstance(node_output, dict):
                            final_state = node_output

                if final_state and final_state.get("final_report"):
                    await self.tracer.markdown("---\n")
                    await self.tracer.markdown("### Report Complete\n")
                    return final_state["final_report"]
                else:
                    error_msg = "Report generation completed but no output produced."
                    if final_state and final_state.get("errors"):
                        error_msg += f" Errors: {', '.join(final_state['errors'])}"
                    await self.tracer.markdown(f"**Error:** {error_msg}\n")
                    return f"# Report Generation Failed\n\n{error_msg}"

            except Exception as e:
                logger.exception(f"Weekly digest workflow failed: {e}")
                await self.tracer.markdown(f"**Fatal Error:** {e}\n")
                return f"# Report Generation Failed\n\n**Error:** {e}"

            finally:
                # Cleanup
                if self.graphiti_client:
                    try:
                        await self.graphiti_client.close()
                    except Exception:
                        pass
