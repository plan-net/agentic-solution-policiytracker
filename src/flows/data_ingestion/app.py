"""
Flow 1: Data Ingestion - Kodosumi endpoint

Professional document ingestion interface with comprehensive validation,
health monitoring, and Ray deployment configuration.
"""

from pathlib import Path

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define rich user interface form
data_ingestion_form = F.Model(
    F.Markdown(
        """
        # Political Monitoring Agent v0.2.0 - Data Ingestion Flow

        Process political documents into temporal knowledge graph with entity extraction,
        relationship mapping, and community detection. Built on Graphiti for advanced
        temporal analysis and political intelligence insights.
        """
    ),
    F.Errors(),  # Display validation errors
    F.Break(),  # Visual separator
    # Job Configuration
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., EU AI Act Analysis, Weekly Political Review",
        value="Document Ingestion",
    ),
    # Data Management
    F.Checkbox(
        label="Clear Existing Data",
        name="clear_data",
        value=False,
        option="⚠️ Clear graph database and reingest all documents (irreversible)",
    ),
    # Processing Configuration
    F.InputNumber(
        label="Document Limit",
        name="document_limit",
        min_value=1,
        max_value=100,
        step=1,
        value=10,
        placeholder="Maximum documents to process in this run",
    ),
    # Action Buttons
    F.Submit("Start Ingestion"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=data_ingestion_form,
    summary="Political Document Ingestion",
    description="Ingest political documents into temporal knowledge graph with entity extraction and community detection",
    version="0.2.0",
    author="political-monitoring@example.com",
    tags=["Politics", "Document Processing", "Knowledge Graph", "Graphiti", "Flow 1"],
)
async def ingest_documents(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch document ingestion workflow."""

    # Enhanced validation with InputsError
    error = InputsError()

    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this ingestion run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Source path is fixed to policy directory
    source_path_str = "data/input/policy/"
    source_path = Path(source_path_str)

    if not source_path.exists():
        error.add(source_path=f"Default policy directory does not exist: {source_path_str}")
    else:
        # Check for supported documents
        doc_count = 0
        for pattern in ["**/*.txt", "**/*.md"]:
            doc_count += len(list(source_path.rglob(pattern.split("/", 1)[1])))

        if doc_count == 0:
            error.add(source_path="No .txt or .md documents found in policy directory")

    # Document limit validation
    try:
        document_limit = int(inputs.get("document_limit", 10))
        if document_limit < 1:
            error.add(document_limit="Document limit must be at least 1")
        elif document_limit > 100:
            error.add(document_limit="Document limit cannot exceed 100")
    except (ValueError, TypeError):
        error.add(document_limit="Document limit must be a valid number")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Launch the document ingestion workflow
    return Launch(
        request,
        "src.flows.data_ingestion.data_ingestion_analyzer:execute_ingestion",
        inputs={
            "job_name": inputs["job_name"],
            "source_path": source_path_str,
            "document_limit": document_limit,
            "clear_data": bool(inputs.get("clear_data", False)),
            "enable_communities": False,  # Communities now built manually via just command
        },
    )


# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 1 monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow1",
        "version": "0.2.0",
        "flow": "data_ingestion",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class DataIngestionFlow:
    """Kodosumi deployment class for Flow 1: Data Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = DataIngestionFlow.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)
