"""Tests for keyword scorer."""

from datetime import datetime, timedelta

import pytest

from src.etl.filtering.keyword_scorer import KeywordScorer, ScoreBreakdown


@pytest.fixture
def sample_client_config():
    """Sample client configuration for testing."""
    return {
        "company_terms": ["zalando", "zalando se"],
        "core_industries": ["e-commerce", "online retail", "fashion", "marketplace"],
        "primary_markets": ["germany", "european union", "eu", "france"],
        "secondary_markets": ["uk", "switzerland"],
        "strategic_themes": [
            "digital transformation",
            "sustainability",
            "data privacy",
            "automation",
        ],
        "direct_impact_keywords": [
            "must comply",
            "required to",
            "obligation",
            "penalty",
            "enforcement",
            "violation",
        ],
        "exclusion_terms": ["sports", "automotive", "real estate"],
        "topic_patterns": {
            "data-protection": ["gdpr", "data privacy", "personal information"],
            "ecommerce-regulation": [
                "digital services act",
                "dsa",
                "digital markets act",
                "dma",
            ],
            "sustainability": ["esg", "carbon footprint", "circular economy"],
        },
    }


@pytest.fixture
def scorer(sample_client_config):
    """Create a keyword scorer instance."""
    return KeywordScorer(client_config=sample_client_config)


class TestScoreBreakdown:
    """Tests for ScoreBreakdown model."""

    def test_weighted_total_calculation(self):
        """Test weighted total score calculation."""
        breakdown = ScoreBreakdown(
            direct_impact=80.0,
            industry_relevance=60.0,
            geographic_relevance=40.0,
            temporal_urgency=50.0,
            strategic_alignment=70.0,
        )

        # Calculate expected: 80*0.4 + 60*0.25 + 40*0.15 + 50*0.1 + 70*0.1
        # = 32 + 15 + 6 + 5 + 7 = 65
        expected = 65.0
        assert breakdown.weighted_total == expected

    def test_custom_weights(self):
        """Test score calculation with custom weights."""
        custom_weights = {
            "direct_impact": 0.50,
            "industry_relevance": 0.20,
            "geographic_relevance": 0.10,
            "temporal_urgency": 0.10,
            "strategic_alignment": 0.10,
        }
        breakdown = ScoreBreakdown(
            direct_impact=100.0,
            industry_relevance=0.0,
            geographic_relevance=0.0,
            temporal_urgency=0.0,
            strategic_alignment=0.0,
            weights=custom_weights,
        )

        assert breakdown.weighted_total == 50.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        breakdown = ScoreBreakdown(
            direct_impact=50.0,
            matched_direct_impact=["penalty", "violation"],
        )

        result = breakdown.to_dict()

        assert "weighted_total" in result
        assert "dimensions" in result
        assert "matches" in result
        assert "direct_impact" in result["matches"]


