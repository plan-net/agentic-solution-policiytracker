from collections import defaultdict

import structlog

from src.models.scoring import PriorityLevel, ScoringResult

logger = structlog.get_logger()


class PriorityClassifier:
    """Classify documents by priority level."""

    def __init__(self):
        self.priority_thresholds = {
            PriorityLevel.CRITICAL: 90,
            PriorityLevel.HIGH: 75,
            PriorityLevel.MEDIUM: 50,
            PriorityLevel.LOW: 25,
            PriorityLevel.INFORMATIONAL: 0,
        }

    def classify_by_priority(
        self, scoring_results: list[ScoringResult]
    ) -> dict[PriorityLevel, list[ScoringResult]]:
        """Classify documents into priority levels."""
        try:
            logger.info("Classifying documents by priority", document_count=len(scoring_results))

            priority_groups = defaultdict(list)

            for result in scoring_results:
                priority_level = self._determine_priority_level(result.master_score)
                priority_groups[priority_level].append(result)

            # Sort documents within each priority level by score (highest first)
            for priority_level in priority_groups:
                priority_groups[priority_level].sort(key=lambda x: x.master_score, reverse=True)

            # Log distribution
            distribution = {level.value: len(docs) for level, docs in priority_groups.items()}
            logger.info("Priority distribution", distribution=distribution)

            return dict(priority_groups)

        except Exception as e:
            logger.error("Priority classification failed", error=str(e))
            raise

    def _determine_priority_level(self, master_score: float) -> PriorityLevel:
        """Determine priority level based on master score."""
        if master_score >= self.priority_thresholds[PriorityLevel.CRITICAL]:
            return PriorityLevel.CRITICAL
        elif master_score >= self.priority_thresholds[PriorityLevel.HIGH]:
            return PriorityLevel.HIGH
        elif master_score >= self.priority_thresholds[PriorityLevel.MEDIUM]:
            return PriorityLevel.MEDIUM
        elif master_score >= self.priority_thresholds[PriorityLevel.LOW]:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.INFORMATIONAL

    def get_priority_summary(
        self, priority_groups: dict[PriorityLevel, list[ScoringResult]]
    ) -> dict[str, any]:
        """Get summary statistics for priority groups."""
        summary = {
            "total_documents": sum(len(docs) for docs in priority_groups.values()),
            "by_priority": {},
            "score_ranges": {},
            "top_documents": [],
        }

        for priority_level, documents in priority_groups.items():
            if documents:
                scores = [doc.master_score for doc in documents]
                summary["by_priority"][priority_level.value] = {
                    "count": len(documents),
                    "percentage": round(len(documents) / summary["total_documents"] * 100, 1),
                    "avg_score": round(sum(scores) / len(scores), 1),
                    "max_score": max(scores),
                    "min_score": min(scores),
                }

                # Add top document from this priority level
                if priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
                    top_doc = documents[0]  # Already sorted by score
                    summary["top_documents"].append(
                        {
                            "document_id": top_doc.document_id,
                            "score": top_doc.master_score,
                            "priority": priority_level.value,
                            "justification": top_doc.overall_justification,
                        }
                    )

        return summary

    def filter_by_threshold(
        self, scoring_results: list[ScoringResult], threshold: float
    ) -> list[ScoringResult]:
        """Filter documents by score threshold."""
        filtered = [result for result in scoring_results if result.master_score >= threshold]

        logger.info(
            "Filtered documents by threshold",
            threshold=threshold,
            original_count=len(scoring_results),
            filtered_count=len(filtered),
        )

        return filtered

    def filter_by_confidence(
        self, scoring_results: list[ScoringResult], min_confidence: float
    ) -> list[ScoringResult]:
        """Filter documents by confidence threshold."""
        filtered = [
            result for result in scoring_results if result.confidence_score >= min_confidence
        ]

        logger.info(
            "Filtered documents by confidence",
            min_confidence=min_confidence,
            original_count=len(scoring_results),
            filtered_count=len(filtered),
        )

        return filtered
