# app.py - Kodosumi Endpoint for Political Monitoring Agent
import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define rich user interface form
analysis_form = F.Model(
    F.Markdown(
        """
    # Political Monitoring Agent v0.1.0

    Analyze political documents for relevance, priority, and topics using distributed AI processing.
    Upload documents and get comprehensive analysis reports with confidence scoring.
    """
    ),
    F.Errors(),  # Display validation errors
    F.Break(),  # Visual separator
    # Job Configuration
    F.InputText(
        label="Job Name", name="job_name", placeholder="e.g., Weekly Policy Review, Brexit Analysis"
    ),
    # Analysis Parameters
    F.InputNumber(
        label="Priority Threshold (%)",
        name="priority_threshold",
        min_value=0,
        max_value=100,
        step=5,
        value=70,
        placeholder="Minimum priority score for inclusion",
    ),
    # Processing Options
    F.Checkbox(
        label="Include Low Confidence Results",
        name="include_low_confidence",
        value=False,
        option="Include documents with confidence scores below 80%",
    ),
    F.Checkbox(
        label="Enable Topic Clustering",
        name="clustering_enabled",
        value=True,
        option="Group documents by semantic similarity into topic clusters",
    ),
    # Storage Configuration
    F.Select(
        label="Storage Mode",
        name="storage_mode",
        option=[
            F.InputOption(label="Local Files", name="local"),
            F.InputOption(label="Azure Blob Storage", name="azure"),
        ],
        value="local",
    ),
    # Action Buttons
    F.Submit("Start Analysis"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=analysis_form,
    summary="Political Document Analysis",
    description="Comprehensive political document monitoring and analysis using distributed AI",
    version="0.1.0",
    author="political-monitoring@example.com",
    tags=["Politics", "Document Analysis", "AI", "Monitoring"],
)
async def enter(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch political analysis."""

    # Validate inputs
    error = InputsError()

    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this analysis")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Storage mode validation
    storage_mode = inputs.get("storage_mode", "local")
    if storage_mode not in ["local", "azure"]:
        error.add(storage_mode="Please select a valid storage mode")

    # Validate numeric ranges - convert strings to numbers
    try:
        priority_threshold = float(inputs.get("priority_threshold", 70))
        if priority_threshold < 0 or priority_threshold > 100:
            error.add(priority_threshold="Priority threshold must be between 0 and 100")
    except (ValueError, TypeError):
        error.add(priority_threshold="Priority threshold must be a valid number")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Launch the political analysis workflow
    return Launch(
        request,
        "src.political_analyzer:execute_analysis",  # Path to entrypoint function
        inputs={
            "job_name": inputs["job_name"],
            "priority_threshold": priority_threshold,
            "include_low_confidence": bool(inputs.get("include_low_confidence", False)),
            "clustering_enabled": bool(inputs.get("clustering_enabled", True)),
            "storage_mode": inputs.get("storage_mode", "local"),
        },
    )


# Health check endpoint for Kodosumi
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "political-monitoring-agent", "version": "0.1.0"}


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class PoliticalMonitoringAgent:
    """Kodosumi deployment class for Political Monitoring Agent."""

    pass


# Required for Kodosumi deployment
fast_app = PoliticalMonitoringAgent.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)
