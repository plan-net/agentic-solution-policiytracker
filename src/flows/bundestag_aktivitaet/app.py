"""
Flow 5f: Bundestag Aktivitaet Ingestion - Kodosumi endpoint

Ingests parliamentary activities (questions, answers, speeches) from DIP API.
"""

import os
from datetime import datetime

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from ray import serve

from .forms import bundestag_aktivitaet_form

app = ServeAPI()


@app.enter(
    path="/",
    model=bundestag_aktivitaet_form,
    summary="Bundestag Aktivitaet Ingestion",
    description="Collect parliamentary activities (questions, answers, speeches) from DIP API into Neo4j knowledge graph",
    version="1.0.0",
    author="political-monitoring@example.com",
    tags=["Bundestag", "Aktivitaet", "Activities", "Flow 5f"],
)
async def ingest_bundestag_aktivitaeten(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch aktivitaet collection workflow."""

    # Validation
    error = InputsError()

    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this ingestion run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Validate wahlperiode
    wahlperiode = inputs.get("wahlperiode", "20").strip()
    if not wahlperiode:
        error.add(wahlperiode="Wahlperiode is required")

    # Validate aktivitaetsart
    valid_arten = ["Alle", "Kleine Anfrage", "Antwort", "Frage", "Rede", "Rede (zu Protokoll gegeben)"]
    if inputs.get("aktivitaetsart") not in valid_arten:
        error.add(aktivitaetsart=f"Aktivitaetsart must be one of: {', '.join(valid_arten)}")

    # Validate max_aktivitaeten (can be number or "All")
    max_aktivitaeten_input = inputs.get("max_aktivitaeten", "100")
    if max_aktivitaeten_input == "All":
        max_aktivitaeten = None  # None means unlimited
    else:
        try:
            max_aktivitaeten = int(max_aktivitaeten_input)
            if max_aktivitaeten < 1:
                error.add(max_aktivitaeten="Maximum activities must be at least 1")
        except (ValueError, TypeError):
            error.add(max_aktivitaeten="Maximum activities must be a valid number or 'All'")

    # Validate batch_size
    try:
        batch_size = int(inputs.get("batch_size", 100))
        if batch_size < 10:
            error.add(batch_size="Batch size must be at least 10")
        elif batch_size > 500:
            error.add(batch_size="Batch size cannot exceed 500")
    except (ValueError, TypeError):
        error.add(batch_size="Batch size must be a valid number")

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

    # Launch the aktivitaet collection workflow
    return Launch(
        request,
        "src.flows.bundestag_aktivitaet.processor:process_bundestag_aktivitaeten",
        inputs={
            "job_name": inputs["job_name"],
            "wahlperiode": wahlperiode,
            "aktivitaetsart": inputs.get("aktivitaetsart", "Alle"),
            "max_items": max_aktivitaeten,  # Already validated (int or None)
            "batch_size": int(inputs.get("batch_size", 100)),
            "create_relationships": inputs.get("create_relationships", True),
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
    """Health check endpoint for Flow 5f monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow5f",
        "version": "1.0.0",
        "flow": "bundestag_aktivitaet",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class BundestagAktivitaetFlow:
    """Kodosumi deployment class for Flow 5f: Bundestag Aktivitaet Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = BundestagAktivitaetFlow.bind()

# For local debugging
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8015, reload=True)
