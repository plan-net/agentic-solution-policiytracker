"""
Category Research Agents for Weekly Report.

Five specialized agents that query Graphiti for category-specific findings:
- LegislativeResearchAgent: Laws, regulations, directives
- PersonnelResearchAgent: Appointments, personnel changes
- ComplianceResearchAgent: Enforcement, fines, industry compliance
- PolicyResearchAgent: Government initiatives, strategies
- EventsResearchAgent: Upcoming deadlines, events

Implements ToolExecutionAgent-style logging for LangWatch observability.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional

from graphiti_core import Graphiti
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage

from src.chat.observability.langwatch_config import langwatch_config
from src.chat.tools.search import GraphitiSearchTool

from ..models import CategoryResearchResult, Finding, FindingPriority, ReportCategory
from ..prompts.category_prompts import (
    COMPLIANCE_SYSTEM_PROMPT,
    EVENTS_SYSTEM_PROMPT,
    LEGISLATIVE_SYSTEM_PROMPT,
    PERSONNEL_SYSTEM_PROMPT,
    POLICY_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Structured result for search execution tracking (ToolExecutionAgent-style).

    Captures execution metadata for LangWatch observability:
    - Query and search configuration
    - Execution time and success status
    - Result quality metrics (relevance scores, sources found)
    """

    tool_name: str = "graphiti_search"
    query: str = ""
    search_type: str = ""
    category: str = ""
    success: bool = True
    execution_time: float = 0.0
    results_count: int = 0
    output: str = ""
    relevance_scores: list[float] = field(default_factory=list)
    sources_found: list[str] = field(default_factory=list)
    entities_found: list[dict] = field(default_factory=list)
    quality_score: float = 0.0
    error: Optional[str] = None

    def dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


