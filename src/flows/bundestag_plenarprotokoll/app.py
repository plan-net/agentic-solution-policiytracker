"""
Flow 5d: Bundestag Plenarprotokoll Ingestion - Kodosumi endpoint

Plenary session protocols from DIP API with optional full-text extraction.
"""

import os
from datetime import datetime

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from ray import serve

from .forms import bundestag_plenarprotokoll_form

app = ServeAPI()


@app.enter(
    path="/",
    model=bundestag_plenarprotokoll_form,
    summary="Bundestag Plenarprotokoll Ingestion",
    description="Collect German Bundestag plenary session protocols from DIP API into Neo4j knowledge graph",
    version="1.0.0",
    author="political-monitoring@example.com",
    tags=["Bundestag", "Plenarprotokoll", "Plenary Protocols", "Flow 5d"],
)
async def ingest_bundestag_plenarprotokolle(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch plenarprotokoll collection workflow."""

    # Validation
    error = InputsError()

    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this ingestion run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Parse wahlperioden
    wahlperioden_str = inputs.get("wahlperioden", "20").strip()
    try:
        wahlperioden = [wp.strip() for wp in wahlperioden_str.split(",") if wp.strip()]
        if not wahlperioden:
            error.add(wahlperioden="At least one Wahlperiode must be specified")
    except Exception:
        error.add(wahlperioden="Invalid Wahlperioden format. Use comma-separated values (e.g., 19,20,21)")

    # Validate date filters if provided
    start_date = (inputs.get("start_date") or "").strip()
    end_date = (inputs.get("end_date") or "").strip()

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            error.add(start_date="Start date must be in format YYYY-MM-DD")
    else:
        start_date_obj = None

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            error.add(end_date="End date must be in format YYYY-MM-DD")
    else:
        end_date_obj = None

    # Validate date range
    if start_date_obj and end_date_obj:
        if start_date_obj > end_date_obj:
            error.add(end_date="End date must be after start date")

    # Validate batch_size
    try:
        batch_size = int(inputs.get("batch_size", 50))
        if batch_size < 10 or batch_size > 200:
            error.add(batch_size="Batch size must be between 10 and 200")
    except (ValueError, TypeError):
        error.add(batch_size="Batch size must be a valid number")

    # Validate max_protocols (can be number or "All")
    max_protocols_input = inputs.get("max_protocols", "100")
    if max_protocols_input == "All":
        max_protocols = None  # None means unlimited
    else:
        try:
            max_protocols = int(max_protocols_input)
            if max_protocols < 1:
                error.add(max_protocols="Maximum protocols must be at least 1")
        except (ValueError, TypeError):
            error.add(max_protocols="Maximum protocols must be a valid number or 'All'")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Get configuration from environment
    api_key = os.getenv("BUNDESTAG_API_KEY")
    if not api_key:
        error.add(api_key="BUNDESTAG_API_KEY environment variable is required")
        raise error

    # Prepare inputs for Launch
    launch_inputs = {
        "wahlperioden": wahlperioden,
        "start_date": start_date if start_date else None,
        "end_date": end_date if end_date else None,
        "batch_size": batch_size,
        "max_protocols": max_protocols,
        "fetch_full_text": inputs.get("fetch_full_text", False),
        "create_relationships": inputs.get("create_relationships", True),
    }

    # Launch the plenarprotokoll collection workflow
    return Launch(
        request,
        "src.flows.bundestag_plenarprotokoll.processor:process_plenarprotokoll_batch",
        inputs=launch_inputs,
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 5d monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow5d",
        "version": "1.0.0",
        "flow": "bundestag_plenarprotokoll",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 3000000000,  # 3GB (protocols are large)
    }
)
@serve.ingress(app)
class BundestagPlenarprotokollFlow:
    """Kodosumi deployment class for Flow 5d: Bundestag Plenarprotokoll Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = BundestagPlenarprotokollFlow.bind()


# For local debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8013, reload=True)
