"""Weekly Report SDK Flow - Kodosumi Endpoint.

Generates a Weekly Regulatory Intelligence Digest using Claude's native
tool-use capabilities via the MCP protocol.

This implementation replaces the LangGraph-based weekly_digest_v2 with
a simpler, single-agent approach using Claude's agentic loop.
"""

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

from src.flows.weekly_digest_v2.date_resolver import DateResolutionError, DateResolver

app = ServeAPI()

# Define user interface form with model selection
weekly_report_form = F.Model(
    F.Markdown(
        """
        # Weekly Regulatory Intelligence Digest

        Generate a comprehensive weekly report on EU and German regulatory developments
        using Claude's advanced reasoning capabilities.

        The report covers:

        - **Legislative & Regulatory Updates**: New laws, directives, and guidance
        - **Personnel Changes**: Ministry and regulatory body appointments
        - **Industry & Compliance Issues**: Enforcement actions and penalties
        - **Government Policy Developments**: Initiatives and strategies
        - **Upcoming Events & Deadlines**: Important dates to watch

        Enter a calendar week (e.g., **KW48**) or Monday date (e.g., **2025-11-25**).
        """
    ),
    F.Errors(),
    F.Break(),
    # Week Input
    F.InputText(
        label="Week Selection",
        name="week_input",
        placeholder="KW48 or 2025-11-25",
        value="",
    ),
    F.Break(),
    F.Markdown(
        """
        **Supported formats:**
        - `KW48` - Calendar week 48 of current year
        - `KW48/2025` - Calendar week 48 of 2025
        - `2025-11-25` - Specific Monday date (ISO format)
        - `25.11.2025` - Specific Monday date (German format)
        - *Leave empty for previous week*
        """
    ),
    F.Break(),
    # Model Selection
    F.Select(
        label="Claude Model",
        name="claude_model",
        value="claude-sonnet-4-20250514",
        option=[
            F.InputOption(
                name="claude-sonnet-4-20250514",
                label="Claude Sonnet 4 (Recommended - Fast & Cost-effective)"
            ),
            F.InputOption(
                name="claude-opus-4-20250514",
                label="Claude Opus 4 (Higher quality - Slower & More expensive)"
            ),
        ],
    ),
    F.Break(),
    # Include Events checkbox
    F.Checkbox(
        label="Include Forward-Looking Events",
        name="include_events",
        value=True,
        option="Include upcoming deadlines and events (next 30-90 days)",
    ),
    F.Break(),
    # Action Buttons
    F.Submit("Generate Report"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=weekly_report_form,
    summary="Weekly Regulatory Intelligence Digest (Claude SDK)",
    description="Generate a comprehensive weekly briefing using Claude's native tool-use capabilities",
    version="3.0.0",
    author="political-monitoring@example.com",
    tags=["Politics", "Regulatory Intelligence", "Weekly Report", "Claude SDK", "MCP"],
)
async def generate_weekly_report(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch weekly report workflow."""

    # Validation
    error = InputsError()

    week_input = inputs.get("week_input", "").strip()

    # Validate week input if provided
    if week_input:
        try:
            resolver = DateResolver()
            resolved = resolver.resolve(week_input)
            # Store resolved dates for the processor
            inputs["resolved_week_start"] = resolved["week_start"].isoformat()
            inputs["resolved_week_end"] = resolved["week_end"].isoformat()
            inputs["resolved_week_label"] = resolved["week_label"]
            inputs["resolved_week_number"] = resolved["week_number"]
            inputs["resolved_year"] = resolved["year"]
        except DateResolutionError as e:
            error.add(
                week_input=f"Invalid week format: {e}. Use KW48, KW48/2025, or 2025-11-25."
            )
        except Exception as e:
            error.add(week_input=f"Error parsing week: {e}")

    # Validate model selection
    claude_model = inputs.get("claude_model", "claude-sonnet-4-20250514")
    valid_models = ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]
    if claude_model not in valid_models:
        error.add(claude_model="Invalid model selected.")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Launch the weekly report workflow
    return Launch(
        request,
        "src.flows.weekly_report_sdk.processor:execute_weekly_report",
        inputs={
            "week_input": week_input,
            "claude_model": claude_model,
            "include_events": bool(inputs.get("include_events", True)),
            "resolved_week_start": inputs.get("resolved_week_start"),
            "resolved_week_end": inputs.get("resolved_week_end"),
            "resolved_week_label": inputs.get("resolved_week_label"),
            "resolved_week_number": inputs.get("resolved_week_number"),
            "resolved_year": inputs.get("resolved_year"),
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for weekly report SDK flow."""
    return {
        "status": "healthy",
        "service": "weekly-report-sdk",
        "version": "3.0.0",
        "flow": "weekly_report_sdk",
        "features": [
            "claude-native-tools",
            "mcp-knowledge-graph",
            "model-selection",
            "agentic-loop",
        ],
    }


# Info endpoint
@app.get("/info")
async def info():
    """Information endpoint describing the SDK capabilities."""
    return {
        "name": "Weekly Regulatory Intelligence Digest (Claude SDK)",
        "description": "Weekly report generation using Claude's native tool-use capabilities",
        "version": "3.0.0",
        "models": [
            {
                "id": "claude-sonnet-4-20250514",
                "name": "Claude Sonnet 4",
                "description": "Fast and cost-effective for daily reports",
                "default": True,
            },
            {
                "id": "claude-opus-4-20250514",
                "name": "Claude Opus 4",
                "description": "Higher quality reasoning for important reports",
                "default": False,
            },
        ],
        "categories": [
            "Legislative & Regulatory Updates",
            "Personnel Changes",
            "Industry & Compliance Issues",
            "Government Policy Developments",
            "Upcoming Events & Deadlines",
        ],
        "tools": [
            "search_knowledge_graph",
            "analyze_query",
            "get_entity_info",
            "find_relationships",
            "graph_statistics",
        ],
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class WeeklyReportSDKFlow:
    """Kodosumi deployment class for Weekly Report SDK Flow."""

    pass


# Required for Kodosumi deployment
fast_app = WeeklyReportSDKFlow.bind()

# For local debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8012, reload=True)
