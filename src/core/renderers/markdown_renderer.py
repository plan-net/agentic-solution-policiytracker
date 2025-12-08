"""
Markdown Renderer for Kodosumi Integration.

Renders reports as markdown using Jinja2 templates, suitable for
display in the Kodosumi UI and other markdown-compatible systems.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from src.core.renderers.base_renderer import BaseRenderer

logger = logging.getLogger(__name__)


class MarkdownRenderer(BaseRenderer):
    """
    Markdown renderer using Jinja2 templates.

    Renders structured report data into markdown format, suitable for
    Kodosumi integration. Provides custom filters for formatting dates,
    escaping markdown special characters, and displaying priority indicators.

    Example:
        renderer = MarkdownRenderer(Path("templates"))
        output = await renderer.render(
            template_context={
                "week_label": "KW48/2025",
                "executive_summary": "...",
                "findings_by_category": {...},
            },
            template_name="weekly_digest.md.j2"
        )

    Attributes:
        template_env: Jinja2 environment for template loading
    """

    def __init__(
        self,
        template_dir: Path,
        auto_reload: bool = False,
    ):
        """
        Initialize the markdown renderer.

        Args:
            template_dir: Directory containing Jinja2 templates
            auto_reload: Whether to auto-reload templates (for development)
        """
        self.template_dir = template_dir
        self.template_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            auto_reload=auto_reload,
        )
        self._setup_filters()

    def _setup_filters(self) -> None:
        """Add custom Jinja2 filters."""
        self.template_env.filters["escape_md"] = self._escape_markdown
        self.template_env.filters["format_date"] = self._format_date
        self.template_env.filters["priority_emoji"] = self._priority_emoji
        self.template_env.filters["truncate_text"] = self._truncate_text

    @property
    def format_name(self) -> str:
        """Return the format name."""
        return "markdown"

    def get_content_type(self) -> str:
        """Return the MIME type."""
        return "text/markdown"

    async def render(
        self,
        template_context: dict[str, Any],
        template_name: str,
    ) -> str:
        """
        Render markdown report using Jinja2 template.

        Args:
            template_context: Dictionary with all template variables
            template_name: Name of the template file

        Returns:
            Rendered markdown string

        Raises:
            TemplateNotFound: If the template doesn't exist
        """
        # Validate context
        errors = self.validate_context(template_context)
        if errors:
            logger.warning(f"Template context validation errors: {errors}")

        try:
            template = self.template_env.get_template(template_name)
            return template.render(**template_context)
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            return self._generate_fallback_report(template_context)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return self._generate_fallback_report(template_context)

    def _generate_fallback_report(self, context: dict[str, Any]) -> str:
        """
        Generate a basic report if template fails.

        Provides a minimal but functional report when the template
        system encounters errors.

        Args:
            context: Template context dictionary

        Returns:
            Basic markdown report
        """
        week_label = context.get("week_label", "Unknown Week")
        week_start = context.get("week_start")
        week_end = context.get("week_end")
        executive_summary = context.get("executive_summary", "No summary available.")
        generated_at = context.get("generated_at", datetime.now())

        # Format dates
        if week_start and hasattr(week_start, "strftime"):
            start_str = week_start.strftime("%d %B")
        else:
            start_str = "Unknown"

        if week_end and hasattr(week_end, "strftime"):
            end_str = week_end.strftime("%d %B %Y")
        else:
            end_str = "Unknown"

        report_lines = [
            "# Weekly Regulatory Intelligence Digest",
            "",
            f"**{week_label}** ({start_str} - {end_str})",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            executive_summary,
            "",
            "---",
            "",
        ]

        # Add category sections
        findings_by_category = context.get("findings_by_category", {})
        summaries = context.get("summaries", {})

        category_titles = {
            "legislative": "1. Legislative & Regulatory Updates",
            "personnel": "2. Personnel Changes",
            "compliance": "3. Industry & Compliance Issues",
            "policy": "4. Government Policy Developments",
            "events": "5. Upcoming Events & Deadlines",
        }

        for category, title in category_titles.items():
            report_lines.append(f"## {title}")
            report_lines.append("")

            findings = findings_by_category.get(category, [])
            summary = summaries.get(category, "")

            if summary:
                report_lines.append(f"*{summary}*")
                report_lines.append("")

            if findings:
                for i, finding in enumerate(findings[:7], 1):
                    title = finding.get("title", finding.title if hasattr(finding, "title") else "")
                    content = finding.get("content", finding.content if hasattr(finding, "content") else "")
                    report_lines.append(f"### {i}. {title}")
                    report_lines.append(content)
                    report_lines.append("")
            else:
                report_lines.append("*No developments in this category this week.*")
                report_lines.append("")

            report_lines.append("---")
            report_lines.append("")

        # Add graph visualization if available
        graph_link = context.get("graph_visualization_link")
        entities_count = context.get("entities_count", 0)

        if graph_link:
            report_lines.extend([
                "## Entity Relationship Graph",
                "",
                f"**[Explore the knowledge graph for this report]({graph_link})**",
                "",
                f"*{entities_count} entities discovered across all categories.*",
                "",
                "---",
                "",
            ])

        # Footer
        if hasattr(generated_at, "strftime"):
            gen_str = generated_at.strftime("%Y-%m-%d %H:%M")
        else:
            gen_str = str(generated_at)

        report_lines.extend([
            f"*Generated: {gen_str} | Source: Graphiti Knowledge Graph*",
        ])

        return "\n".join(report_lines)

    @staticmethod
    def _escape_markdown(text: str) -> str:
        """
        Escape markdown special characters.

        Args:
            text: Text to escape

        Returns:
            Text with special characters escaped
        """
        if not text:
            return ""

        replacements = {
            "_": r"\_",
            "*": r"\*",
            "[": r"\[",
            "]": r"\]",
            "#": r"\#",
            "`": r"\`",
            "|": r"\|",
        }

        for char, escaped in replacements.items():
            text = text.replace(char, escaped)

        return text

    @staticmethod
    def _format_date(
        dt: Optional[datetime],
        fmt: str = "%d %B %Y",
    ) -> str:
        """
        Format datetime for display.

        Args:
            dt: Datetime to format
            fmt: strftime format string

        Returns:
            Formatted date string or "Not specified"
        """
        if not dt:
            return "Not specified"
        if hasattr(dt, "strftime"):
            return dt.strftime(fmt)
        return str(dt)

    @staticmethod
    def _priority_emoji(priority: str) -> str:
        """
        Return emoji for priority level.

        Args:
            priority: Priority level string

        Returns:
            Corresponding emoji
        """
        emojis = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }
        if hasattr(priority, "value"):
            priority = priority.value
        return emojis.get(str(priority).lower(), "⚪")

    @staticmethod
    def _truncate_text(text: str, length: int = 200) -> str:
        """
        Truncate text to specified length.

        Args:
            text: Text to truncate
            length: Maximum length

        Returns:
            Truncated text with ellipsis if needed
        """
        if not text:
            return ""
        if len(text) <= length:
            return text
        return text[: length - 3] + "..."
