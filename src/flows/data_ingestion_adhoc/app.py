"""
Flow 1C: Ad-hoc Document/URL Ingestion

Process ad-hoc URLs or uploaded documents (PDF/DOCX/TXT/PPT/PPTX) through
the political monitoring pipeline with markdown conversion.
"""

import os

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Get defaults from environment variables
DEFAULT_MAX_ITEMS = int(os.getenv("FLOW1C_MAX_ITEMS", "10"))

# Define user interface form
adhoc_form = F.Model(
    F.Markdown(
        """
        # Political Monitoring Agent v0.2.0 - Ad-hoc URL Processing

        Process ad-hoc URLs through the political monitoring pipeline.

        **Features**:
        - Automatically fetches and extracts article content
        - Converts to markdown for processing
        - Integrates with Flow 1's proven pipeline
        - Updates knowledge graph with new entities

        **Safety Limit**: Maximum 10 URLs per run

        **Note**: Document upload (PDF/DOCX/TXT/PPT/PPTX) will be added in a future update.
        For now, please use URLs to web articles or pre-converted markdown files in Flow 1.
        """
    ),
    F.Errors(),
    F.Break(),
    # Job Configuration
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., Emergency EU Directive Analysis",
        value="Ad-hoc URL Processing",
    ),
    F.Break(),
    # URL Input
    F.Markdown("## URLs to Process"),
    F.InputText(
        label="URL 1",
        name="url1",
        placeholder="https://example.com/article-1",
    ),
    F.InputText(
        label="URL 2 (optional)",
        name="url2",
        placeholder="https://example.com/article-2",
    ),
    F.InputText(
        label="URL 3 (optional)",
        name="url3",
        placeholder="https://example.com/article-3",
    ),
    F.InputText(
        label="URL 4 (optional)",
        name="url4",
        placeholder="https://example.com/article-4",
    ),
    F.InputText(
        label="URL 5 (optional)",
        name="url5",
        placeholder="https://example.com/article-5",
    ),
    F.Break(),
    # Action Buttons
    F.Submit("Start Processing"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=adhoc_form,
    summary="Ad-hoc Document/URL Processing",
    description="Process ad-hoc URLs or uploaded documents (PDF/DOCX/TXT/PPT/PPTX) through the pipeline",
    version="0.2.0",
    author="political-monitoring@example.com",
    tags=["Politics", "Ad-hoc", "URLs", "Documents", "Flow 1C"],
)
async def process_adhoc(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch ad-hoc processing workflow."""

    # Enhanced validation with InputsError
    error = InputsError()

    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this processing run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Collect URLs from individual fields
    urls = []
    for i in range(1, 11):  # Support up to 10 URLs
        url_field = f"url{i}"
        url = inputs.get(url_field, "").strip()
        if url:
            # Basic URL validation
            if url.startswith("http://") or url.startswith("https://"):
                urls.append(url)
            else:
                error.add(**{url_field: "URL must start with http:// or https://"})

    # Validate that at least one URL is provided
    if not urls:
        error.add(url1="Please provide at least one URL to process")

    # Validate URL count
    if len(urls) > DEFAULT_MAX_ITEMS:
        error.add(url1=f"Number of URLs ({len(urls)}) exceeds maximum limit of {DEFAULT_MAX_ITEMS}")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Convert URLs list to newline-separated string for processor
    urls_text = "\n".join(urls)

    # Launch the ad-hoc processing workflow
    return Launch(
        request,
        "src.flows.data_ingestion_adhoc.processor:execute_adhoc_processing",
        inputs={
            "job_name": inputs["job_name"],
            "input_type": "urls",
            "urls": urls_text,
            "documents": [],
            "max_items": len(urls),
        },
    )


# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 1C monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow1c",
        "version": "0.2.0",
        "flow": "adhoc_ingestion",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class AdhocFlow:
    """Kodosumi deployment class for Flow 1C: Ad-hoc Processing."""

    pass


# Required for Kodosumi deployment
adhoc_app = AdhocFlow.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8007, reload=True)
