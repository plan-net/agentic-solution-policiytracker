# Kodosumi Flow Deployment Patterns v0.2.0

## Overview
This document covers the mechanics of creating, developing, deploying, and testing Kodosumi flows with Ray Serve. For business logic patterns (document processing, Graphiti integration, etc.), see specific domain pattern files.

## Flow File Structure

### Standard Flow Directory
```
src/flows/my_flow/
├── app.py              # Kodosumi ServeAPI endpoint (REQUIRED)
├── forms.py            # Form definitions using kodosumi.core.forms (RECOMMENDED)
├── processor.py        # Business logic entrypoint (REQUIRED)
├── __init__.py         # Flow exports (REQUIRED)
└── README.md           # Flow documentation (OPTIONAL)
```

### File Responsibilities

**app.py**:
- Kodosumi ServeAPI endpoint
- Form model definition (or import from forms.py)
- Input validation with InputsError
- Launch() call to processor entrypoint
- Health check endpoint
- Ray Serve deployment configuration

**forms.py**:
- Pydantic form model using kodosumi.core.forms
- UI components (markdown, inputs, buttons)
- Default values and validation rules

**processor.py**:
- Main business logic entrypoint function
- Receives inputs dict and Tracer
- Progress tracking via tracer.markdown()
- Returns core.response.Markdown()

**__init__.py**:
- Export app and processor for imports

## Flow Creation Pattern

### 1. Minimal app.py Structure
```python
"""
Flow Name: Brief Description

Purpose and usage notes.
"""

import os
import fastapi
from kodosumi.core import InputsError, Launch, ServeAPI
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Get defaults from environment
DEFAULT_MAX_ITEMS = int(os.getenv("FLOW_MAX_ITEMS", "100"))

# Define form inline or import from forms.py
my_form = F.Model(
    F.Markdown(
        """
        # Flow Title

        Description of what this flow does.
        """
    ),
    F.Errors(),
    F.Break(),

    # Input fields
    F.InputText(
        label="Job Name",
        name="job_name",
        placeholder="e.g., My Job",
        value="Default Job Name",
    ),
    F.InputNumber(
        label="Maximum Items",
        name="max_items",
        min_value=1,
        max_value=1000,
        step=1,
        value=DEFAULT_MAX_ITEMS,
    ),

    # Actions
    F.Submit("Start Processing"),
    F.Cancel("Cancel"),
)


@app.enter(
    path="/",
    model=my_form,
    summary="Flow Summary",
    description="Detailed description for API docs",
    version="0.2.0",
    author="your-email@example.com",
    tags=["Category", "Keywords"],
)
async def process_flow(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch processing workflow."""

    # Validation
    error = InputsError()

    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name")

    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters")

    try:
        max_items = int(inputs.get("max_items", DEFAULT_MAX_ITEMS))
        if max_items < 1:
            error.add(max_items="Maximum items must be at least 1")
    except (ValueError, TypeError):
        error.add(max_items="Maximum items must be a valid number")

    # Check for validation errors
    if error.has_errors():
        raise error

    # Launch processor
    return Launch(
        request,
        "src.flows.my_flow.processor:execute_processing",
        inputs={
            "job_name": inputs["job_name"],
            "max_items": max_items,
        },
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "my-flow",
        "version": "0.2.0",
        "flow": "my_flow",
    }


# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024,  # 4GB
    }
)
@serve.ingress(app)
class MyFlow:
    """Kodosumi deployment class for My Flow."""
    pass


# Required for Kodosumi deployment
fast_app = MyFlow.bind()

# For local debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8010, reload=True)
```

### 2. Processor Pattern
```python
"""
Processor for My Flow.
"""

from kodosumi import core, Tracer
from datetime import datetime


async def execute_processing(inputs: dict, tracer: Tracer):
    """
    Main processing entrypoint called by Launch().

    Args:
        inputs: Validated inputs from form submission
        tracer: Kodosumi tracer for progress updates

    Returns:
        core.response.Markdown with formatted report
    """

    # Extract inputs
    job_name = inputs["job_name"]
    max_items = inputs["max_items"]

    # Progress tracking
    await tracer.markdown(f"🚀 Starting {job_name}...")
    await tracer.markdown(f"📊 Processing up to {max_items} items")

    # Your business logic here
    results = await process_items(max_items)

    # Generate report
    report = generate_report(job_name, results)

    # Final progress update
    await tracer.markdown("✅ Processing complete!")

    # CRITICAL: Return Markdown response
    return core.response.Markdown(report)


async def process_items(max_items: int):
    """Your actual business logic."""
    # Implementation here
    return {"processed": max_items, "errors": []}


def generate_report(job_name: str, results: dict) -> str:
    """Generate markdown report."""
    return f"""# {job_name} - Complete

## Summary
- **Items Processed**: {results['processed']}
- **Errors**: {len(results['errors'])}

## Status
✅ All processing complete!
"""
```

