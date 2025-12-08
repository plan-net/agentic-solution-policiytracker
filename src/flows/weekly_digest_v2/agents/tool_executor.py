"""
Tool Executor Agent for Weekly Digest v2.

Agent 2 in the three-agent architecture. Executes all tool calls based on the
research plan from ResearchPlannerAgent, extracts findings using LLM.

Output format matches src/chat/agent/agents.py ToolExecutionAgent for consistency.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

import langwatch
from graphiti_core import Graphiti
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage

from src.chat.observability.langwatch_config import langwatch_config
from src.chat.tools.search import GraphitiSearchTool
from src.core.observability.tracer import AgentTracer
from src.flows.weekly_digest_v2.models import Finding, FindingPriority
from src.flows.weekly_digest_v2.prompts.extraction import (
    FINDING_EXTRACTION_SYSTEM_PROMPT,
    FINDING_EXTRACTION_USER_PROMPT_TEMPLATE,
)

from .base import ExecutionMetadata, ToolResult, WeeklyDigestState

logger = logging.getLogger(__name__)


class ToolExecutorAgent:
    """
    Agent 2: Executes all tool calls based on research plan.

    Executes Graphiti searches for all categories in the research plan,
    extracts findings using LLM, and returns structured results matching
    the chat implementation's ToolExecutionAgent format.

    Example:
        executor = ToolExecutorAgent(
            graphiti_client=client,
            llm=llm,
            tracer=tracer,
        )
        state_update = await executor.process(state)

    Attributes:
        graphiti_client: Graphiti client for knowledge graph access
        search_tool: GraphitiSearchTool wrapper
        llm: LLM for finding extraction
        tracer: AgentTracer for observability
    """

    def __init__(
        self,
        graphiti_client: Graphiti,
        llm: BaseLLM,
        tracer: Optional[AgentTracer] = None,
    ):
        """
        Initialize the tool executor agent.

        Args:
            graphiti_client: Graphiti client for searches
            llm: LLM for processing results and extracting findings
            tracer: Optional tracer for observability
        """
        self.graphiti_client = graphiti_client
        self.search_tool = GraphitiSearchTool(graphiti_client=graphiti_client)
        self.llm = llm
        self.tracer = tracer

    async def process(self, state: WeeklyDigestState) -> dict[str, Any]:
        """
        Execute all searches and extract findings.

        Iterates through the research plan, executes tool sequences for each
        category, extracts findings using LLM, and returns structured results.

        Args:
            state: Current workflow state with research_plan

        Returns:
            State update matching chat's ToolExecutionAgent output:
            - tool_results: list[ToolResult dict]
            - executed_tools: list[str]
            - execution_metadata: dict
            - findings_by_category: dict[str, list[dict]]
            - summaries: dict[str, str]
        """
        research_plan = state.get("research_plan", {})
        week_start = state.get("week_start")
        week_end = state.get("week_end")

        if not research_plan:
            logger.error("No research plan available for execution")
            return {
                "tool_results": [],
                "executed_tools": [],
                "execution_metadata": {
                    "total_execution_time": 0.0,
                    "tools_successful": 0,
                    "tools_failed": 0,
                    "information_quality": "none",
                },
                "errors": state.get("errors", []) + ["No research plan available"],
            }

        logger.info(
            f"=== TOOL EXECUTOR START === "
            f"Categories: {len(research_plan)}, "
            f"Week: {week_start.strftime('%Y-%m-%d') if week_start else 'N/A'}"
        )

        if self.tracer:
            await self.tracer.markdown("### Executing Research Tools\n")

        tool_results: list[dict[str, Any]] = []
        executed_tools: list[str] = []
        findings_by_category: dict[str, list[dict[str, Any]]] = {}
        summaries: dict[str, str] = {}
        all_entities: list[str] = []
        total_execution_time = 0.0

        for category_name, plan in research_plan.items():
            # Each category's tool execution is a visible span
            with langwatch.trace(
                name=f"execute_{category_name}",
                metadata={
                    "category": category_name,
                    "display_name": plan["display_name"],
                    "queries_count": len(plan["queries"]),
                },
            ):
                if self.tracer:
                    await self.tracer.markdown(f"#### {plan['display_name']}\n")

                category_start_time = datetime.now()
                category_raw_results: list[dict[str, Any]] = []
                category_entities: list[dict[str, str]] = []
                category_sources: list[str] = []

                # Execute tool sequence for this category
                for tool_spec in plan["tool_sequence"]:
                    # Each tool call is a visible span
                    with langwatch.trace(
                        name=f"tool:{tool_spec['tool_name']}",
                        metadata={
                            "category": category_name,
                            "search_type": tool_spec["search_type"],
                        },
                    ):
                        tool_start_time = datetime.now()

                        # Execute search for each query
                        for query in plan["queries"]:
                            try:
                                result = await asyncio.wait_for(
                                    self.search_tool._arun(
                                        query=query,
                                        limit=tool_spec["limit"],
                                        search_type=tool_spec["search_type"],
                                        output_format="structured",
                                        # Pass temporal date filtering for Graphiti
                                        date_filter_start=week_start,
                                        date_filter_end=week_end,
                                        # Use category's temporal filter strategy
                                        temporal_filter_strategy=plan.get(
                                            "temporal_filter_strategy", "comprehensive"
                                        ),
                                    ),
                                    timeout=tool_spec["timeout_seconds"],
                                )

                                # Process results
                                if isinstance(result, dict) and "results" in result:
                                    for r in result["results"]:
                                        category_raw_results.append({
                                            "type": r.get("type", "fact"),
                                            "content": r.get("content", ""),
                                            "relevance_score": r.get("relevance_score"),
                                            "source": r.get("source"),
                                            "name": r.get("name", "Unknown"),
                                        })

                                        # Extract entity names
                                        if r.get("name") and r.get("type") == "entity":
                                            category_entities.append({
                                                "name": r["name"],
                                                "type": r.get("entity_type", "unknown"),
                                            })
                                            all_entities.append(r["name"])

                                        # Extract sources
                                        if r.get("source") and isinstance(r["source"], dict):
                                            source_title = r["source"].get("title", "")
                                            if source_title:
                                                category_sources.append(source_title)

                            except asyncio.TimeoutError:
                                logger.warning(
                                    f"Query timed out for {category_name}: {query[:50]}..."
                                )
                            except Exception as e:
                                logger.warning(
                                    f"Query failed for {category_name}: {query[:50]}... - {e}"
                                )

                        tool_execution_time = (
                            datetime.now() - tool_start_time
                        ).total_seconds()

                        # Capture in LangWatch
                        langwatch_config.capture_tool_execution(
                            tool_name=tool_spec["tool_name"],
                            tool_input={
                                "category": category_name,
                                "queries": plan["queries"][:3],
                                "search_type": tool_spec["search_type"],
                            },
                            tool_output={
                                "results_count": len(category_raw_results),
                            },
                            execution_time=tool_execution_time,
                            success=True,
                        )

                # Check if LLM extraction should be skipped
                skip_llm = plan.get("skip_llm_extraction", False)

                if skip_llm:
                    # Create findings directly from raw results (no LLM)
                    with langwatch.trace(
                        name=f"raw:extract_findings_{category_name}",
                        metadata={
                            "results_count": len(category_raw_results),
                            "skip_llm_extraction": True,
                        },
                    ):
                        logger.info(
                            f"Skipping LLM extraction for {category_name} "
                            f"(skip_llm_extraction=True)"
                        )
                        findings = self._create_findings_from_raw(
                            category_raw_results,
                            category_name,
                            plan["max_findings"],
                        )
                else:
                    # Extract findings using LLM (visible as LLM span)
                    with langwatch.trace(
                        name=f"llm:extract_findings_{category_name}",
                        metadata={
                            "results_count": len(category_raw_results),
                            "skip_llm_extraction": False,
                        },
                    ):
                        findings = await self._extract_findings(
                            category_raw_results,
                            plan["system_prompt"],
                            plan["display_name"],
                            category_name,
                            week_start,
                            week_end,
                            plan["max_findings"],
                        )

                # Calculate metrics
                category_execution_time = (
                    datetime.now() - category_start_time
                ).total_seconds()
                total_execution_time += category_execution_time

                relevance_scores = [
                    r["relevance_score"]
                    for r in category_raw_results
                    if r.get("relevance_score") is not None
                ]
                avg_relevance = (
                    sum(relevance_scores) / len(relevance_scores)
                    if relevance_scores
                    else 0.0
                )

                # Generate category summary
                summary = self._generate_category_summary(findings, plan["display_name"])
                summaries[category_name] = summary

                # Convert findings to dicts
                findings_dicts = [f.model_dump() for f in findings]
                findings_by_category[category_name] = findings_dicts

                # Build ToolResult matching chat format
                tool_result = ToolResult(
                    tool_name=f"category_research_{category_name}",
                    success=len(findings) > 0 or len(category_raw_results) > 0,
                    execution_time=category_execution_time,
                    parameters_used={
                        "category": category_name,
                        "queries_count": len(plan["queries"]),
                        "search_type": plan["search_type"],
                    },
                    output=f"Found {len(findings)} findings from {len(category_raw_results)} results",
                    insights=[f.title for f in findings[:3]],
                    entities_found=category_entities[:20],
                    relationships_discovered=[],
                    source_citations=list(set(category_sources))[:10],
                    temporal_aspects=[
                        f.date.isoformat() if f.date else ""
                        for f in findings
                        if f.date
                    ],
                    quality_score=self._calculate_quality_score(
                        findings, category_raw_results, avg_relevance
                    ),
                    error=None,
                    category=category_name,
                    findings=findings_dicts,
                )

                tool_results.append(tool_result.model_dump())
                executed_tools.append(f"category_research_{category_name}")

                if self.tracer:
                    await self.tracer.markdown(
                        f"**Found {len(findings)} findings** "
                        f"({len(category_raw_results)} raw results, "
                        f"{category_execution_time:.2f}s)\n"
                    )

                logger.info(
                    f"=== CATEGORY COMPLETE === "
                    f"Category: {category_name}, "
                    f"Findings: {len(findings)}, "
                    f"Raw Results: {len(category_raw_results)}, "
                    f"Time: {category_execution_time:.2f}s"
                )

        # Build execution metadata matching chat format
        execution_metadata: ExecutionMetadata = {
            "total_execution_time": total_execution_time,
            "tools_successful": sum(1 for r in tool_results if r["success"]),
            "tools_failed": sum(1 for r in tool_results if not r["success"]),
            "information_quality": self._assess_overall_quality(tool_results),
        }

        logger.info(
            f"=== TOOL EXECUTOR COMPLETE === "
            f"Categories: {len(research_plan)}, "
            f"Total Findings: {sum(len(f) for f in findings_by_category.values())}, "
            f"Time: {total_execution_time:.2f}s"
        )

        if self.tracer:
            await self.tracer.markdown(
                f"**Execution Complete:** "
                f"{execution_metadata['tools_successful']} successful, "
                f"{total_execution_time:.2f}s total\n"
            )

        return {
            "tool_results": tool_results,
            "executed_tools": executed_tools,
            "execution_metadata": execution_metadata,
            "findings_by_category": findings_by_category,
            "summaries": summaries,
            "all_entities": list(set(all_entities)),
            "current_stage": "execution_complete",
            "current_agent": "report_synthesizer",
        }

    async def _extract_findings(
        self,
        results: list[dict[str, Any]],
        system_prompt: str,
        display_name: str,
        category_name: str,
        week_start: Optional[datetime],
        week_end: Optional[datetime],
        max_findings: int,
    ) -> list[Finding]:
        """
        Extract structured findings from search results using LLM.

        Args:
            results: Raw search results
            system_prompt: Category-specific system prompt
            display_name: Display name for the category
            category_name: Internal category name
            week_start: Week start date
            week_end: Week end date
            max_findings: Maximum findings to extract

        Returns:
            List of extracted findings
        """
        if not results:
            return []

        # Format results for LLM
        formatted_results = []
        for r in results[:15]:  # Limit to prevent token overflow
            line = f"- [{r['type']}]"
            if r.get("relevance_score") is not None:
                line += f" [Score: {r['relevance_score']:.2f}]"
            line += f" {r['content'][:200]}"
            if r.get("source") and isinstance(r["source"], dict):
                source_title = r["source"].get("title", "")
                if source_title:
                    line += f" [Source: {source_title}]"
            formatted_results.append(line)

        results_text = "\n".join(formatted_results)

        # Build extraction prompt using improved template
        week_start_str = week_start.strftime("%d %B") if week_start else "start"
        week_end_str = week_end.strftime("%d %B %Y") if week_end else "end"

        extraction_prompt = FINDING_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            week_start_str=week_start_str,
            week_end_str=week_end_str,
            results_text=results_text,
            display_name=display_name,
            max_findings=max_findings,
        )

        try:
            messages = [
                SystemMessage(content=FINDING_EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=extraction_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            if "NO_FINDINGS" in response_text:
                return []

            return self._parse_llm_findings(response_text, category_name)

        except Exception as e:
            logger.warning(f"LLM extraction failed for {category_name}: {e}")
            return self._create_fallback_findings(results, category_name)

    def _parse_llm_findings(
        self, response_text: str, category_name: str
    ) -> list[Finding]:
        """Parse structured findings from LLM response."""
        findings = []
        finding_blocks = response_text.split("---")

        for block in finding_blocks:
            if "FINDING:" not in block and "Title:" not in block:
                continue

            try:
                lines = block.strip().split("\n")
                finding_data: dict[str, Any] = {}

                for line in lines:
                    if line.startswith("Title:"):
                        finding_data["title"] = line.replace("Title:", "").strip()
                    elif line.startswith("Content:"):
                        finding_data["content"] = line.replace("Content:", "").strip()
                    elif line.startswith("Impact:"):
                        impact_str = line.replace("Impact:", "").strip()
                        if impact_str and impact_str.lower() != "not specified":
                            finding_data["impact"] = impact_str
                    elif line.startswith("Action:"):
                        action_str = line.replace("Action:", "").strip()
                        if action_str and action_str.lower() != "not specified":
                            finding_data["action"] = action_str
                    elif line.startswith("Date:"):
                        date_str = line.replace("Date:", "").strip()
                        if date_str and date_str.lower() != "not specified":
                            try:
                                finding_data["date"] = datetime.strptime(
                                    date_str, "%Y-%m-%d"
                                )
                            except ValueError:
                                pass
                    elif line.startswith("Priority:"):
                        priority_str = line.replace("Priority:", "").strip().lower()
                        if priority_str in ["high", "medium", "low"]:
                            finding_data["priority"] = FindingPriority(priority_str)
                    elif line.startswith("Forward-looking:"):
                        forward = line.replace("Forward-looking:", "").strip().lower()
                        finding_data["forward_looking"] = forward == "yes"
                    elif line.startswith("Source:"):
                        source_str = line.replace("Source:", "").strip()
                        if source_str and source_str.lower() != "not specified":
                            finding_data["source"] = source_str
                    elif line.startswith("Entities:"):
                        entities_str = line.replace("Entities:", "").strip()
                        if entities_str and entities_str.lower() != "none":
                            finding_data["entities"] = [
                                e.strip() for e in entities_str.split(",")
                            ]

                if finding_data.get("title") and finding_data.get("content"):
                    findings.append(
                        Finding(
                            title=finding_data["title"],
                            content=finding_data["content"],
                            impact=finding_data.get("impact"),
                            action=finding_data.get("action"),
                            category=category_name,
                            priority=finding_data.get("priority", FindingPriority.MEDIUM),
                            date=finding_data.get("date"),
                            source=finding_data.get("source"),
                            entities=finding_data.get("entities", []),
                            forward_looking=finding_data.get("forward_looking", False),
                        )
                    )

            except Exception as e:
                logger.debug(f"Failed to parse finding block: {e}")
                continue

        return findings

    def _create_fallback_findings(
        self, results: list[dict[str, Any]], category_name: str
    ) -> list[Finding]:
        """Create basic findings from raw results (fallback)."""
        findings = []
        for result in results[:5]:
            content = result.get("content", "")
            if len(content) > 50:
                source = None
                source_data = result.get("source")
                if source_data and isinstance(source_data, dict):
                    source = source_data.get("title")

                findings.append(
                    Finding(
                        title=content[:50] + "...",
                        content=content[:200],
                        category=category_name,
                        priority=FindingPriority.MEDIUM,
                        source=source,
                    )
                )
        return findings

    def _create_findings_from_raw(
        self,
        results: list[dict[str, Any]],
        category_name: str,
        max_findings: int,
    ) -> list[Finding]:
        """
        Create Finding objects directly from raw Graphiti results.

        Skips LLM extraction - useful when temporal filtering already
        ensures relevance, or for performance optimization.

        Args:
            results: Raw search results from Graphiti
            category_name: Name of the category
            max_findings: Maximum number of findings to create

        Returns:
            List of Finding objects created directly from raw results
        """
        findings = []
        for result in results[:max_findings]:
            content = result.get("content", "")
            if not content or len(content) < 20:
                continue

            # Extract source
            source = None
            source_data = result.get("source")
            if source_data and isinstance(source_data, dict):
                source = source_data.get("title")

            # Create title from content (truncate if needed)
            title = content[:80] + "..." if len(content) > 80 else content

            # Truncate content for finding
            finding_content = content[:500] if len(content) > 500 else content

            # Extract entity name if available
            entities = []
            if result.get("name") and result.get("type") == "entity":
                entities.append(result["name"])

            findings.append(
                Finding(
                    title=title,
                    content=finding_content,
                    category=category_name,
                    priority=FindingPriority.MEDIUM,  # Default priority without LLM
                    source=source,
                    entities=entities,
                    forward_looking=False,  # Cannot determine without LLM
                )
            )

        logger.info(
            f"Created {len(findings)} findings from raw results for {category_name} "
            f"(skip_llm_extraction=True)"
        )
        return findings

    def _generate_category_summary(
        self, findings: list[Finding], display_name: str
    ) -> str:
        """Generate a brief summary of findings for a category."""
        if not findings:
            return f"No significant {display_name.lower()} developments found this week."

        high_priority = [f for f in findings if f.priority == FindingPriority.HIGH]
        forward_looking = [f for f in findings if f.forward_looking]

        summary_parts = [f"Found {len(findings)} {display_name.lower()} developments."]

        if high_priority:
            summary_parts.append(f"{len(high_priority)} high-priority items.")

        if forward_looking:
            summary_parts.append(
                f"{len(forward_looking)} forward-looking items with upcoming dates."
            )

        return " ".join(summary_parts)

    def _calculate_quality_score(
        self,
        findings: list[Finding],
        raw_results: list[dict[str, Any]],
        avg_relevance: float,
    ) -> float:
        """Calculate quality score for category research."""
        if not raw_results:
            return 0.0

        # Factors: relevance, finding extraction success, high-priority items
        relevance_factor = min(avg_relevance, 1.0)
        extraction_factor = len(findings) / max(len(raw_results), 1) if raw_results else 0
        high_priority_factor = (
            sum(1 for f in findings if f.priority == FindingPriority.HIGH)
            / max(len(findings), 1)
            if findings
            else 0
        )

        # Weighted average
        score = (relevance_factor * 0.5) + (extraction_factor * 0.3) + (high_priority_factor * 0.2)
        return min(max(score, 0.0), 1.0)

    def _assess_overall_quality(self, tool_results: list[dict[str, Any]]) -> str:
        """Assess overall information quality from all tool results."""
        if not tool_results:
            return "none"

        avg_quality = sum(r["quality_score"] for r in tool_results) / len(tool_results)

        if avg_quality > 0.6:
            return "high"
        elif avg_quality > 0.3:
            return "medium"
        else:
            return "low"
