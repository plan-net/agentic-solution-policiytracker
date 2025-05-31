# Kodosumi v0.2.0 Flow Patterns

## v0.2.0 Flow Architecture (Current)
Kodosumi flows in v0.2.0 use specialized flow structure:
- `src/flows/data_ingestion/app.py` - Kodosumi flow endpoint
- `src/flows/data_ingestion/document_processor.py` - Business logic entrypoint
- `src/flows/data_ingestion/report_generator.py` - Output generation

## Flow Endpoint Pattern
```python
# src/flows/data_ingestion/app.py
from kodosumi import ServeAPI, Launch
from src.flows.data_ingestion.forms import DataIngestionForm

app = ServeAPI()

@app.enter(path="/", model=DataIngestionForm, version="0.2.0")
async def enter(request, inputs):
    # Form validation with InputsError
    if inputs.errors:
        raise InputsError(inputs.errors)
    
    # Launch business logic entrypoint
    return Launch("src.flows.data_ingestion.document_processor:process_documents")
```

## Flow Entrypoint Pattern
```python
# src/flows/data_ingestion/document_processor.py
from kodosumi import core, Tracer
import ray

async def process_documents(inputs: dict, tracer: Tracer):
    # Progress tracking
    await tracer.markdown("🚀 Starting document processing pipeline...")
    
    # Ray task creation
    @ray.remote
    class DocumentProcessor:
        async def process(self, documents):
            # Processing logic
            return results
    
    # Execute processing
    processor = DocumentProcessor.remote()
    results = await processor.process.remote(inputs.documents)
    
    # Generate report
    from src.flows.data_ingestion.report_generator import generate_report
    report_content = await generate_report(results)
    
    # CRITICAL: Return Markdown response
    await tracer.markdown("✅ Processing complete!")
    return core.response.Markdown(report_content)
```

## Flow Deployment Pattern
```python
# config.yaml - Ray Serve configuration
flows:
  flow1-data-ingestion:
    import_path: src.flows.data_ingestion.app:app
    route_prefix: /data-ingestion
    num_replicas: 1
    ray_actor_options:
      num_cpus: 2
      memory: 4000000000
```

## Development Commands
```bash
# Deploy flows
just deploy-all              # Deploy all flows
just deploy-data-ingestion   # Deploy specific flow

# Test flows
just test-flows              # Test all flows
just status                  # Check deployment status

# Access flows
# Kodosumi Admin: http://localhost:3370 (admin/admin)  
# Flow endpoint: http://localhost:8001/data-ingestion
```

## Flow Structure Best Practices

### File Organization
```
src/flows/data_ingestion/
├── app.py                  # Kodosumi endpoint (lightweight)
├── document_processor.py   # Main business logic
├── report_generator.py     # Output formatting
├── forms.py               # Pydantic form models
└── __init__.py            # Flow exports
```

### Form Model Pattern
```python
# src/flows/data_ingestion/forms.py
from kodosumi import F
from pydantic import BaseModel, Field

class DataIngestionForm(BaseModel):
    documents: F.Files = Field(
        description="Upload documents for analysis",
        extensions=[".pdf", ".docx", ".md", ".txt"]
    )
    processing_mode: F.Select = Field(
        default="comprehensive",
        options=["quick", "comprehensive", "detailed"]
    )
    include_graph_update: F.Checkbox = Field(
        default=True,
        description="Update knowledge graph with new entities"
    )
```

## Progress Tracking Patterns

### Tracer Usage
```python
async def process_documents(inputs: dict, tracer: Tracer):
    total_docs = len(inputs.documents)
    
    # Stage progress
    await tracer.markdown(f"📊 Processing {total_docs} documents...")
    await tracer.markdown("🔍 Stage 1: Document extraction...")
    
    # Processing with updates
    for i, doc in enumerate(inputs.documents, 1):
        await tracer.markdown(f"📄 Processing document {i}/{total_docs}: {doc.name}")
        # Process document...
    
    await tracer.markdown("🧠 Stage 2: Knowledge graph integration...")
    # Graph processing...
    
    await tracer.markdown("📝 Stage 3: Report generation...")
    # Report generation...
```

## Response Formatting

