"""
Hybrid relevance filter.

Combines fast keyword-based scoring with optional LLM analysis
for borderline cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import structlog

from .keyword_scorer import KeywordScorer, ScoreBreakdown
from .llm_analyzer import LLMAnalyzer, LLMAnalysisResult

logger = structlog.get_logger()


class FilterStrategy(Enum):
    """Available filtering strategies."""

    KEYWORD_ONLY = "keyword_only"
    LLM_ONLY = "llm_only"
    HYBRID = "hybrid"


class FilterDecision(Enum):
    """Possible filter decisions."""

    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"
    UNCERTAIN = "uncertain"


@dataclass
class FilterConfig:
    """Configuration for relevance filtering."""

    # Strategy
    strategy: FilterStrategy = FilterStrategy.HYBRID

    # Keyword filter thresholds
    high_confidence_threshold: float = 70.0  # Above this = definitely relevant
    low_confidence_threshold: float = 5.0  # Below this = definitely not relevant (lowered from 30 for German content)
    min_keyword_matches: int = 1

    # LLM filter settings
    llm_enabled: bool = False
    llm_model: str = "gpt-4o-mini"
    llm_relevance_threshold: float = 50.0
    llm_batch_size: int = 10

    # Behavior
    include_uncertain: bool = True  # Include uncertain content for human review


@dataclass
class FilterResult:
    """Result of relevance filtering."""

    decision: FilterDecision
    stage: str  # "keyword" or "llm"

    # Scores
    keyword_score: Optional[float] = None
    llm_score: Optional[float] = None
    final_score: Optional[float] = None

    # Score details
    score_breakdown: Optional[ScoreBreakdown] = None
    llm_result: Optional[LLMAnalysisResult] = None

    # Matched content
    matched_keywords: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)

    # Explanation
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "decision": self.decision.value,
            "stage": self.stage,
            "keyword_score": self.keyword_score,
            "llm_score": self.llm_score,
            "final_score": self.final_score,
            "matched_keywords": self.matched_keywords,
            "matched_patterns": self.matched_patterns,
            "explanation": self.explanation,
        }


class RelevanceFilter:
    """Hybrid relevance filter with keyword + optional LLM analysis.

    Flow:
    1. Fast keyword scoring on all content
    2. High confidence (>70): Mark as RELEVANT
    3. Low confidence (<30): Mark as NOT_RELEVANT
    4. Uncertain (30-70): Use LLM if enabled, otherwise mark as UNCERTAIN
    """

    def __init__(
        self,
        client_config: dict[str, Any],
        config: Optional[FilterConfig] = None,
        additional_keywords: Optional[list[str]] = None,
    ):
        """Initialize the relevance filter.

        Args:
            client_config: Loaded client.yaml configuration
            config: Filter configuration
            additional_keywords: Extra keywords for relevance matching
        """
        self.config = config or FilterConfig()
        self.client_config = client_config

        # Initialize keyword scorer
        self.keyword_scorer = KeywordScorer(
            client_config=client_config,
            additional_keywords=additional_keywords,
        )

        # Initialize LLM analyzer (if enabled)
        self.llm_analyzer: Optional[LLMAnalyzer] = None
        if self.config.llm_enabled and self.config.strategy != FilterStrategy.KEYWORD_ONLY:
            self.llm_analyzer = LLMAnalyzer(
                model=self.config.llm_model,
                client_config=client_config,
                relevance_threshold=self.config.llm_relevance_threshold,
            )

        logger.info(
            "Initialized RelevanceFilter",
            strategy=self.config.strategy.value,
            llm_enabled=self.config.llm_enabled,
            high_threshold=self.config.high_confidence_threshold,
            low_threshold=self.config.low_confidence_threshold,
        )

    async def filter_content(
        self,
        title: str,
        content: str,
        published_date: Optional[datetime] = None,
    ) -> FilterResult:
        """Filter content for relevance.

        Args:
            title: Article title
            content: Article content/description
            published_date: Optional publication date

        Returns:
            FilterResult with decision and details
        """
        if self.config.strategy == FilterStrategy.LLM_ONLY:
            return await self._filter_llm_only(title, content)

        # Stage 1: Keyword scoring
        breakdown = self.keyword_scorer.score_content(title, content, published_date)
        keyword_score = breakdown.weighted_total

        result = FilterResult(
            decision=FilterDecision.UNCERTAIN,  # Default, will be updated based on score
            stage="keyword",
            keyword_score=keyword_score,
            final_score=keyword_score,
            score_breakdown=breakdown,
            matched_keywords=breakdown.all_matched_keywords,
            matched_patterns=breakdown.matched_patterns,
        )

        # Check for exclusions
        if len(breakdown.matched_exclusions) >= 2:
            result.decision = FilterDecision.NOT_RELEVANT
            result.explanation = f"Excluded due to exclusion terms: {', '.join(breakdown.matched_exclusions)}"
            return result

        # High confidence: definitely relevant
        if keyword_score >= self.config.high_confidence_threshold:
            result.decision = FilterDecision.RELEVANT
            result.explanation = f"High keyword score ({keyword_score:.1f}). Matches: {', '.join(result.matched_keywords[:5])}"
            return result

        # Low confidence: definitely not relevant
        if keyword_score <= self.config.low_confidence_threshold:
            result.decision = FilterDecision.NOT_RELEVANT
            result.explanation = f"Low keyword score ({keyword_score:.1f})"
            return result

        # Uncertain zone (30-70)
        if self.config.strategy == FilterStrategy.HYBRID and self.llm_analyzer and self.llm_analyzer.is_enabled:
            # Use LLM for uncertain cases
            return await self._filter_with_llm(title, content, result)

        # No LLM available - mark as uncertain
        result.decision = FilterDecision.UNCERTAIN
        result.explanation = f"Keyword score ({keyword_score:.1f}) is uncertain. LLM disabled."

        # Optionally include uncertain content
        if self.config.include_uncertain:
            result.decision = FilterDecision.RELEVANT
            result.explanation += " Including due to include_uncertain=True."

        return result

    async def _filter_llm_only(self, title: str, content: str) -> FilterResult:
        """Filter using only LLM analysis.

        Args:
            title: Article title
            content: Article content

        Returns:
            FilterResult
        """
        if not self.llm_analyzer or not self.llm_analyzer.is_enabled:
            return FilterResult(
                decision=FilterDecision.UNCERTAIN,
                stage="llm",
                explanation="LLM analysis not available",
            )

        llm_result = await self.llm_analyzer.analyze(title, content)

        return FilterResult(
            decision=FilterDecision.RELEVANT if llm_result.is_relevant else FilterDecision.NOT_RELEVANT,
            stage="llm",
            llm_score=llm_result.score,
            final_score=llm_result.score,
            llm_result=llm_result,
            explanation=llm_result.explanation,
        )

    async def _filter_with_llm(
        self,
        title: str,
        content: str,
        keyword_result: FilterResult,
    ) -> FilterResult:
        """Enhance keyword result with LLM analysis.

        Args:
            title: Article title
            content: Article content
            keyword_result: Initial keyword scoring result

        Returns:
            Enhanced FilterResult
        """
        if not self.llm_analyzer:
            return keyword_result

        llm_result = await self.llm_analyzer.analyze(title, content)

        # Update result with LLM data
        keyword_result.stage = "llm"
        keyword_result.llm_score = llm_result.score
        keyword_result.llm_result = llm_result

        # Combine scores (weighted average)
        keyword_weight = 0.6
        llm_weight = 0.4
        keyword_result.final_score = (
            (keyword_result.keyword_score or 0) * keyword_weight
            + llm_result.score * llm_weight
        )

        # Make decision based on LLM confidence
        if llm_result.confidence >= 0.7:
            # High LLM confidence - trust LLM
            keyword_result.decision = (
                FilterDecision.RELEVANT if llm_result.is_relevant else FilterDecision.NOT_RELEVANT
            )
            keyword_result.explanation = f"LLM (confidence {llm_result.confidence:.2f}): {llm_result.explanation}"
        else:
            # Low LLM confidence - use combined score
            if keyword_result.final_score >= 50:
                keyword_result.decision = FilterDecision.RELEVANT
            else:
                keyword_result.decision = FilterDecision.NOT_RELEVANT
            keyword_result.explanation = (
                f"Combined score {keyword_result.final_score:.1f} "
                f"(keyword: {keyword_result.keyword_score:.1f}, LLM: {llm_result.score:.1f})"
            )

        return keyword_result

    async def filter_batch(
        self,
        articles: list[tuple[str, str, Optional[datetime]]],  # (title, content, date)
    ) -> list[FilterResult]:
        """Filter a batch of articles.

        Args:
            articles: List of (title, content, published_date) tuples

        Returns:
            List of FilterResult for each article
        """
        results = []

        for title, content, published_date in articles:
            result = await self.filter_content(title, content, published_date)
            results.append(result)

        # Log summary
        relevant = sum(1 for r in results if r.decision == FilterDecision.RELEVANT)
        not_relevant = sum(1 for r in results if r.decision == FilterDecision.NOT_RELEVANT)
        uncertain = sum(1 for r in results if r.decision == FilterDecision.UNCERTAIN)

        logger.info(
            "Batch filtering complete",
            total=len(articles),
            relevant=relevant,
            not_relevant=not_relevant,
            uncertain=uncertain,
        )

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get filter statistics."""
        return {
            "strategy": self.config.strategy.value,
            "llm_enabled": self.config.llm_enabled,
            "thresholds": {
                "high": self.config.high_confidence_threshold,
                "low": self.config.low_confidence_threshold,
            },
        }


