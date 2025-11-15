"""
Flow 5a: Bundestag Person Ingestion - Kodosumi endpoint

Deterministic ingestion of German Bundestag members (MdBs).
"""

import os
from datetime import datetime

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from ray import serve

from .forms import bundestag_person_form

app = ServeAPI()


@app.enter(
    path="/",
    model=bundestag_person_form,
    summary="Bundestag Person Ingestion",
    description="Collect German Bundestag members (MdBs) from DIP API into Neo4j knowledge graph",
    version="0.2.0",
    author="political-monitoring@example.com",
    tags=["Bundestag", "Person", "MdB", "Flow 5a"],
)
async def ingest_bundestag_persons(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch person collection workflow."""

    # Validation
    error = InputsError()

    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this ingestion run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Validate wahlperiode
    valid_wahlperioden = ["19", "20", "21", "all"]
    if inputs.get("wahlperiode") not in valid_wahlperioden:
        error.add(wahlperiode=f"Wahlperiode must be one of: {', '.join(valid_wahlperioden)}")

    # Validate max_items (can be number or "All")
    max_items_input = inputs.get("max_items", "100")
    if max_items_input == "All":
        max_items = None  # None means unlimited
    else:
        try:
            max_items = int(max_items_input)
            if max_items < 1:
                error.add(max_items="Maximum items must be at least 1")
        except (ValueError, TypeError):
            error.add(max_items="Maximum items must be a valid number or 'All'")

    # Validate date filters if provided
    start_date = inputs.get("start_date", "").strip()
    end_date = inputs.get("end_date", "").strip()

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

    # Check for validation errors
    if error.has_errors():
        raise error

    # Get configuration from environment
    api_key = os.getenv("BUNDESTAG_API_KEY")
    if not api_key:
        error.add(api_key="BUNDESTAG_API_KEY environment variable is required")
        raise error

    api_url = os.getenv("BUNDESTAG_API_URL", "https://search.dip.bundestag.de/api/v1")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicamonitoring.v2")

    # Launch the person collection workflow
    return Launch(
        request,
        "src.flows.bundestag_person.processor:process_bundestag_persons",
        inputs={
            "job_name": inputs["job_name"],
            "wahlperiode": inputs.get("wahlperiode", "all"),
            "max_items": max_items,  # Already validated (int or None)
            "start_date": start_date if start_date else None,
            "end_date": end_date if end_date else None,
            "api_key": api_key,
            "api_url": api_url,
            "neo4j_uri": neo4j_uri,
            "neo4j_username": neo4j_username,
            "neo4j_password": neo4j_password,
            "neo4j_database": neo4j_database,
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 5a monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow5a",
        "version": "0.2.0",
        "flow": "bundestag_person",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class BundestagPersonFlow:
    """Kodosumi deployment class for Flow 5a: Bundestag Person Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = BundestagPersonFlow.bind()

# For local debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8010, reload=True)
