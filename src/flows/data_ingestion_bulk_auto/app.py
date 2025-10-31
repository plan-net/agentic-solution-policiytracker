"""
Flow 1B: Bulk Auto-Delta Document Ingestion

Automatically detects and processes unprocessed documents by comparing
processed_documents.json with current folder state.

For Airflow orchestration - no file list parameters needed.
"""

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define user interface form
bulk_auto_form = F.Model(
    F.Markdown(
        """
        # Political Monitoring Agent v0.2.0 - Bulk Auto-Delta Processing

        Automatically detects and processes unprocessed documents by comparing
        the document tracking file with current folder contents. No file selection needed.

        **Safety Limit**: Maximum 500 documents per run.
        """
    ),
    F.Errors(),
    F.Break(),
    # Job Configuration
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., Airflow Auto Orchestration",
        value="Bulk Auto-Delta Processing",
    ),
    # Processing Configuration
    F.InputNumber(
        label="Maximum Documents",
        name="max_documents",
        min_value=1,
        max_value=500,
        step=1,
        value=500,
        placeholder="Safety limit: maximum documents to process",
    ),
    # Action Buttons
    F.Submit("Start Processing"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=bulk_auto_form,
    summary="Bulk Auto-Delta Document Processing",
    description="Automatically detect and process unprocessed documents (max 500 per run)",
    version="0.2.0",
    author="political-monitoring@example.com",
    tags=["Politics", "Bulk Processing", "Auto-Delta", "Flow 1B"],
)
async def process_bulk_auto(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch bulk auto-delta processing."""

    # Enhanced validation with InputsError
    error = InputsError()

    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this processing run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Max documents validation
    try:
        max_documents = int(inputs.get("max_documents", 500))
        if max_documents < 1:
            error.add(max_documents="Maximum documents must be at least 1")
        elif max_documents > 500:
            error.add(max_documents="Maximum documents cannot exceed 500 (safety limit)")
    except (ValueError, TypeError):
        error.add(max_documents="Maximum documents must be a valid number")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Launch the bulk auto-delta processing workflow
    return Launch(
        request,
        "src.flows.data_ingestion_bulk_auto.processor:execute_bulk_auto_processing",
        inputs={
            "job_name": inputs["job_name"],
            "max_documents": max_documents,
        },
    )


# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 1B monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow1b",
        "version": "0.2.0",
        "flow": "bulk_auto_delta_ingestion",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class BulkAutoFlow:
    """Kodosumi deployment class for Flow 1B: Bulk Auto-Delta Processing."""

    pass


# Required for Kodosumi deployment
bulk_auto_app = BulkAutoFlow.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8006, reload=True)
