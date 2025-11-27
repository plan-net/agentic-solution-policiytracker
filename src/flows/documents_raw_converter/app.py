"""
Flow 1D: Raw Document Auto-Conversion

Kodosumi endpoint for converting raw documents (PDF, DOC, DOCX, PPT, PPTX)
to markdown format with policy-compatible metadata.
"""

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define user interface form
raw_converter_form = F.Model(
    F.Markdown(
        """
        # Political Monitoring Agent v0.2.0 - Raw Document Conversion + Graphiti Processing

        Automatically converts raw documents (PDF, DOC, DOCX, PPT, PPTX) to markdown format
        with policy-compatible metadata, and optionally processes them through Graphiti for
        knowledge graph extraction using parallel Ray actors.

        **Supported Formats**: PDF, DOC, DOCX, PPT, PPTX

        **Features:**
        - Auto-detection of unprocessed documents
        - Policy-compatible metadata generation
        - Optional Graphiti knowledge graph extraction
        - Parallel processing with Ray actors
        - Entity and relationship extraction
        """
    ),
    F.Errors(),
    F.Break(),
    # Job Configuration
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., Weekly Document Conversion",
        value="Raw Document Auto-Conversion + Graphiti",
    ),
    F.InputText(
        label="Source Directory",
        name="raw_docs_dir",
        placeholder="Path to raw documents",
        value="data/input/documents_raw",
    ),
    F.InputText(
        label="Output Directory",
        name="output_dir",
        placeholder="Path for converted markdown files",
        value="data/input/documents_md",
    ),
    F.Checkbox(
        label="Graphiti Processing",
        name="enable_graphiti",
        value=True,
        option="✅ Process converted documents through Graphiti for knowledge graph extraction",
    ),
    # Action Buttons
    F.Submit("Start Processing"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=raw_converter_form,
    summary="Raw Document Auto-Conversion",
    description="Convert raw documents to markdown with policy-compatible metadata",
    version="0.2.0",
    author="political-monitoring@example.com",
    tags=["Documents", "Conversion", "Markdown", "Flow 1D"],
)
async def process_raw_documents(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch raw document conversion."""

    # Enhanced validation with InputsError
    error = InputsError()

    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this conversion run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    if not inputs.get("raw_docs_dir"):
        error.add(raw_docs_dir="Please provide a source directory path")

    if not inputs.get("output_dir"):
        error.add(output_dir="Please provide an output directory path")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Launch the raw document conversion workflow
    return Launch(
        request,
        "src.flows.documents_raw_converter.processor:execute_raw_document_conversion",
        inputs={
            "job_name": inputs["job_name"],
            "raw_docs_dir": inputs["raw_docs_dir"],
            "output_dir": inputs["output_dir"],
            "enable_graphiti": inputs.get("enable_graphiti", True),  # Pass Graphiti checkbox
        },
    )


# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 1D monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow1d",
        "version": "0.2.0",
        "flow": "raw_document_conversion",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 0.5,
        "memory": 800 * 1024 * 1024,  # 800MB
    }
)
@serve.ingress(app)
class RawConverterFlow:
    """Kodosumi deployment class for Flow 1D: Raw Document Conversion."""

    pass


# Required for Kodosumi deployment
app = RawConverterFlow.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8008, reload=True)
