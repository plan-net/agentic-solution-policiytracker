# Kodosumi Implementation Patterns

## Two-File Architecture Pattern
Always implement Kodosumi agents with this structure:
- `src/app.py` - Endpoint with rich forms, validation, and Launch() calls
- `src/political_analyzer.py` - Entrypoint with business logic and Ray tasks

## Endpoint Pattern (app.py)
```python
# Use this structure for Kodosumi endpoints:
app = ServeAPI()

# Rich form with F.Model, F.Errors(), validation
@app.enter(path="/", model=form, version="0.1.0")
async def enter(request, inputs):
    # Validate with InputsError
    # Launch entrypoint: "src.political_analyzer:execute_analysis"
```

## Entrypoint Pattern 
```python
async def execute_analysis(inputs: dict, tracer: Tracer):
    # Use tracer.markdown() for progress updates
    # Create Ray tasks with @ray.remote
    # Monitor progress with ray.wait()
```

## Key Commands
- Deploy: `just dev` or `just kodosumi-deploy`
- Quick restart: `just dev-quick`
- Test forms at: http://localhost:3370 (admin/admin)

## Important Patterns
- Always use absolute imports: `src.module:function`
- Set ray_actor_options: `{"num_cpus": 2, "memory": 4000000000}`
- Use Tracer for real-time progress streaming
- Handle errors with proper error.add() pattern