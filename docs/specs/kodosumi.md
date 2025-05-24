# Kodosumi Integration Guide for Claude Code

## 🎯 What is Kodosumi?

Kodosumi is a runtime environment for managing and executing agentic services at scale, built on:
- **Ray** - Distributed computing framework for parallel processing
- **FastAPI** - Powers agent endpoints and HTTP interfaces
- **Litestar** - Runs the admin interface and core services

## 🏗️ Architecture Overview

Kodosumi services have two main components:

1. **Entrypoint** (e.g., `calc.py`) - Core business logic and distributed computing
2. **Endpoint** (e.g., `app.py`) - HTTP interface and user interaction

```
User → Endpoint (app.py) → Launch → Entrypoint (calc.py) → Ray Workers
         ↓                           ↓
      Form UI                   Distributed Tasks
```

## 📦 Key Imports

```python
# Advanced form builder (recommended)
import kodosumi.core as core
from kodosumi.core import ServeAPI
from kodosumi.core import forms as F

# Simple approach
from kodosumi.serve import Launch, ServeAPI

# Always needed
from ray import serve
import fastapi
```

## 🚀 Quick Start Commands

### 1. Start Kodosumi
```bash
# Install kodosumi
pip install kodosumi

# Create working directory
mkdir ./home
cd ./home

# Start Ray
ray start --head

# Deploy your service
serve deploy config.yaml

# Start Kodosumi and register endpoints
koco start --register http://localhost:8001/-/routes
```

### 2. Access Kodosumi
- **Admin Panel**: http://localhost:3370
- **Default Login**: username: `admin`, password: `admin`
- **Ray Dashboard**: http://localhost:8265
- **API Docs**: http://localhost:3370/schema/swagger

### 3. Stop Everything
```bash
# Stop services (Ctrl+C in terminal)
# Stop Ray serve
serve shutdown --yes
# Stop Ray
ray stop
```

## 📁 Essential Project Structure

```
your-agent/
├── __init__.py          # Package marker
├── app.py              # Endpoint - HTTP interface & forms
├── calc.py             # Entrypoint - business logic & Ray tasks
└── config.yaml         # Deployment configuration
```

### Two-Part Architecture

1. **Endpoint (`app.py`)**: Handles HTTP requests, forms, validation
2. **Entrypoint (`calc.py`)**: Contains core logic and distributed tasks

## 🔧 How to Structure Your Service

Kodosumi services follow a two-file pattern: endpoint (app.py) and entrypoint (calc.py):

### 1. Entrypoint - Business Logic (`calc.py`)

The entrypoint contains your core business logic and distributed tasks:

```python
# calc.py
import asyncio
import ray
from kodosumi.core import Tracer

async def execute(inputs: dict, tracer: Tracer):
    """Main entrypoint function called by Launch"""
    # Extract inputs
    tasks = inputs["tasks"]
    
    # Create distributed tasks
    futures = [process_task.remote(i) for i in range(tasks)]
    
    # Wait for results with progress tracking
    pending = futures.copy()
    results = []
    
    while pending:
        done, pending = ray.wait(pending, timeout=0.1)
        if done:
            batch_results = await asyncio.gather(*done)
            results.extend(batch_results)
            # Use tracer for progress updates
            await tracer.markdown(f"Completed {len(results)}/{tasks} tasks")
    
    return results

@ray.remote
def process_task(task_id: int):
    """Ray remote function for distributed processing"""
    # Your heavy computation here
    import time
    time.sleep(1)  # Simulate work
    return {"task_id": task_id, "result": "processed"}
```

### 2. Endpoint - HTTP Interface (`app.py`)

The endpoint handles user interaction and launches the entrypoint:

```python
# app.py
import fastapi
from kodosumi.core import ServeAPI, Launch, InputsError
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define the user interface
my_model = F.Model(
    F.Markdown("# My Agent Service"),
    F.Errors(),
    F.Break(),
    F.InputNumber(label="Number of Tasks", name="tasks", 
                  value=10, min_value=1, max_value=100),
    F.Submit("Process"),
    F.Cancel("Cancel")
)

@app.enter(
    path="/",
    model=my_model,
    summary="My Agent Service",
    description="Distributed task processing service",
    version="1.0.0",
    author="team@example.com",
    tags=["Processing", "AI"]
)
async def enter(request: fastapi.Request, inputs: dict):
    """Endpoint that receives form submission"""
    # Validate inputs
    tasks = inputs.get("tasks", 0)
    if not tasks or tasks < 1:
        error = InputsError("Invalid input")
        error.add(tasks="Please specify at least 1 task")
        raise error
    
    # Launch the entrypoint execution
    return Launch(
        request,
        "my_service.calc:execute",  # Path to entrypoint function
        inputs={"tasks": tasks}
    )

# Ray deployment configuration
@serve.deployment
@serve.ingress(app)
class MyService: 
    pass

fast_app = MyService.bind()
```

