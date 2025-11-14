"""
Flow 5c: Bundestag Drucksache Ingestion - Kodosumi endpoint

Parliamentary documents (Drucksachen) from DIP API with full-text extraction.
"""

import os
from datetime import datetime

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from ray import serve

from .forms import bundestag_drucksache_form

app = ServeAPI()


@app.enter(
    path="/",
    model=bundestag_drucksache_form,
    summary="Bundestag Drucksache Ingestion",
    description="Collect German Bundestag parliamentary documents (Drucksachen) from DIP API into Neo4j knowledge graph",
    version="1.0.0",
    author="political-monitoring@example.com",
    tags=["Bundestag", "Drucksache", "Flow 5c"],
)
async def ingest_bundestag_drucksachen(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch drucksache collection workflow."""

    # DEBUG: First line of function
    print("=" * 100, flush=True)
    print("🎯 FLOW 5C FUNCTION CALLED: ingest_bundestag_drucksachen", flush=True)
    print(f"Inputs received: {inputs}", flush=True)
    print("=" * 100, flush=True)

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

    # Validate dokumentart
    if not inputs.get("dokumentart"):
        error.add(dokumentart="Dokumentart is required")

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
        batch_size = int(inputs.get("batch_size", 100))
        if batch_size < 10 or batch_size > 500:
            error.add(batch_size="Batch size must be between 10 and 500")
    except (ValueError, TypeError):
        error.add(batch_size="Batch size must be a valid number")

    # Validate max_drucksachen
    try:
        max_drucksachen = int(inputs.get("max_drucksachen", 100))
        if max_drucksachen < 1 or max_drucksachen > 10000:
            error.add(max_drucksachen="Maximum drucksachen must be between 1 and 10000")
    except (ValueError, TypeError):
        error.add(max_drucksachen="Maximum drucksachen must be a valid number")

    # Validate max_concurrent_downloads
    try:
        max_concurrent_val = inputs.get("max_concurrent_downloads")
        if max_concurrent_val is None or max_concurrent_val == "":
            max_concurrent = 5  # Default
        else:
            max_concurrent = int(max_concurrent_val)
            if max_concurrent < 1 or max_concurrent > 10:
                error.add(max_concurrent_downloads="Max concurrent downloads must be between 1 and 10")
    except (ValueError, TypeError):
        error.add(max_concurrent_downloads="Max concurrent downloads must be a valid number")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Get configuration from environment
    api_key = os.getenv("BUNDESTAG_API_KEY")
    if not api_key:
        error.add(api_key="BUNDESTAG_API_KEY environment variable is required")
        raise error

    # DEBUG: Log before Launch
    import logging
    import json
    logger = logging.getLogger(__name__)

    # Prepare inputs for Launch
    launch_inputs = {
        "wahlperioden": wahlperioden,
        "dokumentart": inputs.get("dokumentart", "Alle"),
        "start_date": start_date if start_date else None,
        "end_date": end_date if end_date else None,
        "batch_size": batch_size,
        "max_drucksachen": max_drucksachen,
        "extract_full_text": inputs.get("extract_full_text", False),
        "max_concurrent_downloads": max_concurrent,
        "create_relationships": inputs.get("create_relationships", True),
    }

    logger.info("=" * 80)
    logger.info("🚀 FLOW 5C: About to call Launch()")
    logger.info(f"Job name: {inputs.get('job_name')}")
    logger.info(f"Launch inputs: {json.dumps(launch_inputs, indent=2)}")
    logger.info(f"Entrypoint: src.flows.bundestag_drucksache.processor:process_drucksache_batch")
    logger.info("=" * 80)
    print("=" * 80, flush=True)
    print("🚀 FLOW 5C: About to call Launch()", flush=True)
    print(f"Job name: {inputs.get('job_name')}", flush=True)
    print(f"Launch inputs: {json.dumps(launch_inputs, indent=2)}", flush=True)
    print(f"Launch inputs type: {type(launch_inputs)}", flush=True)
    print(f"Wahlperioden type: {type(wahlperioden)}", flush=True)
    print(f"Wahlperioden value: {wahlperioden}", flush=True)
    print(f"Entrypoint: src.flows.bundestag_drucksache.processor:process_drucksache_batch", flush=True)
    print("=" * 80, flush=True)

    # Launch the drucksache collection workflow
    result = Launch(
        request,
        "src.flows.bundestag_drucksache.processor:process_drucksache_batch",
        inputs=launch_inputs,
    )

    # DEBUG: Log after Launch
    logger.info("=" * 80)
    logger.info("✅ FLOW 5C: Launch() returned successfully")
    logger.info(f"Result type: {type(result)}")
    logger.info(f"Result: {result}")
    logger.info("=" * 80)
    print("=" * 80, flush=True)
    print("✅ FLOW 5C: Launch() returned successfully", flush=True)
    print(f"Result type: {type(result)}", flush=True)
    print("=" * 80, flush=True)

    return result


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 5c monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow5c",
        "version": "1.0.0",
        "flow": "bundestag_drucksache",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 1,
        "memory": 1500000000,  # 1.5GB
    }
)
@serve.ingress(app)
class BundestagDrucksacheFlow:
    """Kodosumi deployment class for Flow 5c: Bundestag Drucksache Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = BundestagDrucksacheFlow.bind()


# For local debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8012, reload=True)
