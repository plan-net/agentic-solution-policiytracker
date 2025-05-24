import statistics
from typing import Dict, List

from src.models.content import ProcessedContent
from src.models.scoring import DimensionScore


class ConfidenceCalculator:
    """Calculate confidence scores for scoring results."""

    @staticmethod
    def calculate_confidence(
        document: ProcessedContent, dimension_scores: Dict[str, DimensionScore]
    ) -> float:
        """Calculate overall confidence score (0-1)."""

        factors = {
            "text_length": 0.2,
            "keyword_density": 0.3,
            "score_variance": 0.2,
            "evidence_quality": 0.3,
        }

        # Text length factor (longer documents = higher confidence)
        text_length_factor = min(document.word_count / 500, 1.0)

        # Keyword density factor (more evidence = higher confidence)
        total_evidence = sum(len(score.evidence_snippets) for score in dimension_scores.values())
        max_possible_evidence = len(dimension_scores) * 3  # 3 snippets per dimension
        keyword_density_factor = (
            total_evidence / max_possible_evidence if max_possible_evidence > 0 else 0.0
        )

        # Score variance factor (lower variance = higher confidence)
        scores = [score.score for score in dimension_scores.values()]
        if len(scores) > 1:
            score_std = statistics.stdev(scores)
            score_variance_factor = max(
                0.0, 1.0 - (score_std / 50)
            )  # Normalize by max possible std
        else:
            score_variance_factor = 0.5  # Default for single score

        # Evidence quality factor (more detailed evidence = higher confidence)
        total_evidence_chars = sum(
            sum(len(snippet) for snippet in score.evidence_snippets)
            for score in dimension_scores.values()
        )
        evidence_quality_factor = min(
            total_evidence_chars / 1500, 1.0
        )  # Normalize by expected length

        # Calculate weighted confidence
        confidence = (
            text_length_factor * factors["text_length"]
            + keyword_density_factor * factors["keyword_density"]
            + score_variance_factor * factors["score_variance"]
            + evidence_quality_factor * factors["evidence_quality"]
        )

        return max(0.0, min(1.0, confidence))

    @staticmethod
    def get_confidence_factors(
        document: ProcessedContent, dimension_scores: Dict[str, DimensionScore]
    ) -> Dict[str, float]:
        """Get detailed confidence factors for debugging."""

        text_length_factor = min(document.word_count / 500, 1.0)

        total_evidence = sum(len(score.evidence_snippets) for score in dimension_scores.values())
        max_possible_evidence = len(dimension_scores) * 3
        keyword_density_factor = (
            total_evidence / max_possible_evidence if max_possible_evidence > 0 else 0.0
        )

        scores = [score.score for score in dimension_scores.values()]
        if len(scores) > 1:
            score_std = statistics.stdev(scores)
            score_variance_factor = max(0.0, 1.0 - (score_std / 50))
        else:
            score_variance_factor = 0.5

        total_evidence_chars = sum(
            sum(len(snippet) for snippet in score.evidence_snippets)
            for score in dimension_scores.values()
        )
        evidence_quality_factor = min(total_evidence_chars / 1500, 1.0)

        return {
            "text_length": text_length_factor,
            "keyword_density": keyword_density_factor,
            "score_variance": score_variance_factor,
            "evidence_quality": evidence_quality_factor,
        }
