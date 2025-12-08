"""
Configurable Category Researcher for Weekly Digest v2.

YAML-driven category research agent that executes tool plans from configuration.
Replaces the hardcoded category agents from v1 with a single configurable class.

Key features:
- Loads search queries and prompts from YAML category configs
- Executes tool plans (comprehensive/focused) from YAML tool plan configs
- Integrates with LangWatch for observability
- Supports conditional tool execution based on context
"""

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

import langwatch
from graphiti_core import Graphiti
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage

from src.chat.observability.langwatch_config import langwatch_config
from src.chat.tools.search import GraphitiSearchTool
from src.core.config.category_config import CategoryConfig, SearchType
from src.core.config.tool_plan_config import ToolPlanConfig, ToolSpec
from src.core.observability.tracer import AgentTracer
from src.flows.weekly_digest_v2.models import (
    CategoryResearchResult,
    Finding,
    FindingPriority,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchExecution:
    """
    Tracks a single search execution for observability.

    Captures execution metadata for LangWatch and debugging.
    """

    tool_name: str = "graphiti_search"
    query: str = ""
    search_type: str = ""
    category: str = ""
    success: bool = True
    execution_time: float = 0.0
    results_count: int = 0
    relevance_scores: list[float] = field(default_factory=list)
    sources_found: list[str] = field(default_factory=list)
    entities_found: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    error: Optional[str] = None
    step_description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class ConfigurableCategoryResearcher:
    """
    YAML-driven category researcher.

    Executes category research based on YAML configurations for categories
    and tool plans. Provides a single configurable class replacing the
    multiple hardcoded category agents from v1.

    Example:
        config = CategoryConfig.from_yaml(Path("config/categories/legislative.yaml"))
        tool_plan = ToolPlanConfig.from_yaml(Path("config/tool_plans/comprehensive.yaml"))
        researcher = ConfigurableCategoryResearcher(
            category_config=config,
            tool_plan=tool_plan,
            graphiti_client=client,
            llm=llm,
            tracer=tracer,
        )
        result = await researcher.research(week_start, week_end)

    Attributes:
        category_config: Category configuration loaded from YAML
        tool_plan: Tool plan configuration loaded from YAML
        graphiti_client: Graphiti client for knowledge graph access
        llm: LLM for finding extraction
        tracer: AgentTracer for observability
    """

    def __init__(
        self,
        category_config: CategoryConfig,
        tool_plan: ToolPlanConfig,
        graphiti_client: Graphiti,
        llm: BaseLLM,
        tracer: Optional[AgentTracer] = None,
    ):
        """
        Initialize the configurable category researcher.

        Args:
            category_config: Category configuration from YAML
            tool_plan: Tool plan configuration from YAML
            graphiti_client: Graphiti client for searches
            llm: LLM for processing results
            tracer: Optional tracer for observability
        """
        self.category_config = category_config
        self.tool_plan = tool_plan
        self.graphiti_client = graphiti_client
        self.llm = llm
        self.tracer = tracer

        # Create search tool
        self.search_tool = GraphitiSearchTool(graphiti_client=graphiti_client)

    @property
    def category_name(self) -> str:
        """Return the category name."""
        return self.category_config.name

    @property
    def display_name(self) -> str:
        """Return the display name."""
        return self.category_config.display_name

    async def research(
        self,
        week_start: datetime,
        week_end: datetime,
    ) -> CategoryResearchResult:
        """
        Execute category research following the configured tool plan.

        Args:
            week_start: Start of the week (Monday 00:00)
            week_end: End of the week (Sunday 23:59)

        Returns:
            CategoryResearchResult with findings, summary, and metadata
        """
        start_time = datetime.now()
        all_findings: list[Finding] = []
        all_executions: list[SearchExecution] = []
        all_entities: list[str] = []
        errors: list[str] = []

        # Log research start
        logger.info(
            f"=== CATEGORY RESEARCH START === "
            f"Category: {self.category_name}, "
            f"Plan: {self.tool_plan.name}, "
            f"Week: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
        )

        if self.tracer:
            await self.tracer.markdown(
                f"**Researching {self.display_name}** using {self.tool_plan.name} plan..."
            )

        try:
            # Build execution context for conditional tools
            context: dict[str, Any] = {
                "entities_found": [],
                "findings": [],
                "category": self.category_name,
            }

            # Execute tool sequence
            for tool_spec in self.tool_plan.tool_sequence:
                # Check if tool should execute
                if not tool_spec.should_execute(context):
                    logger.debug(
                        f"Skipping tool {tool_spec.tool_name} "
                        f"(condition: {tool_spec.conditional})"
                    )
                    continue

                # Execute the tool
                try:
                    execution, findings, entities = await self._execute_tool(
                        tool_spec, week_start, week_end, context
                    )
                    all_executions.append(execution)

                    if findings:
                        all_findings.extend(findings)
                        context["findings"].extend(findings)

                    if entities:
                        all_entities.extend(entities)
                        context["entities_found"].extend(entities)

                except asyncio.TimeoutError:
                    error_msg = (
                        f"Timeout executing {tool_spec.tool_name} "
                        f"after {tool_spec.timeout_seconds}s"
                    )
                    logger.warning(error_msg)
                    errors.append(error_msg)

                    if tool_spec.required:
                        raise

                except Exception as e:
                    error_msg = f"Tool {tool_spec.tool_name} failed: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

                    # Record failed execution
                    all_executions.append(
                        SearchExecution(
                            tool_name=tool_spec.tool_name,
                            category=self.category_name,
                            success=False,
                            error=str(e),
                            step_description=tool_spec.description,
                        )
                    )

                    if tool_spec.required:
                        raise

            # Check for fallback plan if no findings
            if not all_findings and self.tool_plan.fallback_plan:
                logger.info(
                    f"No findings from {self.tool_plan.name} plan, "
                    f"fallback to {self.tool_plan.fallback_plan} not implemented"
                )

            # Deduplicate and rank findings
            all_findings = self._deduplicate_findings(all_findings)
            all_findings = self._rank_findings(all_findings)

            # Limit to max findings
            all_findings = all_findings[: self.category_config.max_findings]

            # Generate summary
            summary = await self._generate_summary(all_findings)

            # Build execution metadata
            execution_metadata = self._build_execution_metadata(all_executions)
            execution_metadata["entities_found"] = list(set(all_entities))

            execution_time = (datetime.now() - start_time).total_seconds()

            # Log completion
            successful = sum(1 for e in all_executions if e.success)
            logger.info(
                f"=== CATEGORY RESEARCH COMPLETE === "
                f"Category: {self.category_name}, "
                f"Findings: {len(all_findings)}, "
                f"Searches: {len(all_executions)}, "
                f"Success Rate: {successful}/{len(all_executions)}, "
                f"Time: {execution_time:.2f}s"
            )

            if self.tracer:
                await self.tracer.markdown(
                    f"Found **{len(all_findings)} findings** for {self.display_name}"
                )

            return CategoryResearchResult(
                category=self.category_name,
                findings=all_findings,
                summary=summary,
                query_used="; ".join(self.category_config.search_queries[:3]),
                execution_time=execution_time,
                success=len(errors) == 0,
                error="; ".join(errors) if errors else None,
                execution_metadata=execution_metadata,
            )

        except Exception as e:
            logger.error(
                f"=== CATEGORY RESEARCH FAILED === "
                f"Category: {self.category_name}: {e}"
            )
            return CategoryResearchResult(
                category=self.category_name,
                findings=[],
                summary=f"Research failed: {e}",
                execution_time=(datetime.now() - start_time).total_seconds(),
                success=False,
                error=str(e),
                execution_metadata={"error": str(e)},
            )

    async def _execute_tool(
        self,
        tool_spec: ToolSpec,
        week_start: datetime,
        week_end: datetime,
        context: dict[str, Any],
    ) -> tuple[SearchExecution, list[Finding], list[str]]:
        """
        Execute a single tool from the tool plan.

        Args:
            tool_spec: Tool specification from plan
            week_start: Week start date
            week_end: Week end date
            context: Current execution context

        Returns:
            Tuple of (SearchExecution, findings, entities)
        """
        # Determine search type early for trace metadata
        if tool_spec.search_type == "from_category":
            search_type = self.category_config.search_type.value
        else:
            search_type = tool_spec.search_type

        # Wrap entire tool execution in LangWatch trace for visibility
        with langwatch.trace(
            name=f"tool:{tool_spec.tool_name}",
            metadata={
                "category": self.category_name,
                "search_type": search_type,
                "tool_name": tool_spec.tool_name,
            },
        ):
            start_time = datetime.now()

            # Log tool execution
            logger.info(
                f"=== TOOL EXECUTION === "
                f"Tool: {tool_spec.tool_name}, "
                f"Search Type: {search_type}, "
                f"Category: {self.category_name}"
            )

            all_results: list[dict[str, Any]] = []
            all_entities: list[str] = []

            # Execute search for each configured query
            for query in self.category_config.search_queries:
                # Add temporal context
                temporal_query = self.category_config.get_temporal_query(
                    query, week_start.year
                )

                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        self.search_tool._arun(
                            query=temporal_query,
                            limit=tool_spec.limit,
                            search_type=search_type,
                            output_format="structured",
                        ),
                        timeout=tool_spec.timeout_seconds,
                    )

                    # Process results
                    if isinstance(result, dict) and "results" in result:
                        for r in result["results"]:
                            all_results.append({
                                "type": r.get("type", "fact"),
                                "content": r.get("content", ""),
                                "relevance_score": r.get("relevance_score"),
                                "source": r.get("source"),
                                "name": r.get("name", "Unknown"),
                            })
                            # Extract entity names
                            if r.get("name") and r.get("type") == "entity":
                                all_entities.append(r["name"])

                except asyncio.TimeoutError:
                    logger.warning(f"Query timed out: {query[:50]}...")
                    continue
                except Exception as e:
                    logger.warning(f"Query failed: {query[:50]}... - {e}")
                    continue

            execution_time = (datetime.now() - start_time).total_seconds()

            # Calculate quality metrics
            relevance_scores = [
                r["relevance_score"]
                for r in all_results
                if r.get("relevance_score") is not None
            ]
            avg_relevance = (
                sum(relevance_scores) / len(relevance_scores)
                if relevance_scores
                else 0.0
            )

            sources_found = [
                r["source"]["title"]
                for r in all_results
                if r.get("source") and isinstance(r["source"], dict)
            ]

            # Create execution record
            execution = SearchExecution(
                tool_name=tool_spec.tool_name,
                query="; ".join(self.category_config.search_queries[:2]),
                search_type=search_type,
                category=self.category_name,
                success=True,
                execution_time=execution_time,
                results_count=len(all_results),
                relevance_scores=relevance_scores,
                sources_found=list(set(sources_found)),
                entities_found=list(set(all_entities)),
                quality_score=avg_relevance,
                step_description=tool_spec.description,
            )

            # Log completion
            logger.info(
                f"=== TOOL COMPLETE === "
                f"Tool: {tool_spec.tool_name}, "
                f"Results: {len(all_results)}, "
                f"Avg Relevance: {avg_relevance:.2f}, "
                f"Time: {execution_time:.2f}s"
            )

            # Capture tool execution in LangWatch directly for explicit span visibility
            langwatch_config.capture_tool_execution(
                tool_name=tool_spec.tool_name,
                tool_input={
                    "category": self.category_name,
                    "search_type": search_type,
                    "queries_count": len(self.category_config.search_queries),
                    "queries": self.category_config.search_queries[:3],  # First 3 queries for context
                },
                tool_output={
                    "results_count": len(all_results),
                    "avg_relevance": avg_relevance,
                    "entities_found": len(all_entities),
                    "sources_found": len(sources_found),
                },
                execution_time=execution_time,
                success=True,
            )

            # Also capture in AgentTracer if available (for Kodosumi UI updates)
            if self.tracer:
                await self.tracer.capture_tool_execution(
                    tool_name=tool_spec.tool_name,
                    tool_input={
                        "category": self.category_name,
                        "search_type": search_type,
                        "queries_count": len(self.category_config.search_queries),
                    },
                    tool_output={
                        "results_count": len(all_results),
                        "avg_relevance": avg_relevance,
                    },
                    execution_time=execution_time,
                    success=True,
                )

            # Extract findings using LLM (this will be auto-traced by LangChain instrumentation)
            findings = await self._extract_findings(all_results, week_start, week_end)

            return execution, findings, list(set(all_entities))

    async def _extract_findings(
        self,
        results: list[dict[str, Any]],
        week_start: datetime,
        week_end: datetime,
    ) -> list[Finding]:
        """
        Extract structured findings from search results using LLM.

        Args:
            results: Raw search results
            week_start: Week start date
            week_end: Week end date

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

        # Build extraction prompt
        extraction_prompt = f"""Based on the following search results, extract findings for the week of {week_start.strftime('%d %B')} to {week_end.strftime('%d %B %Y')}.