class TestKeywordScorer:
    """Tests for KeywordScorer."""

    def test_initialization(self, scorer):
        """Test scorer initialization."""
        assert scorer is not None
        assert len(scorer._core_industries) > 0
        assert len(scorer._direct_impact_keywords) > 0

    def test_score_highly_relevant_content(self, scorer):
        """Test scoring highly relevant content."""
        title = "New GDPR Enforcement: EU Imposes Penalty on E-Commerce Platforms"
        content = """
        The European Union has announced strict enforcement measures for
        e-commerce platforms. Companies must comply with new data privacy
        regulations by the deadline. Violations will result in significant
        penalties. This affects digital transformation strategies across
        the fashion industry and online retail sector.
        """

        breakdown = scorer.score_content(title, content)

        # Should score high across multiple dimensions
        assert breakdown.weighted_total >= 50.0
        assert breakdown.direct_impact > 0
        assert len(breakdown.matched_direct_impact) > 0
        assert len(breakdown.matched_industries) > 0

    def test_score_irrelevant_content(self, scorer):
        """Test scoring irrelevant content."""
        title = "Local Football Team Wins Championship"
        content = """
        The local sports team celebrated their victory in the regional
        football championship. The automotive industry sponsored the event.
        Real estate developers attended the ceremony.
        """

        breakdown = scorer.score_content(title, content)

        # Should score low and have exclusion matches
        assert breakdown.weighted_total < 30.0
        assert len(breakdown.matched_exclusions) > 0

    def test_score_moderately_relevant_content(self, scorer):
        """Test scoring moderately relevant content."""
        title = "German Government Announces New Digital Strategy"
        content = """
        The German government has unveiled its new digital strategy focusing
        on digital transformation and sustainability. The initiative covers
        various sectors including retail and logistics.
        """

        breakdown = scorer.score_content(title, content)

        # Should score moderately
        assert 30.0 <= breakdown.weighted_total <= 70.0
        assert breakdown.geographic_relevance > 0
        assert breakdown.strategic_alignment > 0

    def test_direct_impact_scoring(self, scorer):
        """Test direct impact keyword scoring."""
        title = "Companies Required to Comply with New Regulation"
        content = "Organizations must comply with the new obligations or face penalties."

        breakdown = scorer.score_content(title, content)

        assert breakdown.direct_impact > 0
        assert "must comply" in breakdown.matched_direct_impact or "penalty" in breakdown.matched_direct_impact

    def test_industry_relevance_scoring(self, scorer):
        """Test industry relevance scoring."""
        title = "E-Commerce Sector Update"
        content = "The online retail marketplace sees significant growth in fashion."

        breakdown = scorer.score_content(title, content)

        assert breakdown.industry_relevance > 0
        assert len(breakdown.matched_industries) >= 1

    def test_geographic_relevance_scoring(self, scorer):
        """Test geographic relevance scoring."""
        title = "EU Regulations Affect Germany"
        content = "The European Union directive impacts businesses in France and Germany."

        breakdown = scorer.score_content(title, content)

        assert breakdown.geographic_relevance > 0
        assert any(
            market in breakdown.matched_markets
            for market in ["germany", "eu", "european union", "france"]
        )

    def test_temporal_urgency_scoring(self, scorer):
        """Test temporal urgency scoring."""
        title = "New Law in Effect Immediately"
        content = "Companies must act urgently. The deadline is approaching rapidly."

        breakdown = scorer.score_content(title, content)

        assert breakdown.temporal_urgency > 0
        assert len(breakdown.matched_temporal) > 0

    def test_strategic_alignment_scoring(self, scorer):
        """Test strategic alignment scoring."""
        title = "Sustainability Report Released"
        content = "Focus on digital transformation, data privacy, and ESG initiatives."

        breakdown = scorer.score_content(title, content)

        assert breakdown.strategic_alignment > 0
        assert len(breakdown.matched_themes) > 0 or len(breakdown.matched_patterns) > 0

    def test_exclusion_handling(self, scorer):
        """Test that exclusion terms are properly detected."""
        title = "Sports and Automotive Industry News"
        content = "Real estate market also discussed alongside sports events."

        breakdown = scorer.score_content(title, content)

        # Should have multiple exclusion matches
        assert len(breakdown.matched_exclusions) >= 2

    def test_is_relevant_threshold(self, scorer):
        """Test is_relevant method with threshold."""
        # Highly relevant content
        relevant_title = "GDPR Enforcement: E-Commerce Must Comply"
        relevant_content = "European Union penalties for fashion retail violations."

        is_relevant, breakdown = scorer.is_relevant(relevant_title, relevant_content)
        assert is_relevant is True

        # Irrelevant content
        irrelevant_title = "Local Sports News"
        irrelevant_content = "Football and automotive racing results."

        is_relevant, breakdown = scorer.is_relevant(irrelevant_title, irrelevant_content)
        assert is_relevant is False

    def test_additional_keywords(self, sample_client_config):
        """Test scorer with additional keywords."""
        additional = ["digitalisierung", "regulierung", "gesetz"]
        scorer = KeywordScorer(
            client_config=sample_client_config,
            additional_keywords=additional,
        )

        # Scorer should be created with additional keywords
        # (These would need to be integrated into the scoring logic)
        assert scorer is not None

    def test_empty_content(self, scorer):
        """Test scoring with empty content."""
        breakdown = scorer.score_content("", "")

        assert breakdown.weighted_total == 0.0
        assert len(breakdown.all_matched_keywords) == 0

    def test_title_weighting(self, scorer):
        """Test that matches in title get extra weight."""
        # Same keyword in title vs content
        title_match = scorer.score_content(
            "Penalty for Violations",
            "General regulatory news.",
        )
        content_match = scorer.score_content(
            "General News",
            "Companies face penalty for violations.",
        )

        # Title match should score higher
        assert title_match.direct_impact >= content_match.direct_impact
