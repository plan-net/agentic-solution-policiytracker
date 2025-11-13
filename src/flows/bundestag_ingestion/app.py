"""
Flow 5: Bundestag Ingestion - Kodosumi endpoint

German parliamentary data collection interface with comprehensive validation,
health monitoring, and Ray deployment configuration.
"""

from datetime import datetime

import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from ray import serve

from .forms import bundestag_ingestion_form

app = ServeAPI()


@app.enter(
    path="/",
    model=bundestag_ingestion_form,
    summary="Bundestag Data Ingestion",
    description="Collect and ingest German parliamentary data from Bundestag DIP API into Neo4j knowledge graph",
    version="0.2.0",
    author="political-monitoring@example.com",
    tags=["Bundestag", "German Parliament", "Data Collection", "Neo4j", "Flow 5"],
)
async def ingest_bundestag_data(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch Bundestag data collection workflow."""

    # Enhanced validation with InputsError
    error = InputsError()

    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this ingestion run")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")

    # Validate at least one data type is selected
    data_types_selected = any([
        inputs.get("collect_vorgang", False),
        inputs.get("collect_drucksache", False),
        inputs.get("collect_vorgangsposition", False),
        inputs.get("collect_aktivitaet", False),
        inputs.get("collect_plenarprotokoll", False),
        inputs.get("collect_person", False),
        inputs.get("collect_reference_data", False),
    ])

    if not data_types_selected:
        error.add(
            collect_vorgang="Please select at least one data type to collect"
        )

    # Validate max_items_per_type
    try:
        max_items = int(inputs.get("max_items_per_type", 100))
        if max_items < 1:
            error.add(max_items_per_type="Maximum items must be at least 1")
        elif max_items > 10000:
            error.add(max_items_per_type="Maximum items cannot exceed 10000")
    except (ValueError, TypeError):
        error.add(max_items_per_type="Maximum items must be a valid number")

    # Validate batch_size
    try:
        batch_size = int(inputs.get("batch_size", 50))
        if batch_size < 10:
            error.add(batch_size="Batch size must be at least 10")
        elif batch_size > 500:
            error.add(batch_size="Batch size cannot exceed 500")
    except (ValueError, TypeError):
        error.add(batch_size="Batch size must be a valid number")

    # Validate wahlperiode
    valid_wahlperioden = ["19", "20", "21", "all"]
    if inputs.get("wahlperiode") not in valid_wahlperioden:
        error.add(wahlperiode=f"Wahlperiode must be one of: {', '.join(valid_wahlperioden)}")

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

    # Launch the Bundestag ingestion workflow
    return Launch(
        request,
        "src.flows.bundestag_ingestion.processor:process_bundestag_data",
        inputs={
            "job_name": inputs["job_name"],
            # Data type selection
            "collect_vorgang": bool(inputs.get("collect_vorgang", False)),
            "collect_drucksache": bool(inputs.get("collect_drucksache", False)),
            "collect_vorgangsposition": bool(inputs.get("collect_vorgangsposition", False)),
            "collect_aktivitaet": bool(inputs.get("collect_aktivitaet", False)),
            "collect_plenarprotokoll": bool(inputs.get("collect_plenarprotokoll", False)),
            "collect_person": bool(inputs.get("collect_person", False)),
            "collect_reference_data": bool(inputs.get("collect_reference_data", False)),
            # Collection parameters
            "wahlperiode": inputs.get("wahlperiode", "20"),
            "max_items_per_type": int(inputs.get("max_items_per_type", 100)),
            "include_full_text": bool(inputs.get("include_full_text", False)),
            # Processing options
            "batch_size": int(inputs.get("batch_size", 50)),
            "clear_data": bool(inputs.get("clear_data", False)),
            # Date filters
            "start_date": start_date if start_date else None,
            "end_date": end_date if end_date else None,
        },
    )


# Health check endpoint for monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint for Flow 5 monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent-flow5",
        "version": "0.2.0",
        "flow": "bundestag_ingestion",
    }


# Ray deployment configuration
# Note: Resource allocation is controlled by config.yaml
@serve.deployment
@serve.ingress(app)
class BundestagIngestionFlow:
    """Kodosumi deployment class for Flow 5: Bundestag Ingestion."""

    pass


# Required for Kodosumi deployment
fast_app = BundestagIngestionFlow.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8009, reload=True)