def create_filter_from_config(
    client_config: dict[str, Any],
    filter_config: dict[str, Any],
) -> RelevanceFilter:
    """Create a RelevanceFilter from configuration dictionaries.

    Args:
        client_config: Loaded client.yaml
        filter_config: Filter configuration from websites.yaml

    Returns:
        Configured RelevanceFilter
    """
    # Parse strategy
    strategy_str = filter_config.get("strategy", "hybrid")
    strategy = FilterStrategy(strategy_str)

    # Build FilterConfig
    keyword_config = filter_config.get("keyword_filter", {})
    llm_config = filter_config.get("llm_filter", {})

    config = FilterConfig(
        strategy=strategy,
        high_confidence_threshold=keyword_config.get("high_confidence_threshold", 70.0),
        low_confidence_threshold=keyword_config.get("low_confidence_threshold", 5.0),
        min_keyword_matches=keyword_config.get("min_keyword_matches", 1),
        llm_enabled=llm_config.get("enabled", False),
        llm_model=llm_config.get("model", "gpt-4o-mini"),
        llm_relevance_threshold=llm_config.get("relevance_threshold", 50.0),
        llm_batch_size=llm_config.get("batch_size", 10),
    )

    # Additional keywords from config
    additional_keywords = keyword_config.get("additional_keywords", [])

    return RelevanceFilter(
        client_config=client_config,
        config=config,
        additional_keywords=additional_keywords,
    )
