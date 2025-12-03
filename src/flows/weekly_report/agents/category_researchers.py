"""
Category Research Agents for Weekly Report.

Five specialized agents that query Graphiti for category-specific findings:
- LegislativeResearchAgent: Laws, regulations, directives
- PersonnelResearchAgent: Appointments, personnel changes
- ComplianceResearchAgent: Enforcement, fines, industry compliance
- PolicyResearchAgent: Government initiatives, strategies
- EventsResearchAgent: Upcoming deadlines, events
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from graphiti_core import Graphiti
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage

from ..models import CategoryResearchResult, Finding, FindingPriority, ReportCategory
from ..prompts.category_prompts import (
    COMPLIANCE_SYSTEM_PROMPT,
    EVENTS_SYSTEM_PROMPT,
    LEGISLATIVE_SYSTEM_PROMPT,
    PERSONNEL_SYSTEM_PROMPT,
    POLICY_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


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

    async def research(
        self, week_start: datetime, week_end: datetime
    ) -> CategoryResearchResult:
        """
        Execute research for this category.

        Args:
            week_start: Start of the week (Monday)
            week_end: End of the week (Sunday)

        Returns:
            CategoryResearchResult with findings and metadata
        """
        start_time = datetime.now()
        findings = []
        errors = []

        try:
            # Generate and execute search queries
            queries = self.get_search_queries(week_start, week_end)

            for query in queries:
                try:
                    # Execute Graphiti search
                    search_results = await self._execute_search(query, week_start, week_end)

                    if search_results:
                        # Process results with LLM to extract findings
                        category_findings = await self._process_results(
                            search_results, query, week_start, week_end
                        )
                        findings.extend(category_findings)

                except Exception as e:
                    logger.warning(f"Query failed: {query[:50]}... - {e}")
                    errors.append(str(e))

            # Deduplicate and rank findings
            findings = self._deduplicate_findings(findings)
            findings = self._rank_findings(findings)

            # Generate summary
            summary = await self._generate_summary(findings)

            execution_time = (datetime.now() - start_time).total_seconds()

            return CategoryResearchResult(
                category=self.category,
                findings=findings[:10],  # Top 10 findings
                summary=summary,
                query_used="; ".join(queries[:3]),  # First 3 queries for reference
                execution_time=execution_time,
                success=len(errors) == 0,
                error="; ".join(errors) if errors else None,
            )

        except Exception as e:
            logger.error(f"Category research failed for {self.category}: {e}")
            return CategoryResearchResult(
                category=self.category,
                findings=[],
                summary=f"Research failed: {e}",
                execution_time=(datetime.now() - start_time).total_seconds(),
                success=False,
                error=str(e),
            )

    async def _execute_search(
        self, query: str, week_start: datetime, week_end: datetime
    ) -> list[dict[str, Any]]:
        """Execute a Graphiti search query."""
        try:
            from graphiti_core.search.search_config_recipes import (
                EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
            )

            # Build temporal query
            temporal_query = f"{query} {week_start.year}"

            search_results = await self.client._search(
                query=temporal_query,
                config=EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
            )

            # Extract results
            results = []
            if hasattr(search_results, "edges") and search_results.edges:
                for edge in search_results.edges[:20]:
                    if hasattr(edge, "fact") and edge.fact:
                        results.append({
                            "type": "fact",
                            "content": edge.fact,
                            "episodes": getattr(edge, "episodes", []),
                        })

            if hasattr(search_results, "nodes") and search_results.nodes:
                for node in search_results.nodes[:20]:
                    if hasattr(node, "summary") and node.summary:
                        results.append({
                            "type": "entity",
                            "content": node.summary,
                            "name": getattr(node, "name", "Unknown"),
                        })

            return results

        except Exception as e:
            logger.error(f"Graphiti search failed: {e}")
            return []

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

        # Format results for LLM
        results_text = "\n".join([
            f"- [{r['type']}] {r['content'][:200]}" for r in results[:15]
        ])

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

If no relevant findings, respond with "NO_FINDINGS".

Format each finding as:
FINDING:
Title: [title]
Content: [content]
Date: [date or "Not specified"]
Priority: [high/medium/low]
Forward-looking: [yes/no]
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

                if finding_data.get("title") and finding_data.get("content"):
                    findings.append(
                        Finding(
                            title=finding_data["title"],
                            content=finding_data["content"],
                            category=self.category,
                            priority=finding_data.get("priority", FindingPriority.MEDIUM),
                            date=finding_data.get("date"),
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
                findings.append(
                    Finding(
                        title=content[:50] + "...",
                        content=content[:200],
                        category=self.category,
                        priority=FindingPriority.MEDIUM,
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


class LegislativeResearchAgent(BaseCategoryResearchAgent):
    """Agent for researching legislative and regulatory updates."""

    def __init__(self, graphiti_client: Graphiti, llm: BaseLLM):
        super().__init__(
            graphiti_client=graphiti_client,
            llm=llm,
            category=ReportCategory.LEGISLATIVE,
            system_prompt=LEGISLATIVE_SYSTEM_PROMPT,
        )

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
