# app.py - Kodosumi Endpoint for Political Monitoring Agent
import fastapi
from kodosumi.core import ServeAPI, Launch, InputsError
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define rich user interface form
analysis_form = F.Model(
    F.Markdown("""
    # Political Monitoring Agent
    
    Analyze political documents for relevance, priority, and topics using distributed AI processing.
    Upload documents and get comprehensive analysis reports with confidence scoring.
    """),
    F.Errors(),  # Display validation errors
    F.Break(),   # Visual separator
    
    # Job Configuration
    F.InputText(
        label="Job Name", 
        name="job_name",
        placeholder="e.g., Weekly Policy Review, Brexit Analysis"
    ),
    
    # Input Sources
    F.InputText(
        label="Input Folder Path",
        name="input_folder", 
        value="/data/input",
        placeholder="Path to documents folder"
    ),
    
    F.InputText(
        label="Context File Path",
        name="context_file",
        value="/data/context/client.yaml", 
        placeholder="Path to analysis context configuration"
    ),
    
    # Analysis Parameters
    F.InputNumber(
        label="Priority Threshold (%)",
        name="priority_threshold",
        min_value=0,
        max_value=100,
        step=5,
        value=70,
        placeholder="Minimum priority score for inclusion"
    ),
    
    # Processing Options
    F.Checkbox(
        label="Include Low Confidence Results",
        name="include_low_confidence", 
        value=False,
        option="Include documents with confidence scores below 80%"
    ),
    
    F.Checkbox(
        label="Enable Topic Clustering",
        name="clustering_enabled",
        value=True,
        option="Group documents by semantic similarity into topic clusters"
    ),
    
    # Advanced Options
    F.InputNumber(
        label="Batch Size",
        name="batch_size",
        min_value=10,
        max_value=1000,
        value=50,
        placeholder="Number of documents to process per batch"
    ),
    
    F.InputNumber(
        label="Processing Timeout (minutes)",
        name="timeout_minutes",
        min_value=5,
        max_value=120,
        value=30,
        placeholder="Maximum time to wait for analysis completion"
    ),
    
    # Additional Instructions
    F.InputArea(
        label="Additional Instructions",
        name="instructions",
        placeholder="Any specific requirements, focus areas, or custom analysis criteria..."
    ),
    
    # Action Buttons
    F.Submit("Start Analysis"),
    F.Cancel("Cancel"),
    F.Action(text="Advanced Settings", value="advanced", name="action"),
)

@app.enter(
    path="/",
    model=analysis_form,
    summary="Political Document Analysis",
    description="Comprehensive political document monitoring and analysis using distributed AI",
    version="1.0.0",
    author="political-monitoring@example.com",
    tags=["Politics", "Document Analysis", "AI", "Monitoring"]
)
async def enter(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch political analysis."""
    
    # Validate inputs
    error = InputsError()
    
    # Required fields validation
    if not inputs.get("job_name"):
        error.add(job_name="Please provide a job name for this analysis")
    
    if len(inputs.get("job_name", "")) < 3:
        error.add(job_name="Job name must be at least 3 characters long")
    
    if not inputs.get("input_folder"):
        error.add(input_folder="Please specify the input folder path")
        
    if not inputs.get("context_file"):
        error.add(context_file="Please specify the context file path")
    
    # Validate numeric ranges
    priority_threshold = inputs.get("priority_threshold", 0)
    if priority_threshold < 0 or priority_threshold > 100:
        error.add(priority_threshold="Priority threshold must be between 0 and 100")
    
    batch_size = inputs.get("batch_size", 0)
    if batch_size < 10 or batch_size > 1000:
        error.add(batch_size="Batch size must be between 10 and 1000")
    
    timeout_minutes = inputs.get("timeout_minutes", 0)
    if timeout_minutes < 5 or timeout_minutes > 120:
        error.add(timeout_minutes="Timeout must be between 5 and 120 minutes")
    
    # Check for validation errors
    if error.has_errors():
        raise error
    
    # Launch the political analysis workflow
    return Launch(
        request,
        "political_analyzer:execute_analysis",  # Path to entrypoint function
        inputs={
            "job_name": inputs["job_name"],
            "input_folder": inputs["input_folder"],
            "context_file": inputs["context_file"],
            "priority_threshold": float(inputs.get("priority_threshold", 70.0)),
            "include_low_confidence": bool(inputs.get("include_low_confidence", False)),
            "clustering_enabled": bool(inputs.get("clustering_enabled", True)),
            "batch_size": int(inputs.get("batch_size", 50)),
            "timeout_minutes": int(inputs.get("timeout_minutes", 30)),
            "instructions": inputs.get("instructions", "")
        }
    )

# Health check endpoint for Kodosumi
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "political-monitoring-agent",
        "version": "1.0.0"
    }

# Ray deployment configuration
@serve.deployment(
    ray_actor_options={
        "num_cpus": 2,
        "memory": 4 * 1024 * 1024 * 1024  # 4GB
    }
)
@serve.ingress(app)
class PoliticalMonitoringAgent:
    """Kodosumi deployment class for Political Monitoring Agent."""
    pass

# Required for Kodosumi deployment
fast_app = PoliticalMonitoringAgent.bind()

# For local debugging without Kodosumi
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)