Search Results:
{results_text}

Extract up to 5 relevant findings for the category: {self.display_name}

For each finding, provide:
1. Title (brief headline)
2. Content (2-3 sentences with specific details)
3. Date (if mentioned)
4. Priority (high/medium/low based on significance)
5. Whether it's forward-looking (mentions future dates/deadlines)
6. Source (if mentioned in brackets)
7. Entities (key organizations, laws, or people mentioned)

If no relevant findings, respond with "NO_FINDINGS".

Format each finding as:
FINDING:
Title: [title]
Content: [content]
Date: [date or "Not specified"]
Priority: [high/medium/low]
Forward-looking: [yes/no]
Source: [source or "Not specified"]
Entities: [comma-separated list or "None"]
---
"""

        try:
            messages = [
                SystemMessage(content=self.category_config.system_prompt),
                HumanMessage(content=extraction_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            if "NO_FINDINGS" in response_text:
                return []

            return self._parse_llm_findings(response_text)

        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return self._create_fallback_findings(results)

    def _parse_llm_findings(self, response_text: str) -> list[Finding]:
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
                            category=self.category_name,
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
        self, results: list[dict[str, Any]]
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
                        category=self.category_name,
                        priority=FindingPriority.MEDIUM,
                        source=source,
                    )
                )
        return findings

    def _deduplicate_findings(self, findings: list[Finding]) -> list[Finding]:
        """Remove duplicate findings based on title similarity."""
        seen_titles: set[str] = set()
        unique_findings: list[Finding] = []

        for finding in findings:
            title_key = finding.title.lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_findings.append(finding)

        return unique_findings

    def _rank_findings(self, findings: list[Finding]) -> list[Finding]:
        """Rank findings by priority and relevance."""
        priority_order = {
            FindingPriority.HIGH: 3,
            FindingPriority.MEDIUM: 2,
            FindingPriority.LOW: 1,
        }

        return sorted(
            findings,
            key=lambda f: (
                priority_order.get(f.priority, 2),
                f.forward_looking,
                f.date is not None,
            ),
            reverse=True,
        )

    async def _generate_summary(self, findings: list[Finding]) -> str:
        """Generate a brief summary of findings."""
        if not findings:
            return (
                f"No significant {self.display_name.lower()} "
                "developments found this week."
            )

        high_priority = [f for f in findings if f.priority == FindingPriority.HIGH]
        forward_looking = [f for f in findings if f.forward_looking]

        summary_parts = [
            f"Found {len(findings)} {self.display_name.lower()} developments."
        ]

        if high_priority:
            summary_parts.append(f"{len(high_priority)} high-priority items.")

        if forward_looking:
            summary_parts.append(
                f"{len(forward_looking)} forward-looking items with upcoming dates."
            )

        return " ".join(summary_parts)

    def _build_execution_metadata(
        self, executions: list[SearchExecution]
    ) -> dict[str, Any]:
        """Build aggregated execution metadata for observability."""
        if not executions:
            return {}

        total_time = sum(e.execution_time for e in executions)
        successful = sum(1 for e in executions if e.success)
        failed = sum(1 for e in executions if not e.success)

        # Aggregate relevance scores
        all_relevance: list[float] = []
        for e in executions:
            all_relevance.extend(e.relevance_scores)

        avg_relevance = (
            sum(all_relevance) / len(all_relevance) if all_relevance else 0.0
        )

        # Determine quality tier
        if avg_relevance > 0.5:
            information_quality = "high"
        elif avg_relevance > 0.3:
            information_quality = "medium"
        else:
            information_quality = "low"

        return {
            "total_search_time": round(total_time, 3),
            "searches_successful": successful,
            "searches_failed": failed,
            "total_results": sum(e.results_count for e in executions),
            "avg_relevance_score": round(avg_relevance, 3),
            "information_quality": information_quality,
            "tool_plan_used": self.tool_plan.name,
            "search_details": [e.to_dict() for e in executions],
        }
