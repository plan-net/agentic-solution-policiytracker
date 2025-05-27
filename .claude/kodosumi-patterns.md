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
    
    # CRITICAL: Always return core.response.Markdown for final display
    await tracer.markdown("### ✅ Analysis Complete! Report ready for viewing.")
    return core.response.Markdown(execution_summary + report_content)
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

## Final Response Pattern (CRITICAL)

**❌ WRONG - Never return raw dict/data:**
```python
return {"status": "success", "results": data}
```

**✅ CORRECT - Always return Markdown response:**
```python
from kodosumi import core

# Generate comprehensive report content
execution_summary = f"# {job_name} - Final Report\n\n..."
report_content = f"## Results\n\n..."

# Return proper Kodosumi Markdown response for display
await tracer.markdown("### ✅ Analysis Complete! Report ready for viewing.")
return core.response.Markdown(execution_summary + report_content)
```

**Why This Matters:**
- Raw dict returns display poorly in Kodosumi UI
- Users expect professional, formatted reports
- Markdown responses render properly with styling
- Enables rich content (links, code blocks, tables)
- Provides actionable next steps and documentation

**Report Content Should Include:**
- Executive summary with key metrics
- Detailed processing results
- Next steps with actionable guidance
- Technical details and references
- Error handling with troubleshooting steps