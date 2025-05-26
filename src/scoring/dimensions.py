import re
from typing import Any

from src.models.content import ProcessedContent
from src.models.scoring import DimensionScore


class DimensionScorer:
    """Base class for dimension scoring."""

    def __init__(self, context: dict[str, Any]):
        self.context = context

    def extract_evidence(self, text: str, keywords: list[str], max_snippets: int = 3) -> list[str]:
        """Extract evidence snippets containing keywords."""
        evidence = []
        text_lower = text.lower()
        sentences = re.split(r"[.!?]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_lower = sentence.lower()
            for keyword in keywords:
                if keyword.lower() in sentence_lower:
                    # Add context around the keyword
                    evidence.append(sentence[:200] + "..." if len(sentence) > 200 else sentence)
                    break

            if len(evidence) >= max_snippets:
                break

        return evidence


class DirectImpactScorer(DimensionScorer):
    """Score based on direct impact to company/organization."""

    def score(self, document: ProcessedContent) -> DimensionScore:
        text = document.raw_text.lower()
        score = 20  # Base score
        evidence = []
        justification_parts = []

        # Company/brand mentions (highest impact)
        company_terms = self.context.get("company_terms", [])
        company_mentions = 0

        for term in company_terms:
            mentions = len(re.findall(rf"\b{re.escape(term.lower())}\b", text))
            company_mentions += mentions

        if company_mentions > 0:
            score = min(100, 80 + (company_mentions * 5))
            justification_parts.append(f"Direct company mentions: {company_mentions}")
            evidence.extend(self.extract_evidence(document.raw_text, company_terms, 2))

        # High-impact regulatory language
        elif company_mentions == 0:
            regulatory_keywords = [
                "must comply",
                "required",
                "mandate",
                "penalty",
                "enforcement",
                "violation",
            ]
            regulatory_matches = sum(1 for kw in regulatory_keywords if kw in text)

            if regulatory_matches > 0:
                score = min(79, 60 + (regulatory_matches * 3))
                justification_parts.append(f"Regulatory impact indicators: {regulatory_matches}")
                evidence.extend(self.extract_evidence(document.raw_text, regulatory_keywords, 2))

            # Some impact indicators
            else:
                impact_keywords = ["compliance", "regulation", "legal requirement", "policy change"]
                impact_matches = sum(1 for kw in impact_keywords if kw in text)

                if impact_matches > 0:
                    score = min(59, 40 + (impact_matches * 10))
                    justification_parts.append(f"General impact indicators: {impact_matches}")
                    evidence.extend(self.extract_evidence(document.raw_text, impact_keywords, 1))

        justification = (
            "; ".join(justification_parts)
            if justification_parts
            else "Minimal direct relevance detected"
        )

        return DimensionScore(
            dimension_name="direct_impact",
            score=float(score),
            weight=0.40,
            justification=justification,
            evidence_snippets=evidence[:3],
        )


class IndustryRelevanceScorer(DimensionScorer):
    """Score based on industry relevance."""

    def score(self, document: ProcessedContent) -> DimensionScore:
        text = document.raw_text.lower()
        score = 10  # Base score
        evidence = []
        justification_parts = []

        # Core industry terms
        core_industries = self.context.get("core_industries", [])
        core_matches = sum(1 for term in core_industries if term.lower() in text)

        if core_matches >= 3:
            score = min(100, 90 + ((core_matches - 3) * 3))
            justification_parts.append(f"Core industry focus: {core_matches} matches")
            evidence.extend(self.extract_evidence(document.raw_text, core_industries, 2))

        elif core_matches > 0:
            score = min(89, 70 + (core_matches * 10))
            justification_parts.append(f"Some core industry relevance: {core_matches} matches")
            evidence.extend(self.extract_evidence(document.raw_text, core_industries, 2))

        # Adjacent industry terms
        else:
            adjacent_industries = [
                "retail",
                "consumer goods",
                "technology",
                "digital",
                "marketplace",
            ]
            adjacent_matches = sum(1 for term in adjacent_industries if term.lower() in text)

            if adjacent_matches >= 2:
                score = min(69, 50 + (adjacent_matches * 5))
                justification_parts.append(
                    f"Adjacent industry relevance: {adjacent_matches} matches"
                )
                evidence.extend(self.extract_evidence(document.raw_text, adjacent_industries, 1))

            elif adjacent_matches == 1:
                score = min(49, 30 + (adjacent_matches * 10))
                justification_parts.append(f"Minimal industry relevance: {adjacent_matches} match")
                evidence.extend(self.extract_evidence(document.raw_text, adjacent_industries, 1))

        justification = (
            "; ".join(justification_parts)
            if justification_parts
            else "No industry relevance detected"
        )

        return DimensionScore(
            dimension_name="industry_relevance",
            score=float(score),
            weight=0.25,
            justification=justification,
            evidence_snippets=evidence[:3],
        )


class GeographicRelevanceScorer(DimensionScorer):
    """Score based on geographic relevance."""

    def score(self, document: ProcessedContent) -> DimensionScore:
        text = document.raw_text.lower()
        score = 15  # Base score
        evidence = []
        justification_parts = []

        # Primary markets
        primary_markets = self.context.get("primary_markets", [])
        primary_matches = sum(1 for market in primary_markets if market.lower() in text)

        if primary_matches >= 2:
            score = min(100, 85 + (primary_matches * 5))
            justification_parts.append(f"Multiple primary markets: {primary_matches}")
            evidence.extend(self.extract_evidence(document.raw_text, primary_markets, 2))

        elif primary_matches == 1:
            # Check for secondary markets to boost score
            secondary_markets = ["uk", "switzerland", "austria", "netherlands", "belgium"]
            secondary_matches = sum(1 for market in secondary_markets if market.lower() in text)
            score = min(84, 70 + (secondary_matches * 5))
            justification_parts.append(f"Single primary market with {secondary_matches} secondary")
            evidence.extend(
                self.extract_evidence(document.raw_text, primary_markets + secondary_markets, 2)
            )

        # Secondary markets only
        else:
            secondary_markets = ["uk", "switzerland", "austria", "netherlands", "belgium"]
            secondary_matches = sum(1 for market in secondary_markets if market.lower() in text)

            if secondary_matches >= 2:
                score = min(69, 50 + (secondary_matches * 5))
                justification_parts.append(f"Secondary markets: {secondary_matches}")
                evidence.extend(self.extract_evidence(document.raw_text, secondary_markets, 1))

            # Global scope
            else:
                global_terms = ["global", "worldwide", "international", "cross-border"]
                global_matches = sum(1 for term in global_terms if term.lower() in text)

                if global_matches > 0:
                    score = min(49, 40 + (global_matches * 5))
                    justification_parts.append(f"Global scope: {global_matches} indicators")
                    evidence.extend(self.extract_evidence(document.raw_text, global_terms, 1))

        justification = (
            "; ".join(justification_parts)
            if justification_parts
            else "No geographic relevance detected"
        )

        return DimensionScore(
            dimension_name="geographic_relevance",
            score=float(score),
            weight=0.15,
            justification=justification,
            evidence_snippets=evidence[:3],
        )


class TemporalUrgencyScorer(DimensionScorer):
    """Score based on temporal urgency."""

    def score(self, document: ProcessedContent) -> DimensionScore:
        text = document.raw_text.lower()
        score = 20  # Base score
        evidence = []
        justification_parts = []

        # Immediate urgency
        immediate_terms = ["immediate", "urgent", "within days", "this week", "asap"]
        immediate_matches = sum(1 for term in immediate_terms if term.lower() in text)

        if immediate_matches > 0:
            score = min(100, 90 + (immediate_matches * 5))
            justification_parts.append(f"Immediate action required: {immediate_matches} indicators")
            evidence.extend(self.extract_evidence(document.raw_text, immediate_terms, 2))

        # Short-term deadlines
        else:
            short_term = ["this month", "next month", "within 3 months", "q1", "q2"]
            short_matches = sum(1 for term in short_term if term.lower() in text)

            if short_matches > 0:
                score = min(89, 70 + (short_matches * 5))
                justification_parts.append(f"Short-term deadline: {short_matches} indicators")
                evidence.extend(self.extract_evidence(document.raw_text, short_term, 2))

            # Medium-term deadlines
            else:
                medium_term = ["within 6 months", "this year", "2024", "2025"]
                medium_matches = sum(1 for term in medium_term if term.lower() in text)

                if medium_matches > 0:
                    score = min(69, 50 + (medium_matches * 5))
                    justification_parts.append(f"Medium-term deadline: {medium_matches} indicators")
                    evidence.extend(self.extract_evidence(document.raw_text, medium_term, 1))

                # Long-term deadlines
                else:
                    long_term = ["next year", "2026", "2027", "long-term", "future"]
                    long_matches = sum(1 for term in long_term if term.lower() in text)

                    if long_matches > 0:
                        score = min(49, 30 + (long_matches * 5))
                        justification_parts.append(f"Long-term timeline: {long_matches} indicators")
                        evidence.extend(self.extract_evidence(document.raw_text, long_term, 1))

        justification = (
            "; ".join(justification_parts)
            if justification_parts
            else "No urgency indicators detected"
        )

        return DimensionScore(
            dimension_name="temporal_urgency",
            score=float(score),
            weight=0.10,
            justification=justification,
            evidence_snippets=evidence[:3],
        )


class StrategicAlignmentScorer(DimensionScorer):
    """Score based on strategic alignment."""

    def score(self, document: ProcessedContent) -> DimensionScore:
        text = document.raw_text.lower()
        score = 15  # Base score
        evidence = []
        justification_parts = []

        # Strategic themes from context
        strategic_themes = self.context.get("strategic_themes", [])
        theme_matches = sum(1 for theme in strategic_themes if theme.lower() in text)

        if theme_matches >= 3:
            score = min(100, 85 + ((theme_matches - 3) * 5))
            justification_parts.append(f"Strong strategic alignment: {theme_matches} themes")
            evidence.extend(self.extract_evidence(document.raw_text, strategic_themes, 2))

        elif theme_matches > 0:
            score = min(79, 60 + (theme_matches * 10))
            justification_parts.append(f"Moderate strategic alignment: {theme_matches} themes")
            evidence.extend(self.extract_evidence(document.raw_text, strategic_themes, 2))

        # Fallback to general strategic keywords
        else:
            strategic_keywords = [
                "innovation",
                "growth",
                "expansion",
                "transformation",
                "efficiency",
                "customer",
                "market",
            ]
            keyword_matches = sum(1 for kw in strategic_keywords if kw.lower() in text)

            if keyword_matches >= 3:
                score = min(59, 45 + (keyword_matches * 3))
                justification_parts.append(
                    f"General strategic relevance: {keyword_matches} keywords"
                )
                evidence.extend(self.extract_evidence(document.raw_text, strategic_keywords, 1))

            elif keyword_matches > 0:
                score = min(44, 30 + (keyword_matches * 5))
                justification_parts.append(
                    f"Minimal strategic relevance: {keyword_matches} keywords"
                )
                evidence.extend(self.extract_evidence(document.raw_text, strategic_keywords, 1))

        justification = (
            "; ".join(justification_parts)
            if justification_parts
            else "No strategic relevance detected"
        )

        return DimensionScore(
            dimension_name="strategic_alignment",
            score=float(score),
            weight=0.10,
            justification=justification,
            evidence_snippets=evidence[:3],
        )