### Key Components Explained

1. **Launch Object**: Bridges endpoint to entrypoint
   ```python
   Launch(request, "module.file:function", inputs={...})
   ```

2. **Tracer**: Provides real-time updates during execution
   ```python
   await tracer.markdown("Progress update...")
   ```

3. **Ray Remote**: Distributes tasks across workers
   ```python
   @ray.remote
   def heavy_task():
       # Runs on Ray worker
   ```

## 📝 How to Provide a Form

Kodosumi offers two approaches for forms: the simple `Launch` class or the advanced `forms` module:

### Advanced Form Builder (Recommended)

```python
import kodosumi.core as core
from kodosumi.core import ServeAPI
from kodosumi.core import forms as F

app = ServeAPI()

@app.enter(
    path="/",
    model=core.forms.Model(
        F.Markdown("# My Agent Form"),
        F.Errors(),  # Display validation errors
        F.Break(),   # Visual separator
        
        # Text inputs
        F.InputText(label="Topic", name="topic"),
        F.InputArea(label="Description", name="description"),
        
        # Number inputs
        F.InputNumber(label="Temperature", name="temp", 
                      min_value=0, max_value=2, step=0.1),
        
        # Selection inputs
        F.Checkbox(label="Include examples", name="examples", value=True),
        F.Select(label="Style", name="style", option=[
            F.InputOption(label="Formal", name="formal"),
            F.InputOption(label="Casual", name="casual"),
            F.InputOption(label="Technical", name="technical"),
        ], value="formal"),
        
        # Date/Time inputs
        F.InputDate(label="Deadline", name="deadline"),
        F.InputDateTime(label="Schedule", name="schedule"),
        
        # Action buttons
        F.Submit("Generate"),
        F.Cancel("Cancel"),
        F.Action(text="Advanced Options", value="advanced", name="action"),
    ),
    summary="My Agent",
    description="AI-powered content generation",
    version="1.0.0",
    author="your-email@example.com",
    tags=["AI", "Generation"]
)
async def enter(request: fastapi.Request, inputs: dict):
    # Process form inputs
    # inputs contains all form field values
    return process_request(inputs)
```

### Simple Form Approach

```python
from kodosumi.serve import Launch

# For simpler cases, you can still use HTML forms
@app.get("/")
async def form_page():
    form_html = """
    <form method="post" action="/process">
        <input type="text" name="topic" required>
        <button type="submit">Generate</button>
    </form>
    """
    
    return Launch(
        title="My Agent",
        form=form_html
    )
```

## 📋 Available Form Elements

When using `kodosumi.core.forms`, you have access to these form elements:

### Input Elements
- `F.InputText(label, name)` - Single line text input
- `F.InputNumber(label, name, min_value, max_value, step)` - Numeric input
- `F.InputArea(label, name)` - Multi-line text area
- `F.InputDate(label, name, min_date, max_date)` - Date picker
- `F.InputTime(label, name)` - Time picker
- `F.InputDateTime(label, name, min_datetime, max_datetime)` - Date & time picker

### Selection Elements
- `F.Checkbox(label, name, value, option)` - Checkbox input
- `F.Select(label, name, option, value)` - Dropdown select
- `F.InputOption(label, name)` - Option for select dropdown

### Display Elements
- `F.Markdown(content)` - Render markdown content
- `F.Errors()` - Display validation errors
- `F.Break()` - Visual separator

### Action Elements
- `F.Submit(text)` - Submit button
- `F.Cancel(text)` - Cancel button
- `F.Action(text, value, name)` - Custom action button

## ⚠️ Error Handling

Handle form validation errors properly:

```python
import kodosumi.core as core

@app.enter(path="/", model=your_form_model)
async def enter(request: fastapi.Request, inputs: dict):
    # Validate inputs
    if not inputs.get("topic"):
        error = core.InputsError("Validation failed")
        error.add(topic="Topic is required")
        raise error
    
    # Process valid inputs
    return process_inputs(inputs)
```

