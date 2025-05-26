from collections import defaultdict
from typing import Any

import structlog

from src.analysis.priority_classifier import PriorityClassifier
from src.models.report import PriorityQueue
from src.models.scoring import PriorityLevel, ScoringResult

logger = structlog.get_logger()


class ResultAggregator:
    """Aggregate and organize scoring results for reporting."""

    def __init__(self):
        self.priority_classifier = PriorityClassifier()

    def group_by_priority(self, scoring_results: list[ScoringResult]) -> list[PriorityQueue]:
        """Group scoring results by priority level."""
        try:
            logger.info("Grouping results by priority", document_count=len(scoring_results))

            # Classify by priority
            priority_groups = self.priority_classifier.classify_by_priority(scoring_results)

            # Convert to PriorityQueue objects
            priority_queues = []

            # Ensure all priority levels are represented (even if empty)
            for priority_level in PriorityLevel:
                documents = priority_groups.get(priority_level, [])

                if documents or priority_level in [PriorityLevel.CRITICAL, PriorityLevel.HIGH]:
                    # Always include critical and high even if empty for completeness
                    priority_queue = PriorityQueue(
                        priority_level=priority_level,
                        document_count=len(documents),
                        documents=documents,
                    )
                    priority_queues.append(priority_queue)

            logger.info("Priority grouping completed", queue_count=len(priority_queues))

            return priority_queues

        except Exception as e:
            logger.error("Priority grouping failed", error=str(e))
            raise

    def calculate_aggregate_metrics(self, scoring_results: list[ScoringResult]) -> dict[str, Any]:
        """Calculate aggregate metrics across all results."""
        if not scoring_results:
            return self._empty_metrics()

        scores = [result.master_score for result in scoring_results]
        confidence_scores = [result.confidence_score for result in scoring_results]

        metrics = {
            "total_documents": len(scoring_results),
            "score_statistics": {
                "average": round(sum(scores) / len(scores), 1),
                "maximum": max(scores),
                "minimum": min(scores),
                "median": round(sorted(scores)[len(scores) // 2], 1),
            },
            "confidence_statistics": {
                "average": round(sum(confidence_scores) / len(confidence_scores), 3),
                "high_confidence_count": len([c for c in confidence_scores if c >= 0.8]),
                "medium_confidence_count": len([c for c in confidence_scores if 0.6 <= c < 0.8]),
                "low_confidence_count": len([c for c in confidence_scores if c < 0.6]),
            },
            "priority_distribution": self._calculate_priority_distribution(scoring_results),
            "dimension_analysis": self._analyze_dimensions(scoring_results),
            "processing_statistics": self._calculate_processing_stats(scoring_results),
        }

        return metrics

    def _empty_metrics(self) -> dict[str, Any]:
        """Return empty metrics structure."""
        return {
            "total_documents": 0,
            "score_statistics": {"average": 0, "maximum": 0, "minimum": 0, "median": 0},
            "confidence_statistics": {
                "average": 0,
                "high_confidence_count": 0,
                "medium_confidence_count": 0,
                "low_confidence_count": 0,
            },
            "priority_distribution": {},
            "dimension_analysis": {},
            "processing_statistics": {"total_time_ms": 0, "average_time_ms": 0},
        }

    def _calculate_priority_distribution(
        self, scoring_results: list[ScoringResult]
    ) -> dict[str, int]:
        """Calculate distribution of documents across priority levels."""
        distribution = defaultdict(int)

        for result in scoring_results:
            distribution[result.priority_level.value] += 1

        return dict(distribution)

    def _analyze_dimensions(self, scoring_results: list[ScoringResult]) -> dict[str, Any]:
        """Analyze dimension scores across all documents."""
        dimension_stats = defaultdict(list)

        # Collect all dimension scores
        for result in scoring_results:
            for dim_name, dim_score in result.dimension_scores.items():
                dimension_stats[dim_name].append(dim_score.score)

        # Calculate statistics for each dimension
        analysis = {}
        for dim_name, scores in dimension_stats.items():
            if scores:
                analysis[dim_name] = {
                    "average": round(sum(scores) / len(scores), 1),
                    "maximum": max(scores),
                    "minimum": min(scores),
                    "high_scoring_count": len([s for s in scores if s >= 70]),
                    "weight": scoring_results[0].dimension_scores[dim_name].weight,
                }

        return analysis

    def _calculate_processing_stats(self, scoring_results: list[ScoringResult]) -> dict[str, float]:
        """Calculate processing time statistics."""
        processing_times = [
            result.processing_time_ms for result in scoring_results if result.processing_time_ms > 0
        ]

        if not processing_times:
            return {"total_time_ms": 0, "average_time_ms": 0}

        return {
            "total_time_ms": round(sum(processing_times), 2),
            "average_time_ms": round(sum(processing_times) / len(processing_times), 2),
        }

    def generate_insights(self, scoring_results: list[ScoringResult]) -> list[str]:
        """Generate insights based on aggregate analysis."""
        insights = []

        if not scoring_results:
            insights.append("No documents were successfully processed")
            return insights

        metrics = self.calculate_aggregate_metrics(scoring_results)

        # Score insights
        avg_score = metrics["score_statistics"]["average"]
        if avg_score >= 70:
            insights.append(f"High overall relevance detected (average score: {avg_score})")
        elif avg_score >= 50:
            insights.append(f"Moderate relevance across documents (average score: {avg_score})")
        else:
            insights.append(f"Low overall relevance (average score: {avg_score})")

        # Priority insights
        priority_dist = metrics["priority_distribution"]
        high_priority_count = priority_dist.get("critical", 0) + priority_dist.get("high", 0)

        if high_priority_count > 0:
            percentage = round(high_priority_count / metrics["total_documents"] * 100)
            insights.append(
                f"{high_priority_count} high-priority documents identified ({percentage}% of total)"
            )

        # Dimension insights
        dimension_analysis = metrics["dimension_analysis"]
        if dimension_analysis:
            # Find strongest dimension
            strongest_dim = max(dimension_analysis.items(), key=lambda x: x[1]["average"])
            dim_name = strongest_dim[0].replace("_", " ").title()
            avg_score = strongest_dim[1]["average"]
            insights.append(f"{dim_name} is the strongest relevance factor (average: {avg_score})")

        # Confidence insights
        confidence_stats = metrics["confidence_statistics"]
        high_conf_pct = round(
            confidence_stats["high_confidence_count"] / metrics["total_documents"] * 100
        )

        if high_conf_pct >= 70:
            insights.append(f"High confidence in results ({high_conf_pct}% high confidence)")
        elif high_conf_pct >= 40:
            insights.append(f"Moderate confidence in results ({high_conf_pct}% high confidence)")
        else:
            insights.append(f"Lower confidence in results ({high_conf_pct}% high confidence)")

        return insights

    def generate_recommendations(self, scoring_results: list[ScoringResult]) -> list[str]:
        """Generate action recommendations based on results."""
        recommendations = []

        if not scoring_results:
            recommendations.append("No actionable documents found - review input criteria")
            return recommendations

        metrics = self.calculate_aggregate_metrics(scoring_results)
        priority_dist = metrics["priority_distribution"]

        # Critical priority recommendations
        critical_count = priority_dist.get("critical", 0)
        if critical_count > 0:
            recommendations.append(
                f"Immediate review required for {critical_count} critical priority documents"
            )

        # High priority recommendations
        high_count = priority_dist.get("high", 0)
        if high_count > 0:
            recommendations.append(
                f"Schedule review of {high_count} high priority documents within 1 week"
            )

        # Medium priority recommendations
        medium_count = priority_dist.get("medium", 0)
        if medium_count > 5:
            recommendations.append(
                f"Batch review {medium_count} medium priority documents by priority sub-groups"
            )

        # Confidence-based recommendations
        confidence_stats = metrics["confidence_statistics"]
        low_conf_count = confidence_stats["low_confidence_count"]

        if low_conf_count > 0:
            recommendations.append(
                f"Manual verification recommended for {low_conf_count} low-confidence results"
            )

        # Processing recommendations
        if metrics["total_documents"] > 100:
            recommendations.append(
                "Consider setting up automated monitoring for large document volumes"
            )

        return recommendations[:5]  # Limit to top 5 recommendations