class BaseCategoryResearchAgent(ABC):
    """Base class for category research agents."""

    def __init__(
        self,
        graphiti_client: Graphiti,
        llm: BaseLLM,
        category: ReportCategory,
        system_prompt: str,
    ):
        self.client = graphiti_client
        self.llm = llm
        self.category = category
        self.system_prompt = system_prompt

    @abstractmethod
    def get_search_queries(
        self, week_start: datetime, week_end: datetime
    ) -> list[str]:
        """Generate Graphiti search queries for this category."""
        pass

    @abstractmethod
    def get_entity_types(self) -> list[str]:
        """Return entity types relevant to this category."""
        pass

    @property
    @abstractmethod
    def search_type(self) -> str:
        """Return the optimal search type for this category.

        Available types:
        - 'comprehensive': Cross-encoder reranking (COMBINED_HYBRID_SEARCH_CROSS_ENCODER)
        - 'entity_focused': Node search with RRF (NODE_HYBRID_SEARCH_RRF)
        - 'relationship_focused': Edge search with node distance (EDGE_HYBRID_SEARCH_NODE_DISTANCE)
        - 'episode_focused': Episode mentions (EDGE_HYBRID_SEARCH_EPISODE_MENTIONS)
        - 'rrf_balanced': Balanced RRF search (COMBINED_HYBRID_SEARCH_RRF)
        """
        pass

    @langwatch_config.trace(name="category_research")
    async def research(
        self, week_start: datetime, week_end: datetime
    ) -> CategoryResearchResult:
        """Execute research with execution metadata tracking (ToolExecutionAgent-style).

        Args:
            week_start: Start of the week (Monday)
            week_end: End of the week (Sunday)

        Returns:
            CategoryResearchResult with findings, metadata, and execution_metadata
        """
        start_time = datetime.now()
        findings = []
        errors = []
        search_results_tracking: list[SearchResult] = []  # Track all search executions

        # Log category research start (ToolExecutionAgent pattern)
        logger.info(
            f"=== CATEGORY RESEARCH START === Category: {self.category.value}, "
            f"Search Type: {self.search_type}"
        )

        try:
            # Generate and execute search queries
            queries = self.get_search_queries(week_start, week_end)

            for query in queries:
                try:
                    # Execute Graphiti search with tracking
                    search_results, search_tracking = await self._execute_search(
                        query, week_start, week_end
                    )
                    search_results_tracking.append(search_tracking)

                    if search_results:
                        # Process results with LLM to extract findings
                        category_findings = await self._process_results(
                            search_results, query, week_start, week_end
                        )
                        findings.extend(category_findings)

                except Exception as e:
                    logger.warning(f"Query failed: {query[:50]}... - {e}")
                    errors.append(str(e))

            # Aggregate execution metadata (ToolExecutionAgent pattern)
            execution_metadata = self._build_execution_metadata(search_results_tracking)

            # Deduplicate and rank findings
            findings = self._deduplicate_findings(findings)
            findings = self._rank_findings(findings)

            # Generate summary
            summary = await self._generate_summary(findings)

            execution_time = (datetime.now() - start_time).total_seconds()

            # Log category research completion (ToolExecutionAgent pattern)
            searches_successful = execution_metadata.get("searches_successful", 0)
            total_searches = len(search_results_tracking)
            logger.info(
                f"✅ CATEGORY RESEARCH COMPLETE === Category: {self.category.value}, "
                f"Findings: {len(findings)}, Searches: {total_searches}, "
                f"Success Rate: {searches_successful}/{total_searches}, "
                f"Time: {execution_time:.2f}s"
            )

            return CategoryResearchResult(
                category=self.category,
                findings=findings[:10],  # Top 10 findings
                summary=summary,
                query_used="; ".join(queries[:3]),  # First 3 queries for reference
                execution_time=execution_time,
                success=len(errors) == 0,
                error="; ".join(errors) if errors else None,
                execution_metadata=execution_metadata,  # NEW: structured execution tracking
            )

        except Exception as e:
            logger.error(
                f"❌ CATEGORY RESEARCH FAILED === Category: {self.category.value}: {e}"
            )
            return CategoryResearchResult(
                category=self.category,
                findings=[],
                summary=f"Research failed: {e}",
                execution_time=(datetime.now() - start_time).total_seconds(),
                success=False,
                error=str(e),
                execution_metadata={},
            )

    @langwatch_config.trace(name="graphiti_search")
    async def _execute_search(
        self, query: str, week_start: datetime, week_end: datetime
    ) -> tuple[list[dict[str, Any]], SearchResult]:
        """Execute search with structured result tracking for LangWatch (ToolExecutionAgent-style).

        Returns:
            Tuple of (processed_results, SearchResult) for result tracking and aggregation.
        """
        start_time = datetime.now()

        # Log search start (ToolExecutionAgent pattern)
        logger.info(
            f"=== SEARCH START === Category: {self.category.value}, "
            f"Search Type: {self.search_type}, Query: {query[:50]}..."
        )

        try:
            # Create search tool with the shared Graphiti client
            search_tool = GraphitiSearchTool(graphiti_client=self.client)

            # Build temporal query
            temporal_query = f"{query} {week_start.year}"

            # Use structured output to get relevance scores and sources
            result = await search_tool._arun(
                query=temporal_query,
                limit=20,
                search_type=self.search_type,
                output_format="structured",
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # Process results and extract tracking metrics
            processed_results = []
            relevance_scores = []
            sources_found = []

            if isinstance(result, dict) and "results" in result:
                for r in result["results"]:
                    processed_results.append({
                        "type": r.get("type", "fact"),
                        "content": r.get("content", ""),
                        "relevance_score": r.get("relevance_score"),
                        "source": r.get("source"),
                        "name": r.get("name", "Unknown"),
                    })
                    if r.get("relevance_score"):
                        relevance_scores.append(r["relevance_score"])
                    if r.get("source") and isinstance(r["source"], dict):
                        source_title = r["source"].get("title", "")
                        if source_title:
                            sources_found.append(source_title)

            # Calculate quality score (average relevance)
            avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0

            # Create structured result for tracking (ToolExecutionAgent pattern)
            search_result = SearchResult(
                query=temporal_query,
                search_type=self.search_type,
                category=self.category.value,
                success=True,
                execution_time=execution_time,
                results_count=len(processed_results),
                output=f"Found {len(processed_results)} results",
                relevance_scores=relevance_scores,
                sources_found=sources_found,
                quality_score=avg_relevance,
            )

            # Log search completion (ToolExecutionAgent pattern)
            logger.info(
                f"✅ SEARCH COMPLETE === Category: {self.category.value}, "
                f"Results: {len(processed_results)}, Avg Relevance: {avg_relevance:.2f}, "
                f"Time: {execution_time:.2f}s"
            )

            # Capture tool execution in LangWatch
            langwatch_config.capture_tool_execution(
                tool_name="graphiti_search",
                tool_input={
                    "query": temporal_query,
                    "search_type": self.search_type,
                    "category": self.category.value,
                    "limit": 20,
                },
                tool_output={
                    "results_count": len(processed_results),
                    "avg_relevance": avg_relevance,
                    "sources_found": len(sources_found),
                },
                execution_time=execution_time,
                success=True,
            )

            return processed_results, search_result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log search failure (ToolExecutionAgent pattern)
            logger.error(
                f"❌ SEARCH FAILED === Category: {self.category.value}, "
                f"Error: {e}, Time: {execution_time:.2f}s"
            )

            # Create failure result for tracking
            search_result = SearchResult(
                query=query,
                search_type=self.search_type,
                category=self.category.value,
                success=False,
                execution_time=execution_time,
                error=str(e),
            )

            # Capture failed tool execution in LangWatch
            langwatch_config.capture_tool_execution(
                tool_name="graphiti_search",
                tool_input={
                    "query": query,
                    "search_type": self.search_type,
                    "category": self.category.value,
                    "limit": 20,
                },
                tool_output=None,
                execution_time=execution_time,
                success=False,
                error=str(e),
            )

            return [], search_result

    @langwatch_config.trace(name="llm_extract_findings")
    async def _process_results(
        self,
        results: list[dict[str, Any]],
        query: str,
        week_start: datetime,
        week_end: datetime,
    ) -> list[Finding]:
        """Process search results with LLM to extract structured findings."""
        if not results:
            return []

        # Format results for LLM with relevance scores and sources
        formatted_results = []
        for r in results[:15]:
            # Build result line with available metadata
            line = f"- [{r['type']}]"
            if r.get("relevance_score") is not None:
                line += f" [Relevance: {r['relevance_score']:.2f}]"
            line += f" {r['content'][:200]}"
            if r.get("source") and isinstance(r["source"], dict):
                source_title = r["source"].get("title", "")
                if source_title:
                    line += f" [Source: {source_title}]"
            formatted_results.append(line)

        results_text = "\n".join(formatted_results)

        # Build prompt for LLM
        extraction_prompt = f"""Based on the following search results, extract findings for the week of {week_start.strftime('%d %B')} to {week_end.strftime('%d %B %Y')}.

Search Query: {query}

Results:
{results_text}

Extract up to 5 relevant findings. For each finding, provide:
1. Title (brief headline)
2. Content (2-3 sentences with specific details)
3. Date (if mentioned)
4. Priority (high/medium/low based on significance)
5. Whether it's forward-looking (mentions future dates/deadlines)
6. Source (if mentioned in brackets, extract the source name)

If no relevant findings, respond with "NO_FINDINGS".

Format each finding as:
FINDING:
Title: [title]
Content: [content]
Date: [date or "Not specified"]
Priority: [high/medium/low]
Forward-looking: [yes/no]
Source: [source or "Not specified"]
---
"""

        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=extraction_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)

            if "NO_FINDINGS" in response_text:
                return []

            # Parse findings from response
            return self._parse_llm_findings(response_text)

        except Exception as e:
            logger.warning(f"LLM processing failed: {e}")
            # Fallback: create basic findings from results
            return self._create_basic_findings(results)

    def _parse_llm_findings(self, response_text: str) -> list[Finding]:
        """Parse structured findings from LLM response."""
        findings = []
        finding_blocks = response_text.split("---")

        for block in finding_blocks:
            if "FINDING:" not in block and "Title:" not in block:
                continue

            try:
                lines = block.strip().split("\n")
                finding_data = {}

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

                if finding_data.get("title") and finding_data.get("content"):
                    findings.append(
                        Finding(
                            title=finding_data["title"],
                            content=finding_data["content"],
                            category=self.category,
                            priority=finding_data.get("priority", FindingPriority.MEDIUM),
                            date=finding_data.get("date"),
                            source=finding_data.get("source"),
                            forward_looking=finding_data.get("forward_looking", False),
                        )
                    )

            except Exception as e:
                logger.debug(f"Failed to parse finding block: {e}")
                continue

        return findings

    def _create_basic_findings(self, results: list[dict[str, Any]]) -> list[Finding]:
        """Create basic findings from raw results (fallback)."""
        findings = []
        for result in results[:5]:
            content = result.get("content", "")
            if len(content) > 50:
                # Extract source title if available
                source = None
                source_data = result.get("source")
                if source_data and isinstance(source_data, dict):
                    source = source_data.get("title")

                findings.append(
                    Finding(
                        title=content[:50] + "...",
                        content=content[:200],
                        category=self.category,
                        priority=FindingPriority.MEDIUM,
                        source=source,
                    )
                )
        return findings

    def _deduplicate_findings(self, findings: list[Finding]) -> list[Finding]:
        """Remove duplicate findings based on title similarity."""
        seen_titles = set()
        unique_findings = []

        for finding in findings:
            # Simple deduplication by lowercase title
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
                f.forward_looking,  # Forward-looking items get priority
                f.date is not None,  # Dated items get priority
            ),
            reverse=True,
        )

    async def _generate_summary(self, findings: list[Finding]) -> str:
        """Generate a brief summary of findings."""
        if not findings:
            return f"No significant {self.category.value} developments found this week."

        high_priority = [f for f in findings if f.priority == FindingPriority.HIGH]
        forward_looking = [f for f in findings if f.forward_looking]

        summary_parts = [
            f"Found {len(findings)} {self.category.value} developments."
        ]

        if high_priority:
            summary_parts.append(f"{len(high_priority)} high-priority items.")

        if forward_looking:
            summary_parts.append(f"{len(forward_looking)} forward-looking items with upcoming dates.")

        return " ".join(summary_parts)

    def _build_execution_metadata(
        self, search_results: list[SearchResult]
    ) -> dict[str, Any]:
        """Build aggregated execution metadata (ToolExecutionAgent-style).

        Aggregates metrics from all search executions for observability:
        - Total search time and success rate
        - Result counts and quality scores
        - Detailed per-search breakdown

        Args:
            search_results: List of SearchResult from all executed searches

        Returns:
            Dictionary with aggregated execution metadata
        """
        if not search_results:
            return {}

        total_time = sum(r.execution_time for r in search_results)
        successful = sum(1 for r in search_results if r.success)
        failed = sum(1 for r in search_results if not r.success)

        # Aggregate all relevance scores across searches
        all_relevance: list[float] = []
        for r in search_results:
            all_relevance.extend(r.relevance_scores)

        avg_relevance = sum(all_relevance) / len(all_relevance) if all_relevance else 0.0

        # Determine information quality tier (ToolExecutionAgent pattern)
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
            "total_results": sum(r.results_count for r in search_results),
            "avg_relevance_score": round(avg_relevance, 3),
            "information_quality": information_quality,
            "search_details": [r.dict() for r in search_results],
        }