### Markdown Report Pattern
```python
def generate_execution_summary(results):
    return f"""# Document Processing Complete

## Summary
- **Documents Processed**: {results['processed']} of {results['total']}
- **Entities Extracted**: {results['entities']}
- **Processing Time**: {results['duration']:.1f}s
- **Knowledge Graph Updated**: {'✅ Yes' if results['graph_updated'] else '❌ No'}

## Next Steps
1. Review extracted entities in knowledge graph
2. Use chat interface to query new information
3. Check data quality metrics in dashboard

[View Knowledge Graph](http://localhost:7474) | [Chat Interface](http://localhost:3000)
"""
```

### Error Handling Pattern
```python
async def process_documents(inputs: dict, tracer: Tracer):
    try:
        # Processing logic
        results = await process_all_documents(inputs.documents)
        
        if results['errors']:
            await tracer.markdown(f"⚠️ Completed with {len(results['errors'])} errors")
            
        # Generate success report
        report = generate_execution_summary(results)
        return core.response.Markdown(report)
        
    except Exception as e:
        await tracer.markdown(f"❌ Processing failed: {str(e)}")
        error_report = generate_error_report(e, inputs)
        return core.response.Markdown(error_report)
```

## Integration with v0.2.0 Components

### Knowledge Graph Integration
```python
# Update Graphiti knowledge graph
from src.graphrag.political_document_processor import PoliticalDocumentProcessor

async def process_documents(inputs: dict, tracer: Tracer):
    # Document processing
    await tracer.markdown("🧠 Updating knowledge graph...")
    
    processor = PoliticalDocumentProcessor()
    for doc_path in processed_documents:
        await processor.process_document(doc_path)
    
    await tracer.markdown("✅ Knowledge graph updated")
```

### ETL Pipeline Integration
```python
# Trigger ETL collection after processing
from src.etl.utils.initialization_tracker import InitializationTracker

async def process_documents(inputs: dict, tracer: Tracer):
    # Document processing
    
    # Optional: Trigger related data collection
    if inputs.trigger_related_collection:
        await tracer.markdown("🔄 Triggering related document collection...")
        tracker = InitializationTracker()
        # Trigger collection logic
```

## Common Anti-Patterns

❌ **Legacy v0.1.0 structure**:
```python
# DON'T: Use old app.py + political_analyzer.py pattern
# src/app.py + src/political_analyzer.py (REMOVED in v0.2.0)
```

❌ **Business logic in endpoint**:
```python
# DON'T: Put processing logic in app.py
@app.enter(path="/", model=form)
async def enter(request, inputs):
    # Heavy processing here - WRONG!
    results = complex_processing(inputs)
```

❌ **Raw data returns**:
```python
# DON'T: Return raw dictionaries
return {"status": "success", "data": results}

# DO: Return formatted Markdown
return core.response.Markdown(formatted_report)
```

## Testing Flow Patterns

### Flow Testing Structure
```python
# tests/integration/test_data_ingestion_flow.py
async def test_document_processing_flow():
    # Test with sample documents
    inputs = {"documents": sample_documents}
    
    # Mock tracer
    tracer = MagicMock()
    
    # Test entrypoint
    result = await process_documents(inputs, tracer)
    
    # Verify response format
    assert isinstance(result, core.response.Markdown)
    assert "Documents Processed" in result.content
    
    # Verify tracer calls
    tracer.markdown.assert_called()
```

## Performance Optimization

### Ray Configuration
```python
# Optimal Ray actor options for document processing
ray_actor_options = {
    "num_cpus": 2,                    # CPU-intensive processing
    "memory": 4000000000,             # 4GB memory for large documents
    "max_concurrency": 4,             # Parallel document processing
}
```

### Batch Processing Pattern
```python
@ray.remote
class BatchDocumentProcessor:
    async def process_batch(self, documents_batch):
        # Process documents in parallel
        tasks = [self.process_single(doc) for doc in documents_batch]
        return await asyncio.gather(*tasks)

# Usage in flow
processor = BatchDocumentProcessor.remote()
batch_size = 5
for i in range(0, len(documents), batch_size):
    batch = documents[i:i + batch_size]
    await processor.process_batch.remote(batch)
```