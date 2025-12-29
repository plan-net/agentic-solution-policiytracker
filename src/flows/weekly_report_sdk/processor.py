"""Processor for the Weekly Report SDK flow.

This module contains the main workflow logic that is called by Kodosumi's Launch().
It initializes the WeeklyReportAgent, generates the report, and saves it to the Reports API.
"""

import logging
from datetime import datetime

import kodosumi.core as core
from kodosumi.core import Tracer
from neo4j import AsyncGraphDatabase

from src.config import settings
from src.flows.weekly_digest_v2.date_resolver import DateResolver
from src.graph_viz.reports import (
    CreateReportRequest,
    ReportsService,
    ReportStatus,
    ReportType,
)

from .agent import WeeklyReportAgent

logger = logging.getLogger(__name__)


async def execute_weekly_report(inputs: dict, tracer: Tracer) -> core.response.Markdown:
    """Execute the weekly report generation workflow.

    This function is called by Kodosumi's Launch() mechanism.

    Args:
        inputs: Validated form inputs containing:
            - week_input: Raw week input string
            - claude_model: Selected Claude model
            - include_events: Whether to include events section
            - resolved_*: Pre-resolved date values
        tracer: Kodosumi tracer for progress updates

    Returns:
        Generated report wrapped in core.response.Markdown()
    """
    await tracer.markdown("# Weekly Report Generation\n\nInitializing...")

    # Extract inputs
    claude_model = inputs.get("claude_model", "claude-sonnet-4-20250514")
    include_events = inputs.get("include_events", True)

    # Resolve dates if not already resolved
    if inputs.get("resolved_week_start"):
        week_start = datetime.fromisoformat(inputs["resolved_week_start"])
        week_end = datetime.fromisoformat(inputs["resolved_week_end"])
        week_label = inputs["resolved_week_label"]
    else:
        # Resolve from week_input
        resolver = DateResolver()
        week_input = inputs.get("week_input", "")
        resolved = resolver.resolve(week_input)
        week_start = resolved["week_start"]
        week_end = resolved["week_end"]
        week_label = resolved["week_label"]

    await tracer.markdown(f"""
## Configuration

- **Week**: {week_label}
- **Period**: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}
- **Model**: {claude_model}
- **Include Events**: {include_events}

---

## Research Progress

""")

    # Initialize the agent
    try:
        agent = WeeklyReportAgent(
            model=claude_model,
            max_turns=30,
        )
        await tracer.markdown("✅ Agent initialized\n\n")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        await tracer.markdown(f"❌ Failed to initialize agent: {e}")
        return core.response.Markdown(f"# Error\n\nFailed to initialize agent: {e}")

    # Generate the report
    try:
        await tracer.markdown("**Researching knowledge graph...**\n\n")

        result = await agent.generate_report(
            week_start=week_start,
            week_end=week_end,
            week_label=week_label,
            include_events=include_events,
            tracer=tracer,
        )

        report_content = result["report_content"]
        metadata = result["metadata"]
        tool_calls = result["tool_calls"]

        await tracer.markdown(f"""
---

## Generation Complete

- **Turns**: {metadata.get('turns', 'N/A')}
- **Tool Calls**: {metadata.get('tool_calls_count', 0)}
- **Model**: {metadata.get('model', claude_model)}

""")

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        await tracer.markdown(f"\n\n❌ Report generation failed: {e}")
        return core.response.Markdown(f"# Error\n\nReport generation failed: {e}")

    finally:
        # Cleanup
        await agent.close()

    # Save to Reports API
    report_id = None
    try:
        await tracer.markdown("**Saving report to database...**\n\n")

        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        )

        try:
            reports_service = ReportsService(driver)

            # Create the report
            report = await reports_service.create_report(
                CreateReportRequest(
                    title=f"Weekly Intelligence - {week_label}",
                    report_type=ReportType.WEEKLY,
                    date_range_start=week_start.strftime("%Y-%m-%d"),
                    date_range_end=week_end.strftime("%Y-%m-%d"),
                    options={
                        "model": claude_model,
                        "include_events": include_events,
                        "tool_calls_count": len(tool_calls),
                        "turns": metadata.get("turns", 0),
                    },
                )
            )

            if report:
                report_id = report.report_id

                # Update with content and mark as complete
                from src.graph_viz.reports import UpdateReportRequest

                await reports_service.update_report(
                    report_id,
                    UpdateReportRequest(
                        content=report_content,
                        status=ReportStatus.COMPLETE,
                    ),
                )

                await tracer.markdown(f"✅ Report saved with ID: `{report_id}`\n\n")
            else:
                await tracer.markdown("⚠️ Failed to save report to database\n\n")

        finally:
            await driver.close()

    except Exception as e:
        logger.error(f"Failed to save report: {e}", exc_info=True)
        await tracer.markdown(f"⚠️ Failed to save report: {e}\n\n")

    # Add footer with metadata
    footer = f"""

---

*Generated by Weekly Report SDK v3.0.0*
*Model: {claude_model} | Turns: {metadata.get('turns', 'N/A')} | Tool Calls: {len(tool_calls)}*
"""

    if report_id:
        footer += f"\n*Report ID: {report_id}*"

    full_report = report_content + footer

    await tracer.markdown("---\n\n## Final Report\n\n" + report_content[:500] + "...\n\n*(See full report below)*")

    return core.response.Markdown(full_report)