## Form Building Patterns

### Available Form Components
```python
from kodosumi.core import forms as F

# Text components
F.Markdown("# Markdown content")
F.Errors()  # Error display area
F.Break()   # Visual separator

# Input fields
F.InputText(
    label="Field Label",
    name="field_name",
    value="default",
    placeholder="hint text"
)

F.InputNumber(
    label="Numeric Field",
    name="number_field",
    min_value=1,
    max_value=1000,
    step=1,
    value=100
)

F.Select(
    label="Dropdown",
    name="select_field",
    value="default",
    option=[
        F.InputOption(name="value1", label="Display 1"),
        F.InputOption(name="value2", label="Display 2"),
    ]
)

# Actions
F.Submit("Start Processing")
F.Cancel("Cancel")
```

### Form Organization Pattern
```python
# forms.py - Separate file for complex forms
from kodosumi.core import forms as F

my_flow_form = F.Model(
    F.Markdown("# Flow Title\n\nDescription..."),
    F.Errors(),
    F.Break(),

    # Group 1: Basic Info
    F.Markdown("### Job Information"),
    F.InputText(label="Job Name", name="job_name", value="Default"),
    F.Break(),

    # Group 2: Filters
    F.Markdown("### Filters"),
    F.Select(label="Category", name="category", ...),
    F.InputNumber(label="Limit", name="limit", ...),
    F.Break(),

    # Group 3: Actions
    F.Submit("Start"),
    F.Cancel("Cancel"),
)
```

## Input Validation Pattern

### Comprehensive Validation
```python
from kodosumi.core import InputsError
from datetime import datetime

async def process_flow(request: fastapi.Request, inputs: dict):
    """Process with comprehensive validation."""

    error = InputsError()

    # 1. Required field validation
    if not inputs.get("job_name"):
        error.add(job_name="Job name is required")

    # 2. Length validation
    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters")

    # 3. Numeric validation
    try:
        max_items = int(inputs.get("max_items", 100))
        if max_items < 1:
            error.add(max_items="Must be at least 1")
        elif max_items > 1000:
            error.add(max_items="Cannot exceed 1000")
    except (ValueError, TypeError):
        error.add(max_items="Must be a valid number")

    # 4. Choice validation
    valid_choices = ["option1", "option2", "option3"]
    if inputs.get("category") not in valid_choices:
        error.add(category=f"Must be one of: {', '.join(valid_choices)}")

    # 5. Date validation
    if inputs.get("start_date"):
        try:
            start_date = datetime.strptime(inputs["start_date"], "%Y-%m-%d")
        except ValueError:
            error.add(start_date="Must be in format YYYY-MM-DD")

    # 6. Date range validation
    if inputs.get("start_date") and inputs.get("end_date"):
        try:
            start = datetime.strptime(inputs["start_date"], "%Y-%m-%d")
            end = datetime.strptime(inputs["end_date"], "%Y-%m-%d")
            if start > end:
                error.add(end_date="End date must be after start date")
        except ValueError:
            pass  # Already added individual date errors above

    # 7. Environment variable validation
    api_key = os.getenv("API_KEY")
    if not api_key:
        error.add(api_key="API_KEY environment variable is required")

    # Check for errors
    if error.has_errors():
        raise error

    # Launch if validation passes
    return Launch(request, "module:function", inputs={...})
```

## Deployment Configuration

### config.yaml Structure
```yaml
# Global Ray Serve configuration
proxy_location: EveryNode
http_options:
  host: 0.0.0.0
  port: 8001
grpc_options:
  port: 9000
logging_config:
  encoding: TEXT
  log_level: INFO
  enable_access_log: true

# Applications (flows)
applications:
- name: my-flow                           # Unique flow name
  route_prefix: /my-flow                  # URL path
  import_path: src.flows.my_flow.app:fast_app  # Deployment binding
  runtime_env:
    env_vars:
      PYTHONPATH: .
      LOG_LEVEL: INFO
      # Add all environment variables your flow needs
      NEO4J_URI: bolt://localhost:7687
      API_KEY: your-api-key
  ray_actor_options:
    num_cpus: 2                           # CPU cores
    memory: 4000000000                    # Memory in bytes (4GB)
  autoscaling_config:
    min_replicas: 1                       # Minimum instances
    max_replicas: 2                       # Maximum instances
    target_num_ongoing_requests_per_replica: 1
```

