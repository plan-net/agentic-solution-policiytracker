"""
Weekly Digest v2 Processor - Kodosumi Entry Point.

Provides the entry point function for Kodosumi workflow execution.
Called by the Launch mechanism from app.py.
"""

import logging
from pathlib import Path
from typing import Any

from kodosumi import core
from kodosumi.core import Tracer

from src.chat.observability.langwatch_config import langwatch_config
from src.core.config.report_config import ReportConfig
from src.flows.weekly_digest_v2.agents.orchestrator import ReportOrchestrator

logger = logging.getLogger(__name__)

# Initialize LangWatch at module load time to ensure it's ready before any traces
# This is critical for the @langwatch_config.trace decorator to work properly
langwatch_config.initialize()


@langwatch_config.trace(name="weekly_digest_v2_workflow")
async def execute_weekly_digest(inputs: dict[str, Any], tracer: Tracer):
    """
    Entry point for Kodosumi workflow execution.

    This function is called by Kodosumi's Launch mechanism.
    It initializes the orchestrator and runs the workflow.

    Args:
        inputs: Dictionary containing:
            - week_input: User-provided week input (KW48 or date)
            - include_events: Whether to include events category
            - resolved_*: Pre-resolved date information from app.py
        tracer: Kodosumi tracer for UI updates

    Returns:
        Markdown response containing the final report
    """
    # Ensure LangWatch is initialized (idempotent - safe to call multiple times)
    langwatch_config.initialize()

    logger.info(f"Starting Weekly Digest v2 workflow with inputs: {inputs}")

    try:
        # Load report configuration
        config_dir = Path(__file__).parent / "config"
        config_path = config_dir / "weekly_digest.yaml"

        report_config = ReportConfig.load(config_path)
        logger.info(f"Loaded report config: {report_config.report_type}")

        # Create orchestrator
        orchestrator = ReportOrchestrator(
            report_config=report_config,
            tracer=tracer,
            config_dir=config_dir,
        )

        # Build resolved dates dict if pre-resolved
        resolved_dates = None
        if inputs.get("resolved_week_start"):
            resolved_dates = {
                "week_start": inputs.get("resolved_week_start"),
                "week_end": inputs.get("resolved_week_end"),
                "week_label": inputs.get("resolved_week_label"),
                "week_number": inputs.get("resolved_week_number"),
                "year": inputs.get("resolved_year"),
            }

        # Execute workflow
        final_report = await orchestrator.run(
            week_input=inputs.get("week_input", ""),
            include_events=inputs.get("include_events", True),
            resolved_dates=resolved_dates,
        )

        logger.info("Weekly Digest v2 workflow completed successfully")
        return core.response.Markdown(final_report)

    except Exception as e:
        logger.exception(f"Weekly Digest v2 workflow failed: {e}")
        error_report = f"""# Weekly Regulatory Intelligence Digest

## Report Generation Failed

An error occurred while generating the report:

**Error:** {e}

Please try again or contact support if the problem persists.
"""
        return core.response.Markdown(error_report)