## 📄 How to Return Results as Markdown

Kodosumi can render markdown results in multiple ways:

### With Launch Class
```python
@app.post("/process")
async def process_request(topic: str, style: str):
    markdown_result = f"""
# Results for: {topic}

## Summary
Your generated content in **{style}** style.

### Key Points
- Point 1
- Point 2
- Point 3
    """
    
    return Launch(
        title="Results",
        result=markdown_result,
        markdown=True
    )
```

### With Form Model
```python
@app.enter(path="/result", model=core.forms.Model(
    F.Markdown("""
    # Processing Complete
    
    Your results are ready!
    """),
    F.Action(text="Start Over", value="restart", name="action")
))
async def show_result(request, inputs):
    return your_markdown_content
```

## 🚀 The Launch Object

The `Launch` object is the bridge between your endpoint and entrypoint:

```python
from kodosumi.core import Launch

# Basic usage
return Launch(
    request,                    # FastAPI request object
    "module.file:function",     # Path to entrypoint function
    inputs={"key": "value"}     # Inputs to pass to entrypoint
)

# Full example
return Launch(
    request,
    "my_service.calc:execute",  # Calls execute() in calc.py
    inputs={
        "tasks": 100,
        "config": {"timeout": 30}
    }
)
```

### How Launch Works

1. **Receives** form submission at endpoint
2. **Validates** inputs and prepares data
3. **Launches** entrypoint function asynchronously
4. **Tracks** execution with Tracer
5. **Returns** results or streams progress

### Entrypoint Function Signature

Your entrypoint function must have this signature:

```python
async def your_entrypoint(inputs: dict, tracer: Tracer):
    # inputs: Dictionary from Launch
    # tracer: For progress updates
    
    await tracer.markdown("Starting processing...")
    result = process_data(inputs)
    await tracer.markdown("Complete!")
    
    return result
```

## ⚙️ config.yaml Structure

The config.yaml file controls both Kodosumi server settings and your service deployment:

### Full Configuration Example

```yaml
# Server configuration
proxy_location: EveryNode  # How Ray distributes the proxy
http_options:
  host: 0.0.0.0           # Listen on all interfaces
  port: 8001              # Port for Ray Serve
grpc_options:
  port: 9000              # gRPC port
  grpc_servicer_functions: []
logging_config:
  encoding: TEXT          # TEXT or JSON
  log_level: INFO         # DEBUG, INFO, WARNING, ERROR
  logs_dir: null          # Directory for logs (null = stdout)
  enable_access_log: true # Log HTTP access
  additional_log_standard_attrs: []

# Application deployment
applications:
  - name: your-agent-name
    route_prefix: /your-agent
    import_path: app:fast_app  # Points to your serve.py file
    runtime_env:
      pip:
        - crewai
        - langchain
        - openai
      env_vars:
        PYTHONPATH: .
        OPENAI_API_KEY: ${OPENAI_API_KEY}
```

### Minimal Configuration

```yaml
# If you only need basic deployment
applications:
  - name: my-service
    route_prefix: /my-service
    import_path: app:fast_app
    runtime_env:
      pip:
        - requests
```

### Configuration Options Explained

- **proxy_location**: Controls Ray Serve proxy placement
  - `EveryNode` - Proxy on every node (recommended)
  - `HeadOnly` - Proxy only on head node

- **http_options**: HTTP server settings
  - `host`: IP to bind to (0.0.0.0 = all interfaces)
  - `port`: Port for Ray Serve (default: 8001)

- **logging_config**: Control logging behavior
  - `encoding`: TEXT (human-readable) or JSON (structured)
  - `log_level`: DEBUG, INFO, WARNING, ERROR
  - `enable_access_log`: Log all HTTP requests

- **runtime_env**: Python environment for your service
  - `pip`: List of packages to install
  - `env_vars`: Environment variables (use ${VAR} for substitution)

## 🔑 Key Integration Patterns

### 1. Using Ray for Distributed Processing
```python
import ray

@ray.remote
def heavy_computation(data):
    # CPU-intensive work
    return result

# In your endpoint
@app.post("/process")
async def process(data: str):
    # Distribute work
    result = ray.get(heavy_computation.remote(data))
    return Launch(result=result, markdown=True)
```

### 2. Streaming Results
```python
from kodosumi.serve import Launch

@app.post("/stream")
async def stream_results(request):
    # For streaming, return Launch with streaming=True
    return Launch(
        title="Streaming Results",
        streaming=True,
        stream_handler=your_stream_function
    )
```

