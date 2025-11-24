"""
Flow 5b: Bundestag Vorgang Ingestion - Kodosumi endpoint

Legislative procedures (vorgänge) from DIP API with relationships.
"""

import os

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from ray import serve

from .forms import bundestag_vorgang_form

app = ServeAPI()


@app.enter(
    path="/",
    model=bundestag_vorgang_form,
    summary="Bundestag Vorgang Ingestion",
    description="Collect German Bundestag legislative procedures (Vorgänge) from DIP API into Neo4j knowledge graph",
    version="1.0.0",
    author="political-monitoring@example.com",
    tags=["Bundestag", "Vorgang", "Flow 5b"],
)
async def ingest_bundestag_vorgaenge(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch vorgang collection workflow."""

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
        error.add(
            wahlperioden="Invalid Wahlperioden format. Use comma-separated values (e.g., 19,20,21)"
        )

    # Validate vorgangstyp
    if not inputs.get("vorgangstyp"):
        error.add(vorgangstyp="Vorgangstyp is required")

    # Validate batch_size
    try:
        batch_size = int(inputs.get("batch_size", 100))
        if batch_size < 10 or batch_size > 500:
            error.add(batch_size="Batch size must be between 10 and 500")
    except (ValueError, TypeError):
        error.add(batch_size="Batch size must be a valid number")

    # Validate max_vorgaenge (can be number or "All")
    max_vorgaenge_input = inputs.get("max_vorgaenge", "1000")
    if max_vorgaenge_input == "All":
        max_vorgaenge = None  # None means unlimited
    else:
        try:
            max_vorgaenge = int(max_vorgaenge_input)
            if max_vorgaenge < 100:
                error.add(max_vorgaenge="Maximum vorgänge must be at least 100")
        except (ValueError, TypeError):
            error.add(max_vorgaenge="Maximum vorgänge must be a valid number or 'All'")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Get configuration from environment
    api_key = os.getenv("BUNDESTAG_API_KEY")
    if not api_key:
        error.add(api_key="BUNDESTAG_API_KEY environment variable is required")
        raise error

    # Launch the vorgang collection workflow
    return Launch(
        request,
        "src.flows.bundestag_vorgang.processor:process_vorgang_batch",
        inputs={
            "wahlperioden": wahlperioden,
            "vorgangstyp": inputs.get("vorgangstyp", "Alle"),
            "batch_size": batch_size,
            "max_vorgaenge": max_vorgaenge,  # Already validated (int or None)
            "create_relationships": inputs.get("create_relationships", True),
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 5b monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow5b",
        "version": "1.0.0",
        "flow": "bundestag_vorgang",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class BundestagVorgangFlow:
    """Kodosumi deployment class for Flow 5b: Bundestag Vorgang Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = BundestagVorgangFlow.bind()


# For local debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8011, reload=True)
