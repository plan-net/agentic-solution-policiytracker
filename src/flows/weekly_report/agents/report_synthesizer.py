"""
Report Synthesizer Agent for Weekly Report.

Combines findings from all category agents into a cohesive executive-ready
weekly briefing with cross-references and priority ordering.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader
from langchain_core.language_models import BaseLLM
from langchain_core.messages import HumanMessage, SystemMessage

from src.chat.observability.langwatch_config import langwatch_config

from ..models import Finding, FindingPriority, ReportCategory, ReportMetadata
from ..prompts.category_prompts import SYNTHESIZER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ReportSynthesizerAgent:
    """
    Synthesizes category findings into a final weekly report.

    Responsibilities:
    - Generate executive summary
    - Cross-reference findings across categories
    - Priority ordering within sections
    - Render final report using Jinja2 template
    """

    def __init__(
        self,
        llm: BaseLLM,
        template_dir: Optional[str] = None,
    ):
        self.llm = llm
        self.system_prompt = SYNTHESIZER_SYSTEM_PROMPT

        # Set up Jinja2 environment
        if template_dir is None:
            template_dir = str(
                Path(__file__).parent.parent / "templates"
            )
        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.template_env.filters["escape_md"] = self._escape_markdown
        self.template_env.filters["format_date"] = self._format_date
        self.template_env.filters["priority_emoji"] = self._priority_emoji

    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters."""
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

    def _format_date(self, date: Optional[datetime], format_str: str = "%d %B %Y") -> str:
        """Format datetime for display."""
        if not date:
            return "Not specified"
        return date.strftime(format_str)

    def _priority_emoji(self, priority: str) -> str:
        """Return emoji for priority level."""
        emojis = {
            "high": "🔴",
            "medium": "🟡",
            "low": "🟢",
        }
        return emojis.get(priority.lower() if isinstance(priority, str) else priority.value, "⚪")

    @langwatch_config.trace(name="report_synthesis")
    async def synthesize(
        self,
        week_start: datetime,
        week_end: datetime,
        week_label: str,
        legislative_findings: list[Finding],
        personnel_findings: list[Finding],
        compliance_findings: list[Finding],
        policy_findings: list[Finding],
        events_findings: list[Finding],
        legislative_summary: str = "",
        personnel_summary: str = "",
        compliance_summary: str = "",
        policy_summary: str = "",
        events_summary: str = "",
    ) -> dict[str, Any]:
        """
        Synthesize all category findings into a final report.

        Returns:
            Dictionary with:
            - executive_summary: str
            - report_sections: dict[str, str]
            - final_report: str
            - metadata: ReportMetadata
        """
        start_time = datetime.now()

        # Collect all findings
        all_findings = {
            ReportCategory.LEGISLATIVE: legislative_findings,
            ReportCategory.PERSONNEL: personnel_findings,
            ReportCategory.COMPLIANCE: compliance_findings,
            ReportCategory.POLICY: policy_findings,
            ReportCategory.EVENTS: events_findings,
        }

        summaries = {
            ReportCategory.LEGISLATIVE: legislative_summary,
            ReportCategory.PERSONNEL: personnel_summary,
            ReportCategory.COMPLIANCE: compliance_summary,
            ReportCategory.POLICY: policy_summary,
            ReportCategory.EVENTS: events_summary,
        }

        # Generate executive summary
        executive_summary = await self._generate_executive_summary(
            all_findings, week_start, week_end
        )

        # Render report sections
        report_sections = self._render_sections(all_findings, summaries)

        # Build template context
        template_context = {
            "week_label": week_label,
            "week_start": week_start,
            "week_end": week_end,
            "generated_at": datetime.now(),
            "executive_summary": executive_summary,
            "legislative_section": report_sections.get("legislative", ""),
            "personnel_section": report_sections.get("personnel", ""),
            "compliance_section": report_sections.get("compliance", ""),
            "policy_section": report_sections.get("policy", ""),
            "events_section": report_sections.get("events", ""),
            "total_findings": sum(len(f) for f in all_findings.values()),
            "high_priority_count": sum(
                1 for findings in all_findings.values()
                for f in findings if f.priority == FindingPriority.HIGH
            ),
            "forward_looking_count": sum(
                1 for findings in all_findings.values()
                for f in findings if f.forward_looking
            ),
        }

        # Render final report
        try:
            template = self.template_env.get_template("weekly_report.md.j2")
            final_report = template.render(**template_context)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            final_report = self._generate_fallback_report(template_context)

        # Create metadata
        processing_time = (datetime.now() - start_time).total_seconds()
        iso_year, iso_week, _ = week_start.isocalendar()

        metadata = ReportMetadata(
            week_number=iso_week,
            year=iso_year,
            week_label=week_label,
            week_start=week_start,
            week_end=week_end,
            generated_at=datetime.now(),
            total_findings=template_context["total_findings"],
            categories_completed=sum(1 for f in all_findings.values() if f),
            processing_time_seconds=processing_time,
        )

        return {
            "executive_summary": executive_summary,
            "report_sections": report_sections,
            "final_report": final_report,
            "metadata": metadata,
        }

    @langwatch_config.trace(name="llm_executive_summary")
    async def _generate_executive_summary(
        self,
        all_findings: dict[ReportCategory, list[Finding]],
        week_start: datetime,
        week_end: datetime,
    ) -> str:
        """Generate executive summary using LLM."""
        # Collect high-priority findings
        high_priority = []
        for category, findings in all_findings.items():
            for finding in findings:
                if finding.priority == FindingPriority.HIGH:
                    high_priority.append((category, finding))

        # If no high priority, use top findings from each category
        if not high_priority:
            for category, findings in all_findings.items():
                if findings:
                    high_priority.append((category, findings[0]))

        if not high_priority:
            return (
                f"Week {week_start.strftime('%d %B')} - {week_end.strftime('%d %B %Y')}: "
                "No significant regulatory developments identified in the monitored sources."
            )

        # Format findings for LLM
        findings_text = "\n".join([
            f"- [{cat.value.upper()}] {f.title}: {f.content[:100]}..."
            for cat, f in high_priority[:10]
        ])

        prompt = f"""Generate an executive summary (3-4 sentences, under 100 words) for the Weekly Regulatory Intelligence Digest.

Week: {week_start.strftime('%d %B')} - {week_end.strftime('%d %B %Y')}

Key Findings:
{findings_text}

Requirements:
- Lead with the single most impactful development
- Include 2-3 other significant items
- Mention any urgent deadlines if present
- Professional, neutral tone
- No speculation

Executive Summary:"""

        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt),
            ]
            response = await self.llm.ainvoke(messages)
            summary = response.content if hasattr(response, "content") else str(response)

            # Clean up response
            summary = summary.strip()
            if summary.startswith("Executive Summary:"):
                summary = summary.replace("Executive Summary:", "").strip()

            return summary

        except Exception as e:
            logger.warning(f"LLM summary generation failed: {e}")
            # Fallback summary
            return (
                f"Week of {week_start.strftime('%d %B %Y')}: "
                f"This digest covers {sum(len(f) for f in all_findings.values())} developments "
                "across legislative, personnel, compliance, policy, and upcoming events categories. "
                f"Key areas include {', '.join([cat.value for cat, _ in high_priority[:3]])}."
            )

    def _render_sections(
        self,
        all_findings: dict[ReportCategory, list[Finding]],
        summaries: dict[ReportCategory, str],
    ) -> dict[str, str]:
        """Render markdown sections for each category."""
        sections = {}

        for category, findings in all_findings.items():
            if not findings:
                sections[category.value] = "*No developments in this category this week.*"
                continue

            # Build section content
            lines = []

            # Add summary if available
            summary = summaries.get(category, "")
            if summary:
                lines.append(f"*{summary}*\n")

            # Add findings
            for i, finding in enumerate(findings[:7], 1):  # Top 7 per category
                priority_emoji = self._priority_emoji(finding.priority)

                lines.append(f"### {i}. {finding.title}")
                lines.append(f"{finding.content}")

                # Add metadata line
                metadata_parts = []
                if finding.date:
                    metadata_parts.append(f"Date: {finding.date.strftime('%d %B %Y')}")
                if finding.source:
                    metadata_parts.append(f"Source: {finding.source}")
                if finding.forward_looking:
                    metadata_parts.append("🔮 Forward-looking")

                if metadata_parts:
                    lines.append(f"*{' | '.join(metadata_parts)}*")

                lines.append("")  # Blank line between findings

            sections[category.value] = "\n".join(lines)

        return sections

    def _generate_fallback_report(self, context: dict[str, Any]) -> str:
        """Generate a basic report if template fails."""
        return f"""# Weekly Regulatory Intelligence Digest

**{context['week_label']}** ({context['week_start'].strftime('%d %B')} - {context['week_end'].strftime('%d %B %Y')})

---

## Executive Summary

{context['executive_summary']}

---

## 1. Legislative & Regulatory Updates

{context.get('legislative_section', 'No data available.')}

---

## 2. Personnel Changes

{context.get('personnel_section', 'No data available.')}

---

## 3. Industry & Compliance Issues

{context.get('compliance_section', 'No data available.')}

---

## 4. Government Policy Developments

{context.get('policy_section', 'No data available.')}

---

## 5. Upcoming Events & Deadlines

{context.get('events_section', 'No data available.')}

---

*Generated: {context['generated_at'].strftime('%Y-%m-%d %H:%M')} | Source: Graphiti Knowledge Graph*
*Total Findings: {context['total_findings']} | High Priority: {context['high_priority_count']} | Forward-looking: {context['forward_looking_count']}*
"""
