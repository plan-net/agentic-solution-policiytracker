"""
Report Synthesizer for Weekly Digest v2.

Agent 3 in the three-agent architecture. Synthesizes findings from all categories
into an executive summary and prepares the final report structure for rendering.

Works with the new state structure from ToolExecutorAgent which provides:
- findings_by_category: dict[str, list[dict]] - findings organized by category
- summaries: dict[str, str] - category summaries
- all_entities: list[str] - discovered entities
"""

import logging
from datetime import datetime
from typing import Any, Optional

import langwatch
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage

from src.chat.observability.langwatch_config import langwatch_config
from src.core.observability.tracer import AgentTracer
from src.flows.weekly_digest_v2.models import (
    CategoryResearchResult,
    Finding,
    FindingPriority,
    ReportMetadata,
)
from src.flows.weekly_digest_v2.prompts.synthesis import (
    EXECUTIVE_SUMMARY_SYSTEM_PROMPT,
    EXECUTIVE_SUMMARY_USER_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)


class ReportSynthesizer:
    """
    Synthesizes category findings into a cohesive executive summary.

    Combines findings from all categories, identifies cross-cutting themes,
    and generates an executive summary suitable for decision-makers.

    Example:
        synthesizer = ReportSynthesizer(llm=llm, tracer=tracer)
        summary = await synthesizer.synthesize(
            category_results=[legislative_result, personnel_result, ...],
            week_label="KW48/2025",
        )

    Attributes:
        llm: LLM for summary generation
        tracer: Optional tracer for observability
    """

    def __init__(
        self,
        llm: BaseLLM,
        tracer: Optional[AgentTracer] = None,
    ):
        """
        Initialize the report synthesizer.

        Args:
            llm: LLM for generating summaries
            tracer: Optional tracer for observability
        """
        self.llm = llm
        self.tracer = tracer

    async def synthesize(
        self,
        category_results: list[CategoryResearchResult],
        week_label: str,
        week_start: datetime,
        week_end: datetime,
    ) -> dict[str, Any]:
        """
        Synthesize all category results into executive summary and report structure.

        Args:
            category_results: Results from all category researchers
            week_label: Formatted week label (e.g., "KW48/2025")
            week_start: Week start date
            week_end: Week end date

        Returns:
            Dictionary with executive_summary, findings_by_category,
            summaries, metadata, and all_entities
        """
        start_time = datetime.now()

        logger.info(
            f"=== SYNTHESIS START === "
            f"Week: {week_label}, "
            f"Categories: {len(category_results)}"
        )

        if self.tracer:
            await self.tracer.markdown(
                f"**Synthesizing report** for {week_label}..."
            )

        # Organize findings by category
        findings_by_category: dict[str, list[dict[str, Any]]] = {}
        summaries: dict[str, str] = {}
        all_entities: list[str] = []
        total_findings = 0

        for result in category_results:
            # Convert findings to dicts for template compatibility
            findings_by_category[result.category] = [
                self._finding_to_dict(f) for f in result.findings
            ]
            summaries[result.category] = result.summary
            total_findings += len(result.findings)

            # Collect entities
            for finding in result.findings:
                all_entities.extend(finding.entities)

            # Collect entities from execution metadata
            if result.execution_metadata:
                entities = result.execution_metadata.get("entities_found", [])
                all_entities.extend(entities)

        # Deduplicate entities
        all_entities = list(set(all_entities))

        # Generate executive summary
        executive_summary = await self._generate_executive_summary(
            category_results, week_label, week_start, week_end
        )

        # Build metadata
        metadata = self._build_metadata(
            category_results, week_label, week_start, week_end, start_time
        )

        execution_time = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"=== SYNTHESIS COMPLETE === "
            f"Findings: {total_findings}, "
            f"Entities: {len(all_entities)}, "
            f"Time: {execution_time:.2f}s"
        )

        if self.tracer:
            await self.tracer.markdown(
                f"**Synthesis complete**: {total_findings} findings, "
                f"{len(all_entities)} entities"
            )

        return {
            "executive_summary": executive_summary,
            "findings_by_category": findings_by_category,
            "summaries": summaries,
            "all_entities": all_entities,
            "metadata": metadata,
            "total_findings": total_findings,
        }

    async def _generate_executive_summary(
        self,
        category_results: list[CategoryResearchResult],
        week_label: str,
        week_start: datetime,
        week_end: datetime,
    ) -> str:
        """
        Generate executive summary from all category results.

        Args:
            category_results: Results from all categories
            week_label: Week label for context
            week_start: Week start date
            week_end: Week end date

        Returns:
            Executive summary text
        """
        # Build context from all categories
        category_summaries = []
        high_priority_findings = []
        forward_looking_items = []

        for result in category_results:
            if result.summary:
                category_summaries.append(
                    f"**{result.category.title()}**: {result.summary}"
                )

            for finding in result.findings:
                if finding.priority == FindingPriority.HIGH:
                    high_priority_findings.append(
                        f"- [{result.category.title()}] {finding.title}"
                    )
                if finding.forward_looking:
                    forward_looking_items.append(
                        f"- [{result.category.title()}] {finding.title}"
                    )

        # Build prompt
        summaries_text = "\n".join(category_summaries) if category_summaries else "No category summaries available."
        high_priority_text = "\n".join(high_priority_findings[:10]) if high_priority_findings else "No high-priority items."
        forward_looking_text = "\n".join(forward_looking_items[:10]) if forward_looking_items else "No forward-looking items."

        # Use the improved prompt template
        synthesis_prompt = EXECUTIVE_SUMMARY_USER_PROMPT_TEMPLATE.format(
            week_label=week_label,
            week_start_str=week_start.strftime("%d %B"),
            week_end_str=week_end.strftime("%d %B %Y"),
            categories_count=len(category_results),
            total_findings=sum(len(r.findings) for r in category_results),
            summaries_text=summaries_text,
            high_priority_text=high_priority_text,
            forward_looking_text=forward_looking_text,
        )

        try:
            messages = [
                SystemMessage(content=EXECUTIVE_SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=synthesis_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return self._generate_fallback_summary(
                category_results, week_label, week_start, week_end
            )

    def _generate_fallback_summary(
        self,
        category_results: list[CategoryResearchResult],
        week_label: str,
        week_start: datetime,
        week_end: datetime,
    ) -> str:
        """Generate basic summary when LLM fails."""
        total_findings = sum(len(r.findings) for r in category_results)
        high_priority = sum(
            1
            for r in category_results
            for f in r.findings
            if f.priority == FindingPriority.HIGH
        )

        summary_lines = [
            f"This week's regulatory intelligence digest covers the period "
            f"{week_start.strftime('%d %B')} to {week_end.strftime('%d %B %Y')}.",
            "",
            f"**Key Statistics:**",
            f"- Total findings: {total_findings}",
            f"- High-priority items: {high_priority}",
            f"- Categories covered: {len(category_results)}",
        ]

        # Add category highlights
        for result in category_results:
            if result.findings:
                top_finding = result.findings[0]
                summary_lines.append(
                    f"- {result.category.title()}: {top_finding.title}"
                )

        return "\n".join(summary_lines)

    def _build_metadata(
        self,
        category_results: list[CategoryResearchResult],
        week_label: str,
        week_start: datetime,
        week_end: datetime,
        start_time: datetime,
    ) -> dict[str, Any]:
        """Build report metadata."""
        # Extract week number and year from label
        try:
            # Parse "KW48/2025" format
            parts = week_label.replace("KW", "").split("/")
            week_number = int(parts[0])
            year = int(parts[1]) if len(parts) > 1 else week_start.year
        except (ValueError, IndexError):
            week_number = week_start.isocalendar()[1]
            year = week_start.year

        # Calculate totals
        total_findings = sum(len(r.findings) for r in category_results)
        categories_completed = sum(1 for r in category_results if r.success)
        total_queries = sum(
            r.execution_metadata.get("searches_successful", 0)
            + r.execution_metadata.get("searches_failed", 0)
            for r in category_results
            if r.execution_metadata
        )

        return {
            "week_number": week_number,
            "year": year,
            "week_label": week_label,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "total_findings": total_findings,
            "categories_completed": categories_completed,
            "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
            "graphiti_queries_executed": total_queries,
        }

    @staticmethod
    def _finding_to_dict(finding: Finding) -> dict[str, Any]:
        """Convert Finding to dictionary for template compatibility."""
        return {
            "title": finding.title,
            "content": finding.content,
            "impact": finding.impact,
            "action": finding.action,
            "category": finding.category,
            "priority": finding.priority.value if hasattr(finding.priority, "value") else finding.priority,
            "date": finding.date.isoformat() if finding.date else None,
            "source": finding.source,
            "entities": finding.entities,
            "forward_looking": finding.forward_looking,
            "metadata": finding.metadata,
        }

    async def synthesize_from_state(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Synthesize executive summary from the new state structure.

        This method is called by the orchestrator's _report_synthesizer_node
        and works with the state populated by ToolExecutorAgent.

        Args:
            state: Workflow state containing:
                - findings_by_category: dict[str, list[dict]] - findings per category
                - summaries: dict[str, str] - category summaries
                - all_entities: list[str] - discovered entities
                - week_label: str - formatted week label
                - week_start: datetime - week start
                - week_end: datetime - week end

        Returns:
            State update dict with:
                - executive_summary: str
                - synthesis_metadata: dict
        """
        start_time = datetime.now()

        findings_by_category = state.get("findings_by_category", {})
        summaries = state.get("summaries", {})
        all_entities = state.get("all_entities", [])
        week_label = state.get("week_label", "")
        week_start = state.get("week_start")
        week_end = state.get("week_end")

        total_findings = sum(len(f) for f in findings_by_category.values())

        logger.info(
            f"=== SYNTHESIS START (from state) === "
            f"Week: {week_label}, "
            f"Categories: {len(findings_by_category)}, "
            f"Total Findings: {total_findings}"
        )

        if self.tracer:
            await self.tracer.markdown(
                f"**Synthesizing report** for {week_label}...\n"
                f"Categories: {len(findings_by_category)}, "
                f"Findings: {total_findings}\n"
            )

        # Generate executive summary using LLM
        with langwatch.trace(
            name="llm:generate_executive_summary",
            metadata={
                "categories_count": len(findings_by_category),
                "total_findings": total_findings,
            },
        ):
            executive_summary = await self._generate_executive_summary_from_state(
                findings_by_category=findings_by_category,
                summaries=summaries,
                week_label=week_label,
                week_start=week_start,
                week_end=week_end,
            )

        execution_time = (datetime.now() - start_time).total_seconds()

        # Build synthesis metadata
        synthesis_metadata = {
            "week_label": week_label,
            "categories_synthesized": len(findings_by_category),
            "total_findings": total_findings,
            "entities_count": len(all_entities),
            "synthesis_time_seconds": execution_time,
            "generated_at": datetime.now().isoformat(),
        }

        logger.info(
            f"=== SYNTHESIS COMPLETE === "
            f"Time: {execution_time:.2f}s"
        )

        if self.tracer:
            await self.tracer.markdown(
                f"**Synthesis complete**: {total_findings} findings, "
                f"{len(all_entities)} entities\n"
            )

        # Capture synthesis in LangWatch
        langwatch_config.capture_tool_execution(
            tool_name="report_synthesis",
            tool_input={
                "categories": list(findings_by_category.keys()),
                "total_findings": total_findings,
            },
            tool_output={
                "summary_length": len(executive_summary),
            },
            execution_time=execution_time,
            success=True,
        )

        return {
            "executive_summary": executive_summary,
            "synthesis_metadata": synthesis_metadata,
        }

    async def _generate_executive_summary_from_state(
        self,
        findings_by_category: dict[str, list[dict[str, Any]]],
        summaries: dict[str, str],
        week_label: str,
        week_start: Optional[datetime],
        week_end: Optional[datetime],
    ) -> str:
        """
        Generate executive summary from findings_by_category state.

        Args:
            findings_by_category: Findings organized by category name
            summaries: Category summaries
            week_label: Week label for context
            week_start: Week start date
            week_end: Week end date

        Returns:
            Executive summary text
        """
        # Build context from findings
        category_summaries_text = []
        high_priority_findings = []
        forward_looking_items = []

        for category_name, findings in findings_by_category.items():
            # Add category summary
            summary = summaries.get(category_name, "")
            if summary:
                display_name = category_name.replace("_", " ").title()
                category_summaries_text.append(f"**{display_name}**: {summary}")

            # Extract high priority and forward-looking items
            for finding in findings:
                priority = finding.get("priority", "medium")
                if priority == "high":
                    display_name = category_name.replace("_", " ").title()
                    high_priority_findings.append(
                        f"- [{display_name}] {finding.get('title', '')}"
                    )
                if finding.get("forward_looking", False):
                    display_name = category_name.replace("_", " ").title()
                    forward_looking_items.append(
                        f"- [{display_name}] {finding.get('title', '')}"
                    )

        # Build prompt
        summaries_text = (
            "\n".join(category_summaries_text)
            if category_summaries_text
            else "No category summaries available."
        )
        high_priority_text = (
            "\n".join(high_priority_findings[:10])
            if high_priority_findings
            else "No high-priority items."
        )
        forward_looking_text = (
            "\n".join(forward_looking_items[:10])
            if forward_looking_items
            else "No forward-looking items."
        )

        week_start_str = week_start.strftime("%d %B") if week_start else "start"
        week_end_str = week_end.strftime("%d %B %Y") if week_end else "end"

        # Calculate total findings
        total_findings = sum(len(f) for f in findings_by_category.values())

        # Use the improved prompt template
        synthesis_prompt = EXECUTIVE_SUMMARY_USER_PROMPT_TEMPLATE.format(
            week_label=week_label,
            week_start_str=week_start_str,
            week_end_str=week_end_str,
            categories_count=len(findings_by_category),
            total_findings=total_findings,
            summaries_text=summaries_text,
            high_priority_text=high_priority_text,
            forward_looking_text=forward_looking_text,
        )

        try:
            messages = [
                SystemMessage(content=EXECUTIVE_SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=synthesis_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            logger.error(f"Executive summary generation failed: {e}")
            return self._generate_fallback_summary_from_state(
                findings_by_category, week_label, week_start, week_end
            )

    def _generate_fallback_summary_from_state(
        self,
        findings_by_category: dict[str, list[dict[str, Any]]],
        week_label: str,
        week_start: Optional[datetime],
        week_end: Optional[datetime],
    ) -> str:
        """Generate basic summary when LLM fails (state-based version)."""
        total_findings = sum(len(f) for f in findings_by_category.values())
        high_priority = sum(
            1
            for findings in findings_by_category.values()
            for f in findings
            if f.get("priority") == "high"
        )

        week_start_str = week_start.strftime("%d %B") if week_start else "start"
        week_end_str = week_end.strftime("%d %B %Y") if week_end else "end"

        summary_lines = [
            f"This week's regulatory intelligence digest covers the period "
            f"{week_start_str} to {week_end_str}.",
            "",
            "**Key Statistics:**",
            f"- Total findings: {total_findings}",
            f"- High-priority items: {high_priority}",
            f"- Categories covered: {len(findings_by_category)}",
        ]

        # Add category highlights
        for category_name, findings in findings_by_category.items():
            if findings:
                top_finding = findings[0]
                display_name = category_name.replace("_", " ").title()
                summary_lines.append(
                    f"- {display_name}: {top_finding.get('title', 'N/A')}"
                )

        return "\n".join(summary_lines)
