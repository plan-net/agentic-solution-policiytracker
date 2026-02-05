"""
Keyword-based relevance scorer.

Fast, rule-based scoring using keywords from client.yaml.
Scores content across multiple dimensions:
- Direct Impact (40%)
- Industry Relevance (25%)
- Geographic Relevance (15%)
- Temporal Urgency (10%)
- Strategic Alignment (10%)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import structlog

from ..utils.schema_helpers import (
    extract_company_terms,
    extract_exclusion_terms,
    extract_industries,
    extract_legislative_terms,
    extract_markets,
    extract_regulatory_actors,
)

logger = structlog.get_logger()


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of scoring across dimensions."""

    # Individual dimension scores (0-100)
    direct_impact: float = 0.0
    industry_relevance: float = 0.0
    geographic_relevance: float = 0.0
    temporal_urgency: float = 0.0
    strategic_alignment: float = 0.0

    # Matched terms per dimension
    matched_direct_impact: list[str] = field(default_factory=list)
    matched_industries: list[str] = field(default_factory=list)
    matched_markets: list[str] = field(default_factory=list)
    matched_temporal: list[str] = field(default_factory=list)
    matched_themes: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)

    # Exclusion matches
    matched_exclusions: list[str] = field(default_factory=list)

    # Weights
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "direct_impact": 0.40,
            "industry_relevance": 0.25,
            "geographic_relevance": 0.15,
            "temporal_urgency": 0.10,
            "strategic_alignment": 0.10,
        }
    )

    @property
    def weighted_total(self) -> float:
        """Calculate weighted total score (0-100)."""
        total = (
            self.direct_impact * self.weights["direct_impact"]
            + self.industry_relevance * self.weights["industry_relevance"]
            + self.geographic_relevance * self.weights["geographic_relevance"]
            + self.temporal_urgency * self.weights["temporal_urgency"]
            + self.strategic_alignment * self.weights["strategic_alignment"]
        )
        return round(total, 2)

    @property
    def all_matched_keywords(self) -> list[str]:
        """Get all matched keywords across dimensions."""
        return (
            self.matched_direct_impact
            + self.matched_industries
            + self.matched_markets
            + self.matched_themes
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "weighted_total": self.weighted_total,
            "dimensions": {
                "direct_impact": self.direct_impact,
                "industry_relevance": self.industry_relevance,
                "geographic_relevance": self.geographic_relevance,
                "temporal_urgency": self.temporal_urgency,
                "strategic_alignment": self.strategic_alignment,
            },
            "matches": {
                "direct_impact": self.matched_direct_impact,
                "industries": self.matched_industries,
                "markets": self.matched_markets,
                "temporal": self.matched_temporal,
                "themes": self.matched_themes,
                "patterns": self.matched_patterns,
                "exclusions": self.matched_exclusions,
            },
        }


