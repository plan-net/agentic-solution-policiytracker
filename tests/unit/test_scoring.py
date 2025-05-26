import pytest

from src.scoring.confidence import ConfidenceCalculator
from src.scoring.dimensions import (
    DirectImpactScorer,
    GeographicRelevanceScorer,
    IndustryRelevanceScorer,
    StrategicAlignmentScorer,
    TemporalUrgencyScorer,
)
from src.scoring.relevance_engine import RelevanceEngine


class TestDimensionScorers:
    """Test individual dimension scorers."""

    @pytest.fixture
    def sample_context(self):
        return {
            "company_terms": ["testcorp", "test company"],
            "core_industries": ["e-commerce", "technology"],
            "primary_markets": ["eu", "germany"],
            "strategic_themes": ["digital transformation", "compliance"],
        }

    def test_direct_impact_scorer(self, sample_context, sample_processed_content):
        """Test direct impact scoring."""
        scorer = DirectImpactScorer(sample_context)

        # Test with company mention
        sample_processed_content.raw_text = "TestCorp must comply with new regulations"
        result = scorer.score(sample_processed_content)

        assert result.dimension_name == "direct_impact"
        assert result.score >= 80  # Should be high due to company mention
        assert result.weight == 0.40
        assert (
            "company mention" in result.justification.lower()
            or "testcorp" in result.justification.lower()
        )

    def test_industry_relevance_scorer(self, sample_context, sample_processed_content):
        """Test industry relevance scoring."""
        scorer = IndustryRelevanceScorer(sample_context)

        # Test with industry terms
        sample_processed_content.raw_text = "E-commerce platform technology requirements"
        result = scorer.score(sample_processed_content)

        assert result.dimension_name == "industry_relevance"
        assert result.score >= 50  # Should have some relevance
        assert result.weight == 0.25

    def test_geographic_relevance_scorer(self, sample_context, sample_processed_content):
        """Test geographic relevance scoring."""
        scorer = GeographicRelevanceScorer(sample_context)

        # Test with market terms
        sample_processed_content.raw_text = "New EU regulations in Germany"
        result = scorer.score(sample_processed_content)

        assert result.dimension_name == "geographic_relevance"
        assert result.score >= 70  # Should be high for EU + Germany
        assert result.weight == 0.15

    def test_temporal_urgency_scorer(self, sample_context, sample_processed_content):
        """Test temporal urgency scoring."""
        scorer = TemporalUrgencyScorer(sample_context)

        # Test with urgency terms
        sample_processed_content.raw_text = "Immediate action required this week"
        result = scorer.score(sample_processed_content)

        assert result.dimension_name == "temporal_urgency"
        assert result.score >= 80  # Should be high for immediate urgency
        assert result.weight == 0.10

    def test_strategic_alignment_scorer(self, sample_context, sample_processed_content):
        """Test strategic alignment scoring."""
        scorer = StrategicAlignmentScorer(sample_context)

        # Test with strategic terms
        sample_processed_content.raw_text = "Digital transformation and compliance initiatives"
        result = scorer.score(sample_processed_content)

        assert result.dimension_name == "strategic_alignment"
        assert result.score >= 60  # Should have good alignment
        assert result.weight == 0.10


class TestConfidenceCalculator:
    """Test confidence calculation."""

    def test_confidence_calculation(self, sample_processed_content, sample_dimension_scores):
        """Test confidence score calculation."""
        calculator = ConfidenceCalculator()

        confidence = calculator.calculate_confidence(
            sample_processed_content, sample_dimension_scores
        )

        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)

    def test_confidence_factors(self, sample_processed_content, sample_dimension_scores):
        """Test confidence factor breakdown."""
        calculator = ConfidenceCalculator()

        factors = calculator.get_confidence_factors(
            sample_processed_content, sample_dimension_scores
        )

        required_factors = ["text_length", "keyword_density", "score_variance", "evidence_quality"]
        for factor in required_factors:
            assert factor in factors
            assert 0.0 <= factors[factor] <= 1.0


class TestRelevanceEngine:
    """Test the main relevance engine."""

    @pytest.mark.asyncio
    async def test_score_document(self, sample_context, sample_processed_content):
        """Test document scoring through the engine."""
        engine = RelevanceEngine(sample_context)

        result = await engine.score_document(sample_processed_content)

        assert result.document_id == sample_processed_content.id
        assert 0.0 <= result.master_score <= 100.0
        assert 0.0 <= result.confidence_score <= 1.0
        assert len(result.dimension_scores) == 5  # All 5 dimensions
        assert result.overall_justification
        assert isinstance(result.key_factors, list)

    def test_scoring_summary(self, sample_context):
        """Test scoring configuration summary."""
        engine = RelevanceEngine(sample_context)

        summary = engine.get_scoring_summary()

        assert "dimensions" in summary
        assert "weights" in summary
        assert "context_summary" in summary
        assert len(summary["dimensions"]) == 5