class LegislativeResearchAgent(BaseCategoryResearchAgent):
    """Agent for researching legislative and regulatory updates."""

    def __init__(self, graphiti_client: Graphiti, llm: BaseLLM):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.LEGISLATIVE,
            system_prompt=LEGISLATIVE_SYSTEM_PROMPT,
        )

    @property
    def search_type(self) -> str:
        """Comprehensive search with cross-encoder reranking for laws/regulations."""
        return "comprehensive"

    def get_search_queries(
        self, week_start: datetime, week_end: datetime
    ) -> list[str]:
        return [
            "new regulation law enacted passed proposed legislation",
            "DSA DMA Digital Services Act Digital Markets Act compliance",
            "GDPR data protection regulation enforcement deadline",
            "AI Act artificial intelligence governance regulation",
            "NIS2 cybersecurity directive implementation",
            "regulatory guidance compliance requirement",
            "platform regulation gatekeeper designation",
        ]

    def get_entity_types(self) -> list[str]:
        return ["REGULATION", "LAW", "DIRECTIVE", "GUIDELINE", "COMPLIANCE_DEADLINE"]


class PersonnelResearchAgent(BaseCategoryResearchAgent):
    """Agent for researching personnel changes."""

    def __init__(self, graphiti_client: Graphiti, llm: BaseLLM):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.PERSONNEL,
            system_prompt=PERSONNEL_SYSTEM_PROMPT,
        )

    @property
    def search_type(self) -> str:
        """Entity-focused search for people and positions."""
        return "entity_focused"

    def get_search_queries(
        self, week_start: datetime, week_end: datetime
    ) -> list[str]:
        return [
            "appointed minister ministry new position",
            "resigned departure leaving position",
            "committee chair member leadership change",
            "regulatory body director appointed",
            "EU Commissioner appointment",
            "parliamentary committee changes",
            "state secretary appointment ministry",
        ]

    def get_entity_types(self) -> list[str]:
        return ["PERSON", "POLITICIAN", "OFFICIAL", "MINISTRY", "COMMITTEE"]


