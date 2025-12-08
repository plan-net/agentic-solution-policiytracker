"""
Base Category Researcher for Report Generation.

Provides an abstract base class for category-specific research agents
that query the knowledge graph and extract findings.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from graphiti_core import Graphiti
    from langchain_core.language_models import BaseLLM

    from src.core.config.category_config import CategoryConfig
    from src.core.config.tool_plan_config import ToolPlanConfig
    from src.core.observability.tracer import AgentTracer


@dataclass
class SearchResult:
    """
    Structured result for search execution tracking.

    Captures execution metadata for observability:
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_name": self.tool_name,
            "query": self.query,
            "search_type": self.search_type,
            "category": self.category,
            "success": self.success,
            "execution_time": self.execution_time,
            "results_count": self.results_count,
            "output": self.output,
            "relevance_scores": self.relevance_scores,
            "sources_found": self.sources_found,
            "entities_found": self.entities_found,
            "quality_score": self.quality_score,
            "error": self.error,
        }

    @property
    def average_relevance(self) -> float:
        """Calculate average relevance score."""
        if not self.relevance_scores:
            return 0.0
        return sum(self.relevance_scores) / len(self.relevance_scores)


class BaseCategoryResearcher(ABC):
    """
    Abstract base class for category-specific research agents.

    Category researchers are responsible for:
    - Executing configured search queries against the knowledge graph
    - Processing raw results with LLM to extract structured findings
    - Ranking and deduplicating findings
    - Generating category summaries

    Subclasses can customize:
    - Search execution strategy via tool plans
    - Result processing and finding extraction
    - Ranking criteria
    - Summary generation

    Example:
        class LegislativeResearcher(BaseCategoryResearcher):
            async def research(self, week_start, week_end):
                # Custom implementation
                pass
    """

    def __init__(
        self,
        category_config: "CategoryConfig",
        tool_plan: "ToolPlanConfig",
        graphiti_client: "Graphiti",
        llm: "BaseLLM",
        tracer: "AgentTracer",
    ):
        """
        Initialize the category researcher.

        Args:
            category_config: Configuration for this research category
            tool_plan: Tool execution plan configuration
            graphiti_client: Graphiti client for knowledge graph queries
            llm: Language model for result processing
            tracer: Unified tracer for observability
        """
        self.config = category_config
        self.tool_plan = tool_plan
        self.client = graphiti_client
        self.llm = llm
        self.tracer = tracer

    @abstractmethod
    async def research(
        self,
        week_start: datetime,
        week_end: datetime,
    ) -> "CategoryResearchResult":
        """
        Execute research for this category.

        Implementations should:
        1. Execute searches according to the tool plan
        2. Process results to extract findings
        3. Deduplicate and rank findings
        4. Generate a category summary

        Args:
            week_start: Start of the reporting period
            week_end: End of the reporting period

        Returns:
            CategoryResearchResult with findings and metadata
        """
        pass

    @abstractmethod
    async def _execute_search(
        self,
        query: str,
        search_type: str,
        limit: int,
        week_start: datetime,
        week_end: datetime,
    ) -> tuple[list[dict[str, Any]], SearchResult]:
        """
        Execute a single search query.

        Args:
            query: Search query string
            search_type: Type of search (comprehensive, entity_focused, etc.)
            limit: Maximum results to return
            week_start: Start of the reporting period
            week_end: End of the reporting period

        Returns:
            Tuple of (processed_results, SearchResult for tracking)
        """
        pass

    @abstractmethod
    async def _process_results(
        self,
        results: list[dict[str, Any]],
        query: str,
        week_start: datetime,
        week_end: datetime,
    ) -> list["Finding"]:
        """
        Process search results with LLM to extract findings.

        Args:
            results: Raw search results
            query: Original search query
            week_start: Start of the reporting period
            week_end: End of the reporting period

        Returns:
            List of extracted Finding objects
        """
        pass

    def _deduplicate_findings(self, findings: list["Finding"]) -> list["Finding"]:
        """
        Remove duplicate findings based on title similarity.

        Default implementation uses case-insensitive title matching.
        Subclasses can override for more sophisticated deduplication.

        Args:
            findings: List of findings to deduplicate

        Returns:
            Deduplicated list of findings
        """
        seen_titles: set[str] = set()
        unique_findings: list["Finding"] = []

        for finding in findings:
            title_key = finding.title.lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_findings.append(finding)

        return unique_findings

    def _rank_findings(self, findings: list["Finding"]) -> list["Finding"]:
        """
        Rank findings by priority and relevance.

        Default ranking prioritizes:
        1. High priority findings
        2. Forward-looking items
        3. Dated items

        Subclasses can override for custom ranking logic.

        Args:
            findings: List of findings to rank

        Returns:
            Sorted list of findings
        """
        from src.flows.weekly_digest_v2.models import FindingPriority

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

    async def _generate_summary(self, findings: list["Finding"]) -> str:
        """
        Generate a brief summary of findings.

        Default implementation creates a simple count-based summary.
        Subclasses can override for LLM-generated summaries.

        Args:
            findings: List of findings to summarize

        Returns:
            Summary string
        """
        from src.flows.weekly_digest_v2.models import FindingPriority

        if not findings:
            return f"No significant {self.config.display_name} developments found this week."

        high_priority = [f for f in findings if f.priority == FindingPriority.HIGH]
        forward_looking = [f for f in findings if f.forward_looking]

        summary_parts = [
            f"Found {len(findings)} {self.config.display_name} developments."
        ]

        if high_priority:
            summary_parts.append(f"{len(high_priority)} high-priority items.")

        if forward_looking:
            summary_parts.append(
                f"{len(forward_looking)} forward-looking items with upcoming dates."
            )

        return " ".join(summary_parts)

    def _build_execution_metadata(
        self,
        search_results: list[SearchResult],
    ) -> dict[str, Any]:
        """
        Build aggregated execution metadata from search results.

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

        avg_relevance = (
            sum(all_relevance) / len(all_relevance) if all_relevance else 0.0
        )

        # Determine information quality tier
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
            "search_details": [r.to_dict() for r in search_results],
        }


# Import for type hints - will be defined in weekly_digest_v2
# Using forward reference to avoid circular imports
Finding = Any  # Will be properly typed when models.py is created
CategoryResearchResult = Any  # Will be properly typed when models.py is created