### Resource Allocation Guidelines
```yaml
# Light processing (API calls, simple transforms)
ray_actor_options:
  num_cpus: 1
  memory: 2000000000  # 2GB

# Medium processing (document processing, data transforms)
ray_actor_options:
  num_cpus: 2
  memory: 4000000000  # 4GB

# Heavy processing (ML inference, large batches)
ray_actor_options:
  num_cpus: 4
  memory: 8000000000  # 8GB
```

## Deployment Workflow

### Step 1: Environment Configuration
```bash
# 1. Update .env with required variables
cat >> .env << EOF
MY_FLOW_API_KEY=your-key
MY_FLOW_MAX_ITEMS=500
EOF

# 2. Sync environment to config.yaml
just sync-config
```

### Step 2: Deploy Flow
```bash
# Deploy all flows
just deploy-all

# Or deploy via Ray directly
uv run --active serve deploy config.yaml

# Check deployment status
just status
# OR
uv run --active serve status
```

### Step 3: Access Flow
```
Kodosumi Admin: http://localhost:3370 (admin/admin)
Flow Endpoint:  http://localhost:8001/my-flow
Ray Dashboard:  http://localhost:8265
```

### Step 4: Test Flow
```bash
# Via Kodosumi admin UI
open http://localhost:3370

# Via HTTP API
curl -X POST http://localhost:8001/my-flow \
  -H "Content-Type: application/json" \
  -d '{"job_name": "Test Job", "max_items": 10}'
```

## Development Commands

### Quick Reference
```bash
# Development cycle
just start          # Start Ray + Kodosumi + all services
just deploy-all     # Redeploy all flows after code changes
just status         # Check health of all services

# Specific operations
just sync-config    # Sync .env to config.yaml
just ray-logs       # View Ray application logs
just stop           # Stop all services

# Testing
just test-flows     # Run flow tests
just test           # Run all tests
```

### Deployment Justfile Targets
```makefile
# From justfile
deploy-all: sync-config
    @echo "📦 Deploying all applications..."
    uv run --active serve deploy config.yaml
    @echo "✅ Deployment complete"
    @echo "🌐 Access at: http://localhost:3370"

sync-config:
    @echo "🔄 Syncing environment to config.yaml..."
    uv run python scripts/sync_config.py
    @echo "✅ Config synced"

status:
    @echo "📊 Service Status"
    @uv run --active serve status
```

## Testing Patterns

### Unit Testing Processor
```python
# tests/unit/flows/test_my_flow_processor.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.flows.my_flow.processor import execute_processing


@pytest.mark.asyncio
async def test_processor_success():
    """Test processor with valid inputs."""

    # Mock tracer
    tracer = MagicMock()
    tracer.markdown = AsyncMock()

    # Test inputs
    inputs = {
        "job_name": "Test Job",
        "max_items": 10,
    }

    # Execute
    result = await execute_processing(inputs, tracer)

    # Assertions
    assert result is not None
    assert "Test Job" in result.content
    tracer.markdown.assert_called()
```

### Integration Testing Flow Endpoint
```python
# tests/integration/flows/test_my_flow_integration.py
import pytest
from httpx import AsyncClient
from src.flows.my_flow.app import app


@pytest.mark.asyncio
async def test_flow_endpoint_validation():
    """Test flow endpoint with invalid inputs."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test missing required field
        response = await client.post("/", json={"max_items": 10})
        assert response.status_code == 422  # Validation error

        # Test valid inputs
        response = await client.post("/", json={
            "job_name": "Valid Job",
            "max_items": 10
        })
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["flow"] == "my_flow"
```

### Testing with Ray Local Mode
```python
# conftest.py
import pytest
import ray


@pytest.fixture(scope="session")
def ray_local():
    """Initialize Ray in local mode for testing."""
    if not ray.is_initialized():
        ray.init(local_mode=True)
    yield
    ray.shutdown()
```

## Local Debugging

### Running Flow Standalone
```bash
# Run without Kodosumi/Ray for quick testing
cd src/flows/my_flow
python app.py

# Access at: http://localhost:8010
```

### Debug Mode in app.py
```python
if __name__ == "__main__":
    import uvicorn

    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Run with reload
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="debug"
    )
```

