"""
Weekly Report Processor with LangGraph Workflow.

Orchestrates the multi-agent workflow for generating the Weekly Regulatory
Intelligence Digest using LangGraph for state management and parallel execution.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Optional

import structlog
from graphiti_core import Graphiti
from kodosumi import core
from kodosumi.core import Tracer
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .agents.category_researchers import (
    ComplianceResearchAgent,
    EventsResearchAgent,
    LegislativeResearchAgent,
    PersonnelResearchAgent,
    PolicyResearchAgent,
)
from .agents.report_synthesizer import ReportSynthesizerAgent
from .date_resolver import DateResolver, resolve_week_input
from .models import Finding, ReportMetadata, WeeklyReportState

# Configure logging
logger = structlog.get_logger()


class WeeklyReportProcessor:
    """
    Orchestrates the weekly report generation workflow.

    Uses LangGraph to coordinate:
    1. Date Resolution
    2. Parallel Category Research (5 agents)
    3. Report Synthesis
    """

    def __init__(
        self,
        tracer_instance: Tracer,
        inputs: dict[str, Any],
    ):
        self.tracer = tracer_instance
        self.inputs = inputs

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Initialize Graphiti client
        self.graphiti_client = None  # Will be initialized in run()

        # Build the workflow graph
        self.graph = None  # Built after Graphiti client is ready

    async def _init_graphiti(self) -> Graphiti:
        """Initialize Graphiti client."""
        try:
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

            client = Graphiti(
                neo4j_uri,
                neo4j_user,
                neo4j_password,
            )
            await client.build_indices_and_constraints()
            return client

        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for weekly report generation."""
        # Create graph with dict state (LangGraph requirement)
        graph = StateGraph(dict)

        # Add nodes
        graph.add_node("resolve_dates", self._resolve_dates_node)
        graph.add_node("research_legislative", self._research_legislative_node)
        graph.add_node("research_personnel", self._research_personnel_node)
        graph.add_node("research_compliance", self._research_compliance_node)
        graph.add_node("research_policy", self._research_policy_node)
        graph.add_node("research_events", self._research_events_node)
        graph.add_node("synthesize_report", self._synthesize_report_node)

        # Define edges - Sequential execution to avoid LangGraph fan-in issues
        # Start -> Date Resolution
        graph.add_edge(START, "resolve_dates")

        # Sequential research pipeline
        graph.add_edge("resolve_dates", "research_legislative")
        graph.add_edge("research_legislative", "research_personnel")
        graph.add_edge("research_personnel", "research_compliance")
        graph.add_edge("research_compliance", "research_policy")
        graph.add_edge("research_policy", "research_events")

        # Final synthesis
        graph.add_edge("research_events", "synthesize_report")

        # Synthesis -> End
        graph.add_edge("synthesize_report", END)

        return graph.compile()

    async def _resolve_dates_node(self, state: dict) -> dict:
        """Resolve the week input to date range."""
        await self.tracer.markdown("### Resolving Week Dates\n")

        week_input = state.get("week_input", "")

        try:
            # Check if dates were pre-resolved in app.py
            if state.get("resolved_week_start"):
                week_start = datetime.fromisoformat(state["resolved_week_start"])
                week_end = datetime.fromisoformat(state["resolved_week_end"])
                week_label = state["resolved_week_label"]
                week_number = state["resolved_week_number"]
                year = state["resolved_year"]
            else:
                # Resolve dates
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

    async def _research_category(
        self, state: dict, agent_class: type, category_name: str
    ) -> dict:
        """Generic category research handler."""
        await self.tracer.markdown(f"### Researching {category_name}\n")

        week_start = state.get("week_start")
        week_end = state.get("week_end")

        if not week_start or not week_end:
            await self.tracer.markdown(f"**Skipped:** No valid date range\n")
            return state

        try:
            agent = agent_class(
                graphiti_client=self.graphiti_client,
                llm=self.llm,
            )

            result = await agent.research(week_start, week_end)

            findings_key = f"{category_name.lower()}_findings"
            summary_key = f"{category_name.lower()}_summary"

            # Convert Finding objects to dicts for state serialization
            findings_dicts = [f.model_dump() for f in result.findings]

            await self.tracer.markdown(
                f"**Found {len(result.findings)} {category_name} findings**\n"
            )

            if result.findings:
                for i, finding in enumerate(result.findings[:3], 1):
                    await self.tracer.markdown(f"{i}. {finding.title}\n")
                if len(result.findings) > 3:
                    await self.tracer.markdown(f"   ... and {len(result.findings) - 3} more\n")

            return {
                **state,
                findings_key: findings_dicts,
                summary_key: result.summary,
                "completed_categories": state.get("completed_categories", [])
                + [category_name],
            }

        except Exception as e:
            logger.error(f"{category_name} research failed: {e}")
            await self.tracer.markdown(f"**Error:** {category_name} research failed - {e}\n")
            return {
                **state,
                "warnings": state.get("warnings", [])
                + [f"{category_name} research failed: {e}"],
            }

    async def _research_legislative_node(self, state: dict) -> dict:
        """Research legislative developments."""
        return await self._research_category(
            state, LegislativeResearchAgent, "Legislative"
        )

    async def _research_personnel_node(self, state: dict) -> dict:
        """Research personnel changes."""
        return await self._research_category(
            state, PersonnelResearchAgent, "Personnel"
        )

    async def _research_compliance_node(self, state: dict) -> dict:
        """Research compliance issues."""
        return await self._research_category(
            state, ComplianceResearchAgent, "Compliance"
        )

    async def _research_policy_node(self, state: dict) -> dict:
        """Research policy developments."""
        return await self._research_category(state, PolicyResearchAgent, "Policy")

    async def _research_events_node(self, state: dict) -> dict:
        """Research upcoming events."""
        return await self._research_category(state, EventsResearchAgent, "Events")

    async def _synthesize_report_node(self, state: dict) -> dict:
        """Synthesize findings into final report."""
        await self.tracer.markdown("### Synthesizing Report\n")

        try:
            synthesizer = ReportSynthesizerAgent(llm=self.llm)

            # Convert finding dicts back to Finding objects
            def to_findings(findings_dicts: list[dict]) -> list[Finding]:
                return [Finding(**f) for f in findings_dicts] if findings_dicts else []

            result = await synthesizer.synthesize(
                week_start=state.get("week_start"),
                week_end=state.get("week_end"),
                week_label=state.get("week_label", ""),
                legislative_findings=to_findings(state.get("legislative_findings", [])),
                personnel_findings=to_findings(state.get("personnel_findings", [])),
                compliance_findings=to_findings(state.get("compliance_findings", [])),
                policy_findings=to_findings(state.get("policy_findings", [])),
                events_findings=to_findings(state.get("events_findings", [])),
                legislative_summary=state.get("legislative_summary", ""),
                personnel_summary=state.get("personnel_summary", ""),
                compliance_summary=state.get("compliance_summary", ""),
                policy_summary=state.get("policy_summary", ""),
                events_summary=state.get("events_summary", ""),
            )

            await self.tracer.markdown("**Report synthesis complete!**\n")
            await self.tracer.markdown(
                f"- Total findings: {result['metadata'].total_findings}\n"
                f"- Categories completed: {result['metadata'].categories_completed}\n"
                f"- Processing time: {result['metadata'].processing_time_seconds:.1f}s\n"
            )

            return {
                **state,
                "executive_summary": result["executive_summary"],
                "report_sections": result["report_sections"],
                "final_report": result["final_report"],
                "metadata": result["metadata"].model_dump(),
                "current_stage": "complete",
            }

        except Exception as e:
            logger.error(f"Report synthesis failed: {e}")
            await self.tracer.markdown(f"**Error:** Report synthesis failed - {e}\n")
            return {
                **state,
                "errors": state.get("errors", []) + [str(e)],
                "current_stage": "error",
            }

    async def run_async(self) -> str:
        """Execute the weekly report workflow asynchronously."""
        await self.tracer.markdown("## Weekly Regulatory Intelligence Digest\n")
        await self.tracer.markdown(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        try:
            # Initialize Graphiti
            await self.tracer.markdown("### Initializing Knowledge Graph Connection\n")
            self.graphiti_client = await self._init_graphiti()
            await self.tracer.markdown("**Connected to Graphiti**\n")

            # Build workflow
            self.graph = self._build_workflow()

            # Prepare initial state
            initial_state = {
                "week_input": self.inputs.get("week_input", ""),
                "resolved_week_start": self.inputs.get("resolved_week_start"),
                "resolved_week_end": self.inputs.get("resolved_week_end"),
                "resolved_week_label": self.inputs.get("resolved_week_label"),
                "resolved_week_number": self.inputs.get("resolved_week_number"),
                "resolved_year": self.inputs.get("resolved_year"),
                "include_events": self.inputs.get("include_events", True),
                "current_stage": "init",
                "errors": [],
                "warnings": [],
                "completed_categories": [],
            }

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
            logger.exception(f"Weekly report workflow failed: {e}")
            await self.tracer.markdown(f"**Fatal Error:** {e}\n")
            return f"# Report Generation Failed\n\n**Error:** {e}"

        finally:
            # Cleanup Graphiti client
            if self.graphiti_client:
                try:
                    await self.graphiti_client.close()
                except Exception:
                    pass

async def execute_weekly_report(inputs: dict, tracer: Tracer):
    """
    Entry point for Kodosumi workflow execution.

    This function is called by Kodosumi's Launch mechanism.
    """
    processor = WeeklyReportProcessor(tracer, inputs)
    final_report = await processor.run_async()
    return core.response.Markdown(final_report)