class ComplianceResearchAgent(BaseCategoryResearchAgent):
    """Agent for researching industry and compliance issues."""

    def __init__(self, graphiti_client: Graphiti, llm: BaseLLM):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.COMPLIANCE,
            system_prompt=COMPLIANCE_SYSTEM_PROMPT,
        )

    @property
    def search_type(self) -> str:
        """Relationship-focused search for enforcement actions (company→fine→regulator)."""
        return "relationship_focused"

    def get_search_queries(
        self, week_start: datetime, week_end: datetime
    ) -> list[str]:
        return [
            "fine penalty enforcement action platform",
            "GDPR violation fine million euro",
            "DSA DMA compliance investigation",
            "competition antitrust investigation ruling",
            "platform gatekeeper compliance",
            "data breach notification penalty",
            "content moderation enforcement",
        ]

    def get_entity_types(self) -> list[str]:
        return ["COMPANY", "PLATFORM", "ENFORCEMENT_ACTION", "FINE", "INVESTIGATION"]


class PolicyResearchAgent(BaseCategoryResearchAgent):
    """Agent for researching government policy developments."""

    def __init__(self, graphiti_client: Graphiti, llm: BaseLLM):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.POLICY,
            system_prompt=POLICY_SYSTEM_PROMPT,
        )

    @property
    def search_type(self) -> str:
        """Balanced RRF search for policy (needs both entities and relationships)."""
        return "rrf_balanced"

    def get_search_queries(
        self, week_start: datetime, week_end: datetime
    ) -> list[str]:
        return [
            "ministry policy initiative announcement",
            "digital strategy digitalization government",
            "coalition agreement policy position",
            "e-government digital transformation",
            "federal ministry strategy program",
            "data economy policy framework",
            "infrastructure investment digital",
        ]

    def get_entity_types(self) -> list[str]:
        return ["MINISTRY", "POLICY", "STRATEGY", "INITIATIVE", "GOVERNMENT_AGENCY"]


class EventsResearchAgent(BaseCategoryResearchAgent):
    """Agent for researching upcoming events and deadlines."""

    def __init__(self, graphiti_client: Graphiti, llm: BaseLLM):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.EVENTS,
            system_prompt=EVENTS_SYSTEM_PROMPT,
        )

    @property
    def search_type(self) -> str:
        """Episode-focused search for time-sensitive document-based events."""
        return "episode_focused"

    def get_search_queries(
        self, week_start: datetime, week_end: datetime
    ) -> list[str]:
        return [
            "deadline compliance effective date implementation",
            "public consultation comment period",
            "parliamentary hearing vote scheduled",
            "conference summit event regulatory",
            "court hearing ruling expected date",
            "regulation effective date coming into force",
            "submission deadline registration required",
        ]

    def get_entity_types(self) -> list[str]:
        return ["EVENT", "DEADLINE", "HEARING", "CONSULTATION", "CONFERENCE"]
