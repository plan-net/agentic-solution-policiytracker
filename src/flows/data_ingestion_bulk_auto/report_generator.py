"""
Bulk Auto-Delta report generator for Flow 1B.

Generates comprehensive reports for auto-detected document processing runs.
"""

from datetime import datetime
from pathlib import Path

import structlog
from jinja2 import Environment, FileSystemLoader

# Configure logging for Ray environment
from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()

logger = structlog.get_logger()


class BulkAutoReportGenerator:
    """Generate comprehensive bulk auto-delta processing reports using Jinja2 templates."""

    def __init__(self, template_dir: str = "src/flows/data_ingestion_bulk_auto/templates"):
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )

        # Add utility filters
        self.template_env.filters["escape_md"] = self._escape_markdown
        self.template_env.filters["truncate_text"] = self._truncate_text
        self.template_env.filters["basename"] = self._safe_basename
        self.template_env.filters["format_score"] = self._safe_format_score

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters."""
        if not text:
            return ""

        replacements = {
            "_": r"\_",
            "*": r"\*",
            "[": r"\[",
            "]": r"\]",
            "(": r"\(",
            ")": r"\)",
            "#": r"\#",
            "`": r"\`",
            "|": r"\|",
        }

        for char, escaped in replacements.items():
            text = text.replace(char, escaped)

        return text

    def _truncate_text(self, text: str, length: int = 100) -> str:
        """Truncate text to specified length."""
        if not text:
            return ""

        if len(text) <= length:
            return text

        return text[: length - 3] + "..."

    def _safe_basename(self, path) -> str:
        """Safely extract basename from path, handling undefined values."""
        if not path or path == "unknown":
            return "unknown"

        try:
            return Path(path).name
        except (TypeError, ValueError):
            return str(path) if path else "unknown"

    def _safe_format_score(self, score) -> str:
        """Safely format score, handling undefined values."""
        try:
            return f"{float(score):.1f}"
        except (TypeError, ValueError):
            return "N/A"

    def _create_executive_summary(self, processing_results: dict, config: dict) -> dict:
        """Create executive summary data."""
        return {
            "job_name": config.get("job_name", "Bulk Auto-Delta Processing"),
            "total_unprocessed_found": processing_results.get("total_unprocessed", 0),
            "documents_processed": processing_results.get("processed_count", 0),
            "successful": processing_results.get("successful_count", 0),
            "failed": processing_results.get("failed_count", 0),
            "success_rate": processing_results.get("success_rate", 0),
            "processing_time": processing_results.get("processing_time", 0),
            "processing_rate": processing_results.get("processing_rate", 0),
            "total_entities": processing_results.get("total_entities", 0),
            "total_relationships": processing_results.get("total_relationships", 0),
            "avg_entities_per_doc": processing_results.get("avg_entities_per_doc", 0),
            "safety_limit_applied": processing_results.get("total_unprocessed", 0)
            > config.get("max_documents", 500),
            "max_documents": config.get("max_documents", 500),
            "num_actors": config.get("num_actors", 4),
        }

    def _extract_processing_details(self, document_results: list) -> dict:
        """Extract detailed processing information."""
        successful = [r for r in document_results if r.get("success")]
        failed = [r for r in document_results if not r.get("success")]

        return {
            "successful_documents": successful[:20],  # Limit for display
            "failed_documents": failed,
            "total_successful": len(successful),
            "total_failed": len(failed),
        }

    async def generate_report(
        self,
        processing_results: dict,
        document_results: list,
        config: dict,
    ) -> str:
        """Generate comprehensive bulk auto-delta report."""

        try:
            # Prepare template data
            executive_summary = self._create_executive_summary(processing_results, config)
            processing_details = self._extract_processing_details(document_results)

            # Template context
            template_context = {
                "generation_timestamp": datetime.now(),
                "executive_summary": executive_summary,
                "processing_details": processing_details,
                "document_results": document_results,
                "config": config,
            }

            # Render template
            template = self.template_env.get_template("bulk_auto_report.md.j2")
            report_content = template.render(**template_context)

            logger.info(
                "Generated bulk auto-delta report",
                total_docs=processing_results.get("processed_count", 0),
                successful=processing_results.get("successful_count", 0),
            )

            return report_content

        except Exception as e:
            logger.error(f"Failed to generate bulk auto-delta report: {e}")

            # Return basic fallback report
            return f"""# Bulk Auto-Delta Processing Report - Error

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC

## Error

Failed to generate full report: {e}

## Basic Results

- **Documents Processed:** {processing_results.get("processed_count", 0)}
- **Successful:** {processing_results.get("successful_count", 0)}
- **Failed:** {processing_results.get("failed_count", 0)}
- **Status:** Partial completion

Please check logs for detailed error information.
"""
