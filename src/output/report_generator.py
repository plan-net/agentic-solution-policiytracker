import os
from datetime import datetime
from typing import Any, Optional

import structlog
from jinja2 import Environment, FileSystemLoader

from src.analysis.aggregator import ResultAggregator
from src.analysis.topic_clusterer import TopicClusterer
from src.llm.langchain_service import langchain_llm_service
from src.models.report import ReportData, ReportSummary, TopicCluster
from src.models.scoring import ScoringResult
from src.output.formatter import MarkdownFormatter

logger = structlog.get_logger()


class ReportGenerator:
    """Generate markdown reports from analysis results."""

    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir), trim_blocks=True, lstrip_blocks=True
        )

        # Add custom filters
        self.jinja_env.filters["escape_md"] = MarkdownFormatter.escape_markdown
        self.jinja_env.filters["truncate_text"] = MarkdownFormatter.truncate_text
        self.jinja_env.filters["format_score"] = MarkdownFormatter.format_score
        self.jinja_env.filters["clean_filename"] = MarkdownFormatter.clean_filename

        self.aggregator = ResultAggregator()
        self.clusterer = TopicClusterer()

    async def prepare_report_data(
        self,
        job_id: str,
        job_name: str,
        scoring_results: list[ScoringResult],
        failed_documents: list[dict[str, str]],
        context: dict[str, Any],
        parameters: dict[str, Any],
    ) -> ReportData:
        """Prepare comprehensive report data."""
        try:
            logger.info("Preparing report data", job_id=job_id, results_count=len(scoring_results))

            # Generate topic clusters
            topic_clusters = await self.clusterer.cluster_by_topic(scoring_results)

            # Generate priority queues
            priority_queues = self.aggregator.group_by_priority(scoring_results)

            # Calculate aggregate metrics
            metrics = self.aggregator.calculate_aggregate_metrics(scoring_results)

            # Generate insights and recommendations (enhanced with LLM)
            llm_insights = await self._generate_llm_insights(scoring_results, context, job_id)
            insights = self.aggregator.generate_insights(scoring_results)
            recommendations = self.aggregator.generate_recommendations(scoring_results)

            # Combine traditional and LLM insights
            if llm_insights:
                insights = (
                    llm_insights.key_findings + insights[:2]
                )  # LLM insights first, then top 2 traditional
                recommendations = llm_insights.recommendations + recommendations[:2]

            # Create summary
            summary = ReportSummary(
                total_documents_analyzed=len(scoring_results),
                high_priority_count=len([r for r in scoring_results if r.master_score >= 75]),
                key_findings=insights[:5],  # Top 5 insights
                recommended_actions=recommendations[:5],  # Top 5 recommendations
                processing_time_minutes=metrics.get("processing_statistics", {}).get(
                    "total_time_ms", 0
                )
                / 60000,
                confidence_overview={
                    "high": len([r for r in scoring_results if r.confidence_score >= 0.8]),
                    "medium": len([r for r in scoring_results if 0.6 <= r.confidence_score < 0.8]),
                    "low": len([r for r in scoring_results if r.confidence_score < 0.6]),
                },
            )

            # Create report data
            report_data = ReportData(
                job_id=job_id,
                job_name=job_name,
                generation_timestamp=datetime.now(),
                summary=summary,
                priority_queues=priority_queues,
                topic_clusters=topic_clusters,
                all_results=scoring_results,
                failed_documents=failed_documents,
                context_file_used=parameters.get("context_file", "Unknown"),
                parameters_used=parameters,
                performance_metrics={
                    "total_time_seconds": metrics.get("processing_statistics", {}).get(
                        "total_time_ms", 0
                    )
                    / 1000,
                    "avg_time_per_doc_ms": metrics.get("processing_statistics", {}).get(
                        "average_time_ms", 0
                    ),
                    "avg_score": metrics.get("score_statistics", {}).get("average", 0.0),
                    "max_score": metrics.get("score_statistics", {}).get("maximum", 0.0),
                    "min_score": metrics.get("score_statistics", {}).get("minimum", 0.0),
                    "avg_confidence": metrics.get("confidence_statistics", {}).get("average", 0.0),
                    "max_confidence": metrics.get("confidence_statistics", {}).get(
                        "high_confidence_count", 0.0
                    ),
                    "min_confidence": metrics.get("confidence_statistics", {}).get(
                        "low_confidence_count", 0.0
                    ),
                },
            )

            logger.info(
                "Report data prepared successfully",
                job_id=job_id,
                topic_clusters=len(topic_clusters),
                priority_queues=len(priority_queues),
            )

            return report_data

        except Exception as e:
            logger.error("Failed to prepare report data", job_id=job_id, error=str(e))
            raise

    async def generate_markdown_content(self, report_data: ReportData) -> str:
        """Generate markdown content without writing to file."""
        try:
            logger.info("Generating markdown content")

            # Load main report template
            template = self.jinja_env.get_template("report.md.j2")

            # Render report content with same parameters as generate_markdown_report
            markdown_content = template.render(
                job_id=report_data.job_id,
                job_name=report_data.job_name,
                generation_timestamp=report_data.generation_timestamp,
                summary=report_data.summary,
                priority_queues=report_data.priority_queues,
                topic_clusters=report_data.topic_clusters,
                all_results=report_data.all_results,
                failed_documents=report_data.failed_documents,
                context_file_used=report_data.context_file_used,
                parameters_used=report_data.parameters_used,
                performance_metrics=report_data.performance_metrics,
            )

            return markdown_content

        except Exception as e:
            logger.error("Failed to generate markdown content", error=str(e))
            raise

    async def generate_markdown_report(self, report_data: ReportData, output_path: str) -> str:
        """Generate full markdown report."""
        try:
            logger.info("Generating markdown report", output_path=output_path)

            # Load main report template
            template = self.jinja_env.get_template("report.md.j2")

            # Render report
            markdown_content = template.render(
                job_id=report_data.job_id,
                job_name=report_data.job_name,
                generation_timestamp=report_data.generation_timestamp,
                summary=report_data.summary,
                priority_queues=report_data.priority_queues,
                topic_clusters=report_data.topic_clusters,
                all_results=report_data.all_results,
                failed_documents=report_data.failed_documents,
                context_file_used=report_data.context_file_used,
                parameters_used=report_data.parameters_used,
                performance_metrics=report_data.performance_metrics,
            )

            # Write to file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            logger.info(
                "Markdown report generated successfully",
                output_path=output_path,
                file_size=len(markdown_content),
            )

            return output_path

        except Exception as e:
            logger.error(
                "Failed to generate markdown report", output_path=output_path, error=str(e)
            )
            raise

    async def generate_summary_report(self, report_data: ReportData, output_path: str) -> str:
        """Generate executive summary report."""
        try:
            template = self.jinja_env.get_template("summary.md.j2")

            summary_content = template.render(
                job_name=report_data.job_name,
                generation_timestamp=report_data.generation_timestamp,
                total_documents_analyzed=report_data.summary.total_documents_analyzed,
                high_priority_count=report_data.summary.high_priority_count,
                processing_time_minutes=report_data.summary.processing_time_minutes,
                key_findings=report_data.summary.key_findings,
                recommended_actions=report_data.summary.recommended_actions,
                confidence_overview=report_data.summary.confidence_overview,
            )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(summary_content)

            logger.info("Summary report generated", output_path=output_path)
            return output_path

        except Exception as e:
            logger.error("Failed to generate summary report", error=str(e))
            raise

    def create_cluster_report(self, cluster: TopicCluster) -> str:
        """Generate report section for a topic cluster."""
        try:
            template = self.jinja_env.get_template("cluster.md.j2")

            return template.render(
                topic_name=cluster.topic_name,
                document_count=cluster.document_count,
                average_score=cluster.average_score,
                topic_description=cluster.topic_description,
                key_themes=cluster.key_themes,
                documents=cluster.documents,
            )

        except Exception as e:
            logger.error("Failed to create cluster report", error=str(e))
            return f"Error generating cluster report: {str(e)}"

    def validate_report_data(self, report_data: ReportData) -> list[str]:
        """Validate report data and return list of issues."""
        issues = []

        # Check required fields
        if not report_data.job_id:
            issues.append("Missing job ID")

        if not report_data.job_name:
            issues.append("Missing job name")

        # Check data consistency
        total_in_queues = sum(q.document_count for q in report_data.priority_queues)
        if total_in_queues != len(report_data.all_results):
            issues.append(
                f"Priority queue count mismatch: {total_in_queues} vs {len(report_data.all_results)}"
            )

        # Check for empty results
        if not report_data.all_results and not report_data.failed_documents:
            issues.append("No results or failed documents found")

        # Check timestamp
        if not report_data.generation_timestamp:
            issues.append("Missing generation timestamp")

        return issues

    async def _generate_llm_insights(
        self,
        scoring_results: list[ScoringResult],
        context: dict[str, Any],
        job_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Generate LLM-powered insights for the report."""
        try:
            if not langchain_llm_service.enabled:
                logger.debug("LLM service not enabled, skipping insights generation")
                return None

            # Prepare results summary for LLM
            results_summary = self._prepare_results_summary(scoring_results)

            # langchain_service handles prompts internally

            # Generate insights using LLM
            llm_insights = await langchain_llm_service.generate_report_insights(
                [result.dict() for result in scoring_results], context, session_id=job_id
            )

            logger.info(
                "Generated LLM insights for report",
                confidence=getattr(llm_insights, "confidence", "unknown"),
            )
            return llm_insights

        except Exception as e:
            logger.warning("Failed to generate LLM insights", error=str(e))
            return None

    def _prepare_results_summary(self, scoring_results: list[ScoringResult]) -> str:
        """Prepare a summary of scoring results for LLM processing."""
        if not scoring_results:
            return "No results to summarize"

        # High-level statistics
        total_docs = len(scoring_results)
        high_priority = len([r for r in scoring_results if r.master_score >= 75])
        medium_priority = len([r for r in scoring_results if 50 <= r.master_score < 75])
        low_priority = len([r for r in scoring_results if r.master_score < 50])

        avg_score = sum(r.master_score for r in scoring_results) / total_docs
        avg_confidence = sum(r.confidence_score for r in scoring_results) / total_docs

        # Top findings
        top_results = sorted(scoring_results, key=lambda x: x.master_score, reverse=True)[:5]
        top_findings = []
        for result in top_results:
            top_dim = (
                max(result.dimension_scores.items(), key=lambda x: x[1].score)
                if result.dimension_scores
                else ("unknown", None)
            )
            top_findings.append(
                {
                    "score": result.master_score,
                    "top_dimension": top_dim[0],
                    "justification": result.overall_justification[:200] + "..."
                    if len(result.overall_justification) > 200
                    else result.overall_justification,
                }
            )

        summary = f"""
Analysis Summary:
- Total Documents: {total_docs}
- High Priority (75+): {high_priority} ({high_priority/total_docs*100:.1f}%)
- Medium Priority (50-74): {medium_priority} ({medium_priority/total_docs*100:.1f}%)
- Low Priority (<50): {low_priority} ({low_priority/total_docs*100:.1f}%)
- Average Score: {avg_score:.1f}
- Average Confidence: {avg_confidence:.2f}

Top 5 Findings:
"""

        for i, finding in enumerate(top_findings, 1):
            summary += f"{i}. Score {finding['score']}: {finding['top_dimension']} - {finding['justification']}\n"

        return summary

    def estimate_report_size(self, report_data: ReportData) -> dict[str, int]:
        """Estimate the size of the generated report."""
        # Rough estimation based on content
        base_size = 5000  # Base template size

        # Estimate based on content
        results_size = len(report_data.all_results) * 500  # ~500 chars per result
        clusters_size = len(report_data.topic_clusters) * 300  # ~300 chars per cluster
        failed_docs_size = len(report_data.failed_documents) * 100  # ~100 chars per failed doc

        total_estimated = base_size + results_size + clusters_size + failed_docs_size

        return {
            "estimated_total_chars": total_estimated,
            "estimated_size_kb": total_estimated // 1024,
            "base_template": base_size,
            "results_content": results_size,
            "clusters_content": clusters_size,
            "failed_docs_content": failed_docs_size,
        }