## Common Patterns

### Environment Variable Defaults
```python
import os

# Flow configuration from environment
DEFAULT_MAX_ITEMS = int(os.getenv("FLOW_MAX_ITEMS", "100"))
DEFAULT_TIMEOUT = int(os.getenv("FLOW_TIMEOUT", "300"))
DEFAULT_BATCH_SIZE = int(os.getenv("FLOW_BATCH_SIZE", "50"))

# External service configuration
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL", "https://api.example.com")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
```

### Progress Tracking with Tracer
```python
async def execute_processing(inputs: dict, tracer: Tracer):
    """Process with detailed progress updates."""

    total_items = inputs["max_items"]

    # Stage 1
    await tracer.markdown("🚀 Stage 1: Initialization...")
    # ... initialization logic

    # Stage 2 with progress
    await tracer.markdown(f"📊 Stage 2: Processing {total_items} items...")
    for i, item in enumerate(items, 1):
        # Process item
        if i % 10 == 0:  # Update every 10 items
            await tracer.markdown(f"⏳ Processed {i}/{total_items} items...")

    # Stage 3
    await tracer.markdown("📝 Stage 3: Generating report...")
    # ... report generation

    # Complete
    await tracer.markdown("✅ All stages complete!")
    return core.response.Markdown(report)
```

### Error Handling in Processor
```python
async def execute_processing(inputs: dict, tracer: Tracer):
    """Process with comprehensive error handling."""

    try:
        await tracer.markdown("🚀 Starting processing...")

        # Main processing logic
        results = await process_items(inputs)

        # Check for partial errors
        if results.get("errors"):
            await tracer.markdown(f"⚠️ Completed with {len(results['errors'])} errors")

        # Generate report
        report = generate_report(results)
        return core.response.Markdown(report)

    except Exception as e:
        # Log error
        logger.error(f"Processing failed: {e}", exc_info=True)

        # User-friendly error message
        await tracer.markdown(f"❌ Processing failed: {str(e)}")

        # Return error report
        error_report = f"""# Processing Failed

## Error
{str(e)}

## Next Steps
1. Check logs for details
2. Verify input parameters
3. Contact support if issue persists
"""
        return core.response.Markdown(error_report)
```

## Best Practices

### ✅ DO
- Separate form definitions into forms.py for complex UIs
- Use environment variables for configuration
- Implement comprehensive input validation with InputsError
- Provide progress updates via tracer.markdown()
- Return core.response.Markdown() from processor
- Add health check endpoint for monitoring
- Configure appropriate Ray actor resources
- Test flows with unit and integration tests
- Use meaningful flow names and route prefixes
- Document flow purpose and usage in docstrings

### ❌ DON'T
- Put heavy business logic in app.py (use processor.py)
- Skip input validation (always validate!)
- Return raw dictionaries from processor (use Markdown response)
- Forget to add health check endpoint
- Over-allocate Ray actor resources
- Hardcode configuration (use environment variables)
- Skip testing (flows should be well-tested)
- Use unclear or conflicting route prefixes
- Forget to sync .env to config.yaml before deploying

## Troubleshooting

### Flow Not Appearing in Kodosumi
```bash
# 1. Check Ray deployment
uv run --active serve status

# 2. Check logs
just ray-logs | grep my-flow

# 3. Verify config.yaml
grep -A 10 "my-flow" config.yaml

# 4. Check import path
python -c "from src.flows.my_flow.app import fast_app; print(fast_app)"
```

### Validation Errors Not Showing
```python
# Ensure error.add() uses correct field names
error = InputsError()
error.add(job_name="Error message")  # Field name must match form field name

# Ensure error is raised
if error.has_errors():
    raise error  # Don't forget to raise!
```

### Deployment Fails
```bash
# 1. Check Python path
echo $PYTHONPATH

# 2. Verify module imports
uv run python -c "import src.flows.my_flow.app"

# 3. Check Ray cluster
uv run --active ray status

# 4. Review deployment logs
just ray-logs | tail -50
```

## References

- [Kodosumi Documentation](https://kodosumi.dev)
- [Ray Serve Documentation](https://docs.ray.io/en/latest/serve/)
- Example flows in `src/flows/`:
  - `bundestag_person/` - Simple deterministic ingestion
  - `data_ingestion_bulk_auto/` - Bulk processing with auto-detection
  - `bundestag_vorgang/` - Complex multi-page pagination

---

**Version**: 0.2.0
**Last Updated**: 2025-11-17
**Status**: Production Ready