class KeywordScorer:
    """Fast keyword-based relevance scorer.

    Uses keywords from client.yaml to score content relevance
    across multiple dimensions with configurable weights.
    """

    # Default temporal keywords (German)
    DEFAULT_TEMPORAL_KEYWORDS = [
        "sofort",
        "dringend",
        "frist",
        "deadline",
        "ab sofort",
        "unverzüglich",
        "zeitnah",
        "kurzfristig",
        "in kraft",
        "beschlossen",
        "verabschiedet",
        "neu",
        "änderung",
        "reform",
    ]

    def __init__(
        self,
        client_config: dict[str, Any],
        additional_keywords: Optional[list[str]] = None,
        dimension_weights: Optional[dict[str, float]] = None,
    ):
        """Initialize the keyword scorer.

        Args:
            client_config: Loaded client.yaml configuration
            additional_keywords: Extra keywords for general relevance
            dimension_weights: Optional custom weights for dimensions
        """
        self.client_config = client_config
        self.additional_keywords = additional_keywords or []

        # Extract keyword lists from config using schema helpers
        # This supports both nested and flat formats
        self._company_terms = self._normalize_keywords(
            extract_company_terms(client_config)
        )
        self._core_industries = self._normalize_keywords(
            extract_industries(client_config)
        )

        # Extract markets using helper
        primary_markets, secondary_markets = extract_markets(client_config)
        self._primary_markets = self._normalize_keywords(primary_markets)
        self._secondary_markets = self._normalize_keywords(secondary_markets)

        self._strategic_themes = self._normalize_keywords(
            client_config.get("strategic_themes", [])
        )
        self._direct_impact_keywords = self._normalize_keywords(
            client_config.get("direct_impact_keywords", [])
        )
        self._exclusion_terms = self._normalize_keywords(
            extract_exclusion_terms(client_config)
        )

        # Extract topic patterns
        self._topic_patterns = self._process_topic_patterns(
            client_config.get("topic_patterns", {})
        )

        # Temporal keywords
        self._temporal_keywords = self._normalize_keywords(
            self.DEFAULT_TEMPORAL_KEYWORDS
        )

        # Regulatory vocabulary (v3 amplifiers)
        self._regulatory_actors = self._normalize_keywords(
            extract_regulatory_actors(client_config)
        )
        self._legislative_terms = self._normalize_keywords(
            extract_legislative_terms(client_config)
        )

        # Dimension weights
        self._weights = dimension_weights or {
            "direct_impact": 0.40,
            "industry_relevance": 0.25,
            "geographic_relevance": 0.15,
            "temporal_urgency": 0.10,
            "strategic_alignment": 0.10,
        }

        logger.info(
            "Initialized KeywordScorer",
            industries=len(self._core_industries),
            markets=len(self._primary_markets) + len(self._secondary_markets),
            themes=len(self._strategic_themes),
            impact_keywords=len(self._direct_impact_keywords),
            topic_patterns=len(self._topic_patterns),
            regulatory_actors=len(self._regulatory_actors),
            legislative_terms=len(self._legislative_terms),
        )

    def _normalize_keywords(self, keywords: list[str]) -> list[str]:
        """Normalize keywords to lowercase for matching.

        Args:
            keywords: List of keywords

        Returns:
            Normalized lowercase keywords
        """
        return [k.lower().strip() for k in keywords if k]

    def _process_topic_patterns(
        self,
        patterns: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        """Process topic patterns from config.

        Args:
            patterns: Topic patterns from client.yaml

        Returns:
            Normalized topic patterns
        """
        processed = {}
        for topic, keywords in patterns.items():
            processed[topic] = self._normalize_keywords(keywords)
        return processed

    def score_content(
        self,
        title: str,
        content: str,
        published_date: Optional[datetime] = None,
    ) -> ScoreBreakdown:
        """Score content for relevance.

        Args:
            title: Article title
            content: Article content/description
            published_date: Optional publication date

        Returns:
            ScoreBreakdown with detailed scoring
        """
        # Prepare text for matching (lowercase)
        text_lower = f"{title} {content}".lower()
        title_lower = title.lower()

        breakdown = ScoreBreakdown(weights=self._weights)

        # Check for exclusion terms first
        for term in self._exclusion_terms:
            if term in text_lower:
                breakdown.matched_exclusions.append(term)

        # If too many exclusions, return early with low score
        if len(breakdown.matched_exclusions) >= 3:
            logger.debug("Content excluded due to exclusion terms")
            return breakdown

        # 1. Direct Impact Score (40%)
        breakdown.direct_impact, breakdown.matched_direct_impact = self._score_direct_impact(
            text_lower, title_lower
        )

        # 2. Industry Relevance Score (25%)
        breakdown.industry_relevance, breakdown.matched_industries = self._score_industry(
            text_lower
        )

        # 3. Geographic Relevance Score (15%)
        breakdown.geographic_relevance, breakdown.matched_markets = self._score_geographic(
            text_lower
        )

        # 4. Temporal Urgency Score (10%)
        breakdown.temporal_urgency, breakdown.matched_temporal = self._score_temporal(
            text_lower, published_date
        )

        # 5. Strategic Alignment Score (10%)
        (
            breakdown.strategic_alignment,
            breakdown.matched_themes,
            breakdown.matched_patterns,
        ) = self._score_strategic(text_lower)

        # Apply regulatory vocabulary amplifiers (v3)
        amplifiers_applied = self._apply_regulatory_amplifiers(breakdown, text_lower)

        logger.debug(
            "Scored content",
            title=title[:50],
            total=breakdown.weighted_total,
            matches=len(breakdown.all_matched_keywords),
            amplifiers=amplifiers_applied,
        )

        return breakdown

    def _score_direct_impact(
        self,
        text: str,
        title: str,
    ) -> tuple[float, list[str]]:
        """Score for direct impact keywords.

        Direct impact keywords indicate regulatory/legal relevance:
        - "must comply", "required to", "obligation", "penalty", etc.

        Args:
            text: Full text (lowercase)
            title: Title (lowercase)

        Returns:
            Tuple of (score, matched_keywords)
        """
        matches = []

        # Check direct impact keywords
        for keyword in self._direct_impact_keywords:
            if keyword in text:
                matches.append(keyword)
                # Extra weight if in title
                if keyword in title:
                    matches.append(f"{keyword} (title)")

        # Check company terms (high impact if company mentioned)
        for term in self._company_terms:
            if term in text:
                matches.append(term)
                if term in title:
                    matches.append(f"{term} (title)")

        # Calculate score (max 100)
        if not matches:
            return 0.0, []

        # Score based on number of matches (diminishing returns)
        score = min(100, len(matches) * 15 + (20 if any("(title)" in m for m in matches) else 0))

        return score, list(set(m.replace(" (title)", "") for m in matches))

    def _score_industry(self, text: str) -> tuple[float, list[str]]:
        """Score for industry relevance.

        Args:
            text: Full text (lowercase)

        Returns:
            Tuple of (score, matched_industries)
        """
        matches = []

        for industry in self._core_industries:
            if industry in text:
                matches.append(industry)

        # Also check topic patterns for industry-related topics
        industry_topics = ["ecommerce-regulation", "compliance"]
        for topic in industry_topics:
            if topic in self._topic_patterns:
                for keyword in self._topic_patterns[topic]:
                    if keyword in text and keyword not in matches:
                        matches.append(keyword)

        if not matches:
            return 0.0, []

        score = min(100, len(matches) * 20)
        return score, matches

    def _score_geographic(self, text: str) -> tuple[float, list[str]]:
        """Score for geographic relevance.

        Args:
            text: Full text (lowercase)

        Returns:
            Tuple of (score, matched_markets)
        """
        primary_matches = []
        secondary_matches = []

        for market in self._primary_markets:
            if market in text:
                primary_matches.append(market)

        for market in self._secondary_markets:
            if market in text:
                secondary_matches.append(market)

        all_matches = primary_matches + secondary_matches

        if not all_matches:
            return 0.0, []

        # Primary markets worth more
        score = min(
            100,
            len(primary_matches) * 25 + len(secondary_matches) * 10,
        )

        return score, all_matches

    def _score_temporal(
        self,
        text: str,
        published_date: Optional[datetime],
    ) -> tuple[float, list[str]]:
        """Score for temporal urgency.

        Higher scores for:
        - Recent content
        - Urgency keywords
        - Deadline mentions

        Args:
            text: Full text (lowercase)
            published_date: Publication date

        Returns:
            Tuple of (score, matched_temporal_keywords)
        """
        matches = []
        score = 0.0

        # Check temporal keywords
        for keyword in self._temporal_keywords:
            if keyword in text:
                matches.append(keyword)

        # Keyword-based score
        if matches:
            score = min(60, len(matches) * 15)

        # Recency bonus
        if published_date:
            # Handle timezone-aware vs naive datetime comparison
            now = datetime.now()
            if published_date.tzinfo is not None:
                # Make now timezone-aware using the same timezone
                now = datetime.now(published_date.tzinfo)
            days_old = (now - published_date).days
            if days_old <= 1:
                score = min(100, score + 40)
            elif days_old <= 7:
                score = min(100, score + 25)
            elif days_old <= 30:
                score = min(100, score + 10)

        return score, matches

    def _score_strategic(
        self,
        text: str,
    ) -> tuple[float, list[str], list[str]]:
        """Score for strategic theme alignment.

        Args:
            text: Full text (lowercase)

        Returns:
            Tuple of (score, matched_themes, matched_patterns)
        """
        theme_matches = []
        pattern_matches = []

        # Check strategic themes
        for theme in self._strategic_themes:
            if theme in text:
                theme_matches.append(theme)

        # Check topic patterns
        for topic, keywords in self._topic_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    pattern_matches.append(f"{topic}:{keyword}")

        all_matches = theme_matches + pattern_matches

        if not all_matches:
            return 0.0, [], []

        # Score based on coverage
        score = min(100, len(theme_matches) * 15 + len(pattern_matches) * 10)

        # Bonus for multiple topic pattern matches
        matched_topics = set(m.split(":")[0] for m in pattern_matches)
        if len(matched_topics) >= 2:
            score = min(100, score + 20)

        return score, theme_matches, pattern_matches

    def _apply_regulatory_amplifiers(
        self,
        breakdown: ScoreBreakdown,
        text: str,
    ) -> dict[str, bool]:
        """Apply regulatory vocabulary amplifiers to direct_impact score.

        Amplifiers boost the direct_impact dimension score when regulatory actors
        or legislative terms are present, indicating authoritative regulatory content.

        Args:
            breakdown: ScoreBreakdown object to modify
            text: Full text (lowercase)

        Returns:
            Dictionary indicating which amplifiers were applied
        """
        amplifiers_applied = {
            "regulatory_actors": False,
            "legislative_terms": False,
        }

        # Store original direct_impact score
        original_score = breakdown.direct_impact

        # Check for regulatory actors (20% boost)
        actor_matches = []
        for actor in self._regulatory_actors:
            if actor in text:
                actor_matches.append(actor)

        if actor_matches:
            breakdown.direct_impact = min(100.0, breakdown.direct_impact * 1.20)
            amplifiers_applied["regulatory_actors"] = True
            logger.debug(
                "Applied regulatory_actor amplifier",
                actors=actor_matches[:3],
                original=original_score,
                amplified=breakdown.direct_impact,
            )

        # Check for legislative terms (15% boost)
        term_matches = []
        for term in self._legislative_terms:
            if term in text:
                term_matches.append(term)

        if term_matches:
            breakdown.direct_impact = min(100.0, breakdown.direct_impact * 1.15)
            amplifiers_applied["legislative_terms"] = True
            logger.debug(
                "Applied legislative_terms amplifier",
                terms=term_matches[:3],
                amplified=breakdown.direct_impact,
            )

        # Log combined effect if any amplifiers were applied
        if original_score != breakdown.direct_impact:
            boost_pct = ((breakdown.direct_impact - original_score) / original_score * 100) if original_score > 0 else 0
            logger.info(
                "Regulatory amplifiers applied",
                original_direct_impact=original_score,
                amplified_direct_impact=breakdown.direct_impact,
                boost_percentage=f"{boost_pct:.1f}%",
                actors_found=len(actor_matches),
                terms_found=len(term_matches),
            )

        return amplifiers_applied

    def is_relevant(
        self,
        title: str,
        content: str,
        threshold: float = 30.0,
        published_date: Optional[datetime] = None,
    ) -> tuple[bool, ScoreBreakdown]:
        """Quick check if content is relevant above threshold.

        Args:
            title: Article title
            content: Article content
            threshold: Minimum score to be considered relevant
            published_date: Optional publication date

        Returns:
            Tuple of (is_relevant, score_breakdown)
        """
        breakdown = self.score_content(title, content, published_date)

        # Check for exclusions
        if len(breakdown.matched_exclusions) >= 2:
            return False, breakdown

        is_relevant = breakdown.weighted_total >= threshold
        return is_relevant, breakdown