### 3. File Uploads
```python
@app.post("/upload")
async def handle_upload(file: UploadFile):
    content = await file.read()
    # Process file
    return Launch(
        title="File Processed",
        result=f"Processed {file.filename}"
    )
```

## 🎨 Admin Panel Features

After logging into http://localhost:3370:

1. **Flow Management** (http://localhost:3370/admin/flow)
   - View all deployed services
   - Launch services directly
   - Monitor execution status

2. **Routes Screen** (http://localhost:3370/admin/routes)
   - View all registered endpoints
   - Refresh routes if services aren't showing
   - Click "RECONNECT" to update

3. **Timeline** (http://localhost:3370/timeline/view)
   - View execution history
   - Monitor real-time events
   - Debug service issues

## 🐛 Common Issues & Solutions

### Service Not Showing in Admin Panel
```bash
# Refresh routes in admin panel
# Go to http://localhost:3370/admin/routes
# Click "RECONNECT" button
```

### Import Path Errors
```yaml
# Correct format in config.yaml
import_path: app:fast_app        # ✅ Correct
import_path: app.py:fast_app     # ❌ Wrong
import_path: ./app:fast_app      # ❌ Wrong
```

### Ray Not Starting
```bash
# Check Ray status
ray status

# If issues, stop and restart
ray stop
ray start --head
```

### Port Already in Use
```yaml
# Change port in config.yaml
http_options:
  port: 8002  # Try different port
```

### Missing Dependencies
```yaml
# Ensure all imports are in runtime_env
runtime_env:
  pip:
    - all-your-packages
    - including-sub-dependencies
```

## 📚 Complete Example: AI Content Generator

Here's a complete example showing the two-file architecture:

### File 1: Entrypoint (`generator.py`)

```python
# generator.py - Core business logic
import asyncio
import ray
from kodosumi.core import Tracer
import openai

async def generate_content(inputs: dict, tracer: Tracer):
    """Main entrypoint for content generation"""
    topic = inputs["topic"]
    style = inputs["style"]
    sections = inputs.get("sections", 3)
    
    await tracer.markdown(f"# Generating content about: {topic}")
    
    # Create parallel generation tasks
    futures = [
        generate_section.remote(topic, style, i) 
        for i in range(sections)
    ]
    
    # Collect results with progress updates
    results = []
    for i, future in enumerate(futures):
        section = await future
        results.append(section)
        await tracer.markdown(f"✓ Completed section {i+1}/{sections}")
    
    # Combine results
    full_content = f"# {topic}\n\n"
    full_content += "\n\n".join(results)
    
    await tracer.markdown("## Generation Complete!")
    return full_content

@ray.remote
def generate_section(topic: str, style: str, section_num: int):
    """Generate a single section using AI"""
    # Your AI logic here (OpenAI, Anthropic, etc.)
    prompt = f"Write section {section_num + 1} about {topic} in {style} style"
    
    # Simulated AI response
    import time
    time.sleep(2)  # Simulate API call
    
    return f"## Section {section_num + 1}\n\nContent about {topic} in {style} style..."
```

### File 2: Endpoint (`app.py`)

```python
# app.py - HTTP interface
import fastapi
from kodosumi.core import ServeAPI, Launch, InputsError
from kodosumi.core import forms as F
from ray import serve

app = ServeAPI()

# Define rich user interface
content_form = F.Model(
    F.Markdown("""
    # AI Content Generator
    
    Generate high-quality content using AI. Specify your topic and style,
    and our distributed AI system will create comprehensive content.
    """),
    F.Errors(),
    F.Break(),
    
    F.InputText(
        label="Topic", 
        name="topic",
        placeholder="e.g., Quantum Computing, Climate Change"
    ),
    
    F.Select(label="Writing Style", name="style", option=[
        F.InputOption(label="Professional", name="professional"),
        F.InputOption(label="Academic", name="academic"),
        F.InputOption(label="Casual Blog", name="casual"),
        F.InputOption(label="Technical Documentation", name="technical"),
    ], value="professional"),
    
    F.InputNumber(
        label="Number of Sections", 
        name="sections",
        min_value=1, 
        max_value=10, 
        value=3
    ),
    
    F.Checkbox(
        label="Include examples", 
        name="examples", 
        value=True,
        option="Add practical examples to each section"
    ),
    
    F.InputArea(
        label="Additional Instructions", 
        name="instructions",
        placeholder="Any specific requirements or focus areas..."
    ),
    
    F.Submit("Generate Content"),
    F.Cancel("Cancel"),
)

@app.enter(
    path="/",
    model=content_form,
    summary="AI Content Generator",
    description="Generate comprehensive content on any topic using distributed AI",
    version="2.0.0",
    author="ai-team@example.com",
    tags=["AI", "Content", "Generation"]
)
async def enter(request: fastapi.Request, inputs: dict):
    """Handle form submission and launch generation"""
    
    # Validate inputs
    error = InputsError()
    
    if not inputs.get("topic"):
        error.add(topic="Please provide a topic for content generation")
    
    if len(inputs.get("topic", "")) < 3:
        error.add(topic="Topic must be at least 3 characters long")
        
    if error.has_errors():
        raise error
    
    # Launch the content generation
    return Launch(
        request,
        "generator:generate_content",  # Path to entrypoint
        inputs={
            "topic": inputs["topic"],
            "style": inputs["style"],
            "sections": inputs.get("sections", 3),
            "examples": inputs.get("examples", False),
            "instructions": inputs.get("instructions", "")
        }
    )

# Ray deployment
@serve.deployment(
    ray_actor_options={
        "num_cpus": 1,
        "memory": 2 * 1024 * 1024 * 1024  # 2GB
    }
)
@serve.ingress(app)
class ContentGenerator:
    pass

fast_app = ContentGenerator.bind()

# For local debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8005, reload=True)
```

### File 3: Configuration (`config.yaml`)

```yaml
# Server settings
proxy_location: EveryNode
http_options:
  host: 0.0.0.0
  port: 8001
logging_config:
  encoding: TEXT
  log_level: INFO
  enable_access_log: true

# Application deployment
applications:
  - name: content-generator
    route_prefix: /generator
    import_path: app:fast_app
    runtime_env:
      pip:
        - openai
        - anthropic
        - langchain
      env_vars:
        PYTHONPATH: .
        OPENAI_API_KEY: ${OPENAI_API_KEY}
```

## 🔄 Development Workflow

1. **Create your service** with proper serve.py structure
2. **Write config.yaml** with dependencies
3. **Start Ray**: `ray start --head`
4. **Deploy**: `serve deploy config.yaml`
5. **Start Kodosumi**: `koco start --register http://localhost:8001/-/routes`
6. **Access admin panel**: http://localhost:3370 (admin/admin)
7. **Launch your service** from the Flow screen
8. **View results** in Timeline

## 🔍 Debugging Tips

### Check Logs
```bash
# Ray logs
ray logs

# Kodosumi logs (based on your logging_config)
# If logs_dir is set, check that directory
# Otherwise, logs appear in terminal
```

### Test Your Service Locally First
```python
# Add to your app.py for local testing
if __name__ == "__main__":
    import uvicorn
    # Test without Ray/Kodosumi
    uvicorn.run("app:app", host="0.0.0.0", port=8003, reload=True)
```

### Verify Deployment
1. Check Ray dashboard: http://localhost:8265/#/serve
2. Look for your service in "Serve Deployments"
3. Verify status is "HEALTHY"
4. Check replica count matches expectations

### Monitor Performance
- Ray dashboard shows request metrics
- Check CPU/memory usage per replica
- Monitor request latency
- Scale replicas if needed in deployment config

## 🔗 Key Resources

- **Kodosumi GitHub**: https://github.com/masumi-network/kodosumi
- **Ray Documentation**: https://docs.ray.io
- **Example Services** in kodosumi repo:
  - `apps/my_service/` - Simple calculation service
  - `apps/prime/` - Prime number calculation
  - `apps/form/` - Form handling examples
  - `apps/throughput/` - Performance testing
  - `apps/hymn/` - AI integration with CrewAI
- **Default Ports**:
  - Kodosumi Admin: 3370
  - Ray Dashboard: 8265
  - Ray Serve: 8001 (configurable)
  - gRPC: 9000 (configurable)
  - Uvicorn Debug: 8005 (or any port)

## 💡 Key Success Factors

1. **Two-Part Architecture**: Separate endpoint (app.py) from entrypoint (calc.py)
2. **Use Launch Object**: Bridge between endpoint and entrypoint with `Launch(request, "module:function", inputs)`
3. **Tracer for Updates**: Use `await tracer.markdown()` for real-time progress
4. **Form Builder**: Prefer `@app.enter` with `forms.Model` for rich UIs
5. **Ray Remote**: Use `@ray.remote` for distributed tasks
6. **Always Bind**: `fast_app = YourClass.bind()` for deployment
7. **Error Handling**: Raise `InputsError` with field-specific messages
8. **Test Locally**: Use uvicorn mode for debugging without Ray
9. **Register Services**: Use `--register` flag or refresh routes in admin
10. **Check Dashboards**: Monitor Kodosumi (3370) and Ray (8265)

### Common Patterns

```python
# Endpoint pattern
@app.enter(path="/", model=form_model)
async def enter(request, inputs):
    # Validate
    if error:
        raise InputsError()
    # Launch
    return Launch(request, "module:function", inputs)

# Entrypoint pattern
async def execute(inputs, tracer):
    # Create Ray tasks
    futures = [task.remote(x) for x in items]
    # Track progress
    await tracer.markdown("Processing...")
    # Return results
    return results

# Ray task pattern
@ray.remote
def task(item):
    # Heavy computation
    return result
```

Remember: Kodosumi = Endpoint (forms) → Launch → Entrypoint (logic) → Ray (distribution)

## 🎯 Returning Final Results to Kodosumi UI

### Critical Learning: Using core.response.Markdown() for Final Results

**Problem**: When returning final analysis results from entrypoint functions, using `tracer.markdown()` or `tracer.result()` causes the results to display in the wrong section of the Kodosumi UI. Results appear under "STR" instead of "FINAL" and are not rendered as markdown.

**Solution**: Use `core.response.Markdown()` to return final results properly:

```python
# WRONG: Results show under "STR" section, not rendered as markdown
async def my_entrypoint(inputs: dict, tracer: Tracer):
    # ... processing logic ...
    await tracer.markdown("Processing complete!")
    await tracer.result(final_report)  # ❌ Wrong section
    return {"status": "complete"}

# CORRECT: Results show under "FINAL" section with proper markdown rendering  
import kodosumi.core as core

async def my_entrypoint(inputs: dict, tracer: Tracer):
    # ... processing logic ...
    await tracer.markdown("Processing complete!")
    
    # Generate final report content
    final_report = generate_markdown_report()
    
    # Return using core.response.Markdown for proper display
    return core.response.Markdown(final_report)  # ✅ Correct section and rendering
```

### Key Differences

| Method | Display Section | Markdown Rendering | Use Case |
|--------|----------------|-------------------|----------|
| `tracer.markdown()` | Progress updates | ✅ Yes | Real-time progress during execution |
| `tracer.result()` | STR section | ❌ No | ⚠️ Avoid for final results |
| `core.response.Markdown()` | FINAL section | ✅ Yes | ✅ Final results and reports |

### Complete Example

```python
# political_analyzer.py - Proper final result handling
import kodosumi.core as core
from kodosumi.core import Tracer

async def execute_analysis(inputs: dict, tracer: Tracer):
    """Political analysis entrypoint with proper result display"""
    
    # Progress updates during processing
    await tracer.markdown("## Starting Political Analysis")
    await tracer.markdown("### Step 1: Loading documents...")
    
    # ... workflow execution logic ...
    
    await tracer.markdown("### Step 3: Analysis complete!")
    
    # Generate final report
    execution_summary = f"""
# Political Analysis Complete 🎉

## Configuration
- Documents Processed: {doc_count}
- Storage Mode: {'Azure' if use_azure else 'Local'}
- Processing Time: {processing_time:.1f}s

## Status
✅ Analysis completed successfully
"""

    # Read the generated report file
    report_content = read_final_report()
    
    # Combine summary and detailed report
    full_report = execution_summary + "\n\n" + report_content
    
    # CRITICAL: Use core.response.Markdown() for proper Kodosumi display
    return core.response.Markdown(full_report)
```

### Import Requirements

```python
# Required import for proper result handling
import kodosumi.core as core

# Also ensure you have the Tracer import for progress updates
from kodosumi.core import Tracer
```

### Troubleshooting Final Results

If your final results are not displaying correctly:

1. **Check import**: Ensure `import kodosumi.core as core` is present
2. **Verify return statement**: Use `return core.response.Markdown(content)` not `return content`
3. **Test markdown content**: Ensure your content is valid markdown
4. **Remove conflicting returns**: Don't use both `tracer.result()` and `core.response.Markdown()`

This pattern ensures that final analysis reports display in the correct "FINAL" section of the Kodosumi UI with proper markdown rendering, providing users with a clear, formatted view of results.