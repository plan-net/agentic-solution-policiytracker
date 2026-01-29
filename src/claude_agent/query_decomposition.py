"""Query Decomposition Module

Analyzes complex queries and breaks them into manageable sub-questions.
Helps prevent agents from hitting max_turns limits by handling queries step-by-step.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"           # 1-5 turns expected
    MODERATE = "moderate"       # 6-12 turns expected
    COMPLEX = "complex"         # 13-20 turns expected
    VERY_COMPLEX = "very_complex"  # 21+ turns expected


@dataclass
class QueryAnalysis:
    """Result of query complexity analysis."""
    complexity: QueryComplexity
    estimated_turns: int
    requires_decomposition: bool
    reasoning: str
    entity_count: int
    domain_count: int
    temporal_constraints: bool
    synthesis_required: bool


@dataclass
class SubQuery:
    """A decomposed sub-question."""
    question: str
    order: int
    depends_on: Optional[List[int]] = None  # Which sub-queries must complete first
    priority: str = "normal"  # "high", "normal", "low"
    reasoning: str = ""


@dataclass
class DecompositionResult:
    """Result of query decomposition."""
    should_decompose: bool
    original_query: str
    sub_queries: List[SubQuery]
    strategy: str  # "sequential", "parallel", "hybrid"
    reasoning: str


class QueryDecomposer:
    """Analyzes and decomposes complex queries into manageable sub-questions."""

    def __init__(self, complexity_threshold: int = 20):
        """
        Initialize query decomposer.

        Args:
            complexity_threshold: Estimated turn count above which to suggest decomposition
        """
        self.complexity_threshold = complexity_threshold
        self.multi_domain_keywords = {
            "and", "also", "additionally", "furthermore", "moreover",
            "sowie", "und", "außerdem", "zusätzlich", "darüber hinaus"
        }

    def analyze_complexity(self, query: str) -> QueryAnalysis:
        """
        Analyze query complexity and estimate required turns.

        Args:
            query: User's query string

        Returns:
            QueryAnalysis with complexity assessment
        """
        # Entity detection (simple heuristic: capitalized words, known entity patterns)
        words = query.split()
        entities = self._extract_entities(query)
        entity_count = len(entities)

        # Domain detection
        domains = self._detect_domains(query)
        domain_count = len(domains)

        # Temporal constraints
        temporal_constraints = self._has_temporal_constraints(query)

        # Synthesis requirements
        synthesis_required = self._requires_synthesis(query)

        # Estimate turns
        estimated_turns = self._estimate_turns(
            entity_count=entity_count,
            domain_count=domain_count,
            temporal_constraints=temporal_constraints,
            synthesis_required=synthesis_required,
            query_length=len(query)
        )

        # Determine complexity level
        if estimated_turns <= 5:
            complexity = QueryComplexity.SIMPLE
        elif estimated_turns <= 12:
            complexity = QueryComplexity.MODERATE
        elif estimated_turns <= 20:
            complexity = QueryComplexity.COMPLEX
        else:
            complexity = QueryComplexity.VERY_COMPLEX

        # Should decompose?
        requires_decomposition = estimated_turns > self.complexity_threshold

        # Build reasoning
        reasoning = self._build_reasoning(
            entity_count, domain_count, temporal_constraints,
            synthesis_required, estimated_turns
        )

        return QueryAnalysis(
            complexity=complexity,
            estimated_turns=estimated_turns,
            requires_decomposition=requires_decomposition,
            reasoning=reasoning,
            entity_count=entity_count,
            domain_count=domain_count,
            temporal_constraints=temporal_constraints,
            synthesis_required=synthesis_required
        )

    def decompose_query(self, query: str) -> DecompositionResult:
        """
        Decompose a complex query into manageable sub-queries.

        Args:
            query: User's complex query

        Returns:
            DecompositionResult with sub-queries and execution strategy
        """
        # First analyze complexity
        analysis = self.analyze_complexity(query)

        if not analysis.requires_decomposition:
            return DecompositionResult(
                should_decompose=False,
                original_query=query,
                sub_queries=[],
                strategy="direct",
                reasoning="Query is simple enough to handle directly"
            )

        # Detect query type and decompose accordingly
        sub_queries = self._decompose_by_pattern(query, analysis)

        # Determine execution strategy
        strategy = self._determine_strategy(sub_queries, analysis)

        return DecompositionResult(
            should_decompose=True,
            original_query=query,
            sub_queries=sub_queries,
            strategy=strategy,
            reasoning=f"Query requires {analysis.estimated_turns} turns. "
                     f"Breaking into {len(sub_queries)} sub-queries will be more efficient."
        )

    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query (simple heuristic)."""
        # Common tech companies
        tech_companies = [
            "Meta", "Google", "Amazon", "Apple", "Microsoft", "Facebook",
            "Instagram", "WhatsApp", "Twitter", "X", "TikTok", "YouTube",
            "Netflix", "Tesla", "Samsung"
        ]

        # Look for capitalized words and known entities
        entities = []
        words = query.split()

        for word in words:
            # Check tech companies
            if any(company.lower() in word.lower() for company in tech_companies):
                entities.append(word)
            # Check if capitalized (and not at start of sentence)
            elif word[0].isupper() and len(word) > 1:
                entities.append(word)

        # Look for specific patterns
        if "DSA" in query or "Digital Services Act" in query:
            entities.append("Digital Services Act")
        if "GDPR" in query or "Datenschutz" in query:
            entities.append("GDPR")
        if "AI Act" in query or "KI-Verordnung" in query:
            entities.append("AI Act")

        return list(set(entities))

    def _detect_domains(self, query: str) -> List[str]:
        """Detect which knowledge domains the query spans."""
        domains = []

        domain_keywords = {
            "legislation": ["gesetz", "verordnung", "richtlinie", "act", "regulation", "law", "legislation"],
            "bundestag": ["bundestag", "parlament", "abgeordnete", "fraktion", "parliamentary"],
            "technology": ["tech", "digital", "platform", "online", "software", "ai", "ki"],
            "policy": ["politik", "policy", "strategie", "initiative", "reform"],
            "economy": ["wirtschaft", "market", "markt", "unternehmen", "companies"],
            "news": ["aktuell", "news", "recent", "latest", "neueste"],
        }

        query_lower = query.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                domains.append(domain)

        return domains

    def _has_temporal_constraints(self, query: str) -> bool:
        """Check if query has time-based requirements."""
        temporal_keywords = [
            "aktuell", "recent", "latest", "neueste", "letzte",
            "2024", "2025", "2026", "year", "jahr", "month", "monat",
            "today", "heute", "last week", "letzte woche"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in temporal_keywords)

    def _requires_synthesis(self, query: str) -> bool:
        """Check if query requires synthesizing multiple sources."""
        synthesis_keywords = [
            "compare", "vergleich", "relationship", "beziehung", "connection",
            "zusammenhang", "impact", "auswirkung", "influence", "einfluss",
            "versus", "vs", "difference", "unterschied"
        ]

        # Also check for multiple entities or domains
        query_lower = query.lower()
        has_synthesis_keywords = any(keyword in query_lower for keyword in synthesis_keywords)
        has_connectors = any(keyword in query_lower for keyword in self.multi_domain_keywords)

        return has_synthesis_keywords or has_connectors

    def _estimate_turns(
        self,
        entity_count: int,
        domain_count: int,
        temporal_constraints: bool,
        synthesis_required: bool,
        query_length: int
    ) -> int:
        """Estimate number of turns needed for query."""
        base_turns = 3  # Minimum for any query

        # Add turns for entities
        entity_turns = min(entity_count * 2, 10)  # Max 10 turns for entities

        # Add turns for domains
        domain_turns = domain_count * 3  # Each domain needs ~3 turns

        # Add turns for temporal filtering
        temporal_turns = 3 if temporal_constraints else 0

        # Add turns for synthesis
        synthesis_turns = 5 if synthesis_required else 0

        # Add turns for query complexity (based on length)
        if query_length > 150:
            complexity_turns = 5
        elif query_length > 80:
            complexity_turns = 3
        else:
            complexity_turns = 0

        total = base_turns + entity_turns + domain_turns + temporal_turns + synthesis_turns + complexity_turns

        return min(total, 40)  # Cap at 40

    def _build_reasoning(
        self,
        entity_count: int,
        domain_count: int,
        temporal_constraints: bool,
        synthesis_required: bool,
        estimated_turns: int
    ) -> str:
        """Build human-readable reasoning for complexity assessment."""
        factors = []

        if entity_count > 3:
            factors.append(f"{entity_count} entities to research")
        if domain_count > 2:
            factors.append(f"{domain_count} knowledge domains")
        if temporal_constraints:
            factors.append("temporal filtering required")
        if synthesis_required:
            factors.append("synthesis across sources needed")

        if not factors:
            return f"Simple query, estimated {estimated_turns} turns"

        return f"Complex query with {', '.join(factors)}. Estimated {estimated_turns} turns."

    def _decompose_by_pattern(self, query: str, analysis: QueryAnalysis) -> List[SubQuery]:
        """Decompose query based on detected patterns."""
        sub_queries = []

        # Pattern 1: Multi-entity query
        # Example: "DSA impact on Meta Google Amazon"
        if analysis.entity_count > 2:
            entities = self._extract_entities(query)
            domains = self._detect_domains(query)

            # Extract core question
            core_topic = self._extract_core_topic(query)

            # Create foundational question
            sub_queries.append(SubQuery(
                question=f"What is {core_topic}?",
                order=1,
                priority="high",
                reasoning="Establish foundational understanding"
            ))

            # Create entity-specific questions
            for i, entity in enumerate(entities[:5]):  # Limit to 5 entities
                sub_queries.append(SubQuery(
                    question=f"How does {core_topic} relate to {entity}?",
                    order=2 + i,
                    depends_on=[1],
                    priority="normal",
                    reasoning=f"Understand {entity}-specific aspects"
                ))

        # Pattern 2: Multi-domain query
        # Example: "DSA legislation bundestag news"
        elif analysis.domain_count > 2:
            domains = self._detect_domains(query)
            core_topic = self._extract_core_topic(query)

            # Foundational question
            sub_queries.append(SubQuery(
                question=f"What is {core_topic}?",
                order=1,
                priority="high",
                reasoning="Establish context"
            ))

            # Domain-specific questions
            domain_questions = {
                "legislation": f"What legislation exists regarding {core_topic}?",
                "bundestag": f"What parliamentary proceedings exist in Bundestag about {core_topic}?",
                "news": f"What are the latest news about {core_topic}?",
                "policy": f"What policies have been implemented regarding {core_topic}?",
                "economy": f"What is the economic impact of {core_topic}?",
            }

            for i, domain in enumerate(domains):
                if domain in domain_questions:
                    sub_queries.append(SubQuery(
                        question=domain_questions[domain],
                        order=2 + i,
                        depends_on=[1],
                        priority="normal",
                        reasoning=f"Cover {domain} domain"
                    ))

        # Pattern 3: Comparison query
        # Example: "Compare DSA and GDPR"
        elif "compare" in query.lower() or "vergleich" in query.lower():
            # Extract entities to compare
            entities = self._extract_entities(query)
            if len(entities) >= 2:
                sub_queries.append(SubQuery(
                    question=f"What is {entities[0]}?",
                    order=1,
                    priority="high",
                    reasoning=f"Understand {entities[0]}"
                ))
                sub_queries.append(SubQuery(
                    question=f"What is {entities[1]}?",
                    order=2,
                    priority="high",
                    reasoning=f"Understand {entities[1]}"
                ))
                sub_queries.append(SubQuery(
                    question=f"What are the similarities and differences between {entities[0]} and {entities[1]}?",
                    order=3,
                    depends_on=[1, 2],
                    priority="high",
                    reasoning="Synthesize comparison"
                ))

        # Pattern 4: Temporal + synthesis query
        # Example: "Recent impact of DSA on tech companies"
        elif analysis.temporal_constraints and analysis.synthesis_required:
            core_topic = self._extract_core_topic(query)
            entities = self._extract_entities(query)

            sub_queries.append(SubQuery(
                question=f"What is {core_topic}?",
                order=1,
                priority="high",
                reasoning="Establish context"
            ))
            sub_queries.append(SubQuery(
                question=f"What are the recent developments regarding {core_topic}?",
                order=2,
                depends_on=[1],
                priority="normal",
                reasoning="Get current information"
            ))
            if entities:
                sub_queries.append(SubQuery(
                    question=f"How have {', '.join(entities[:3])} been affected by {core_topic}?",
                    order=3,
                    depends_on=[1, 2],
                    priority="normal",
                    reasoning="Analyze specific impacts"
                ))

        # Default fallback: Break by sentence or logical parts
        if not sub_queries:
            sub_queries = self._decompose_by_structure(query)

        return sub_queries

    def _extract_core_topic(self, query: str) -> str:
        """Extract the main topic from the query."""
        # Look for known topics
        known_topics = [
            "Digital Services Act", "DSA",
            "GDPR", "Datenschutz-Grundverordnung",
            "AI Act", "KI-Verordnung",
            "Data Act", "Daten-Governance"
        ]

        query_upper = query.upper()
        for topic in known_topics:
            if topic.upper() in query_upper:
                return topic

        # Fallback: Use first few significant words
        words = [w for w in query.split() if len(w) > 3]
        return " ".join(words[:3]) if words else "the topic"

    def _decompose_by_structure(self, query: str) -> List[SubQuery]:
        """Decompose query by structural elements (sentences, clauses)."""
        # Split by common separators
        parts = []
        for sep in [" and ", " und ", ", ", "; "]:
            if sep in query:
                parts = query.split(sep)
                break

        if not parts or len(parts) < 2:
            # Can't decompose structurally, create generic breakdown
            return [
                SubQuery(
                    question=f"Please provide an overview: {query}",
                    order=1,
                    priority="high",
                    reasoning="Get comprehensive overview"
                )
            ]

        # Create sub-queries from parts
        sub_queries = []
        for i, part in enumerate(parts[:4]):  # Limit to 4 parts
            sub_queries.append(SubQuery(
                question=part.strip() + ("?" if not part.strip().endswith("?") else ""),
                order=i + 1,
                priority="normal" if i > 0 else "high",
                reasoning=f"Address part {i + 1} of query"
            ))

        return sub_queries

    def _determine_strategy(self, sub_queries: List[SubQuery], analysis: QueryAnalysis) -> str:
        """Determine execution strategy for sub-queries."""
        # Check if any sub-queries have dependencies
        has_dependencies = any(sq.depends_on for sq in sub_queries)

        if not has_dependencies:
            return "parallel"  # All can be executed in parallel

        # Check if all depend on first question (common pattern)
        all_depend_on_first = all(
            sq.depends_on == [1] if sq.depends_on else True
            for sq in sub_queries[1:]
        )

        if all_depend_on_first:
            return "hybrid"  # Execute first, then rest in parallel

        return "sequential"  # Must execute in order

    def format_decomposition_message(self, result: DecompositionResult) -> str:
        """Format a user-friendly message explaining the decomposition."""
        if not result.should_decompose:
            return ""

        message = (
            f"This is a complex query that I can answer more effectively by breaking it down. "
            f"I've identified {len(result.sub_queries)} key questions:\n\n"
        )

        for sq in result.sub_queries:
            priority_emoji = "🔴" if sq.priority == "high" else "🟡" if sq.priority == "normal" else "🟢"
            message += f"{priority_emoji} **{sq.order}.** {sq.question}\n"

        strategy_text = {
            "sequential": "I'll answer these questions one at a time in order.",
            "parallel": "I can research these questions simultaneously.",
            "hybrid": "I'll answer the first question, then research the rest in parallel."
        }

        message += f"\n{strategy_text.get(result.strategy, 'I will process these systematically.')}\n"
        message += "\nWould you like me to proceed with this breakdown, or would you prefer a different approach?"

        return message
