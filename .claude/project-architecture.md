# Political Monitoring Agent v0.2.0 - Architecture Patterns

## Core v0.2.0 Architecture

### Primary Components
- **Chat Interface**: Multi-agent orchestration with 15 knowledge graph tools
- **ETL Pipelines**: Automated data collection via Airflow DAGs
- **Kodosumi Flows**: Document processing workflows (NOT legacy app.py)
- **Graphiti Knowledge Graph**: Temporal entity tracking with direct API
- **Ray Deployment**: Distributed chat server + data ingestion flows

### Key Architecture Shifts from v0.1.0
```
v0.1.0 (REMOVED)              v0.2.0 (CURRENT)
├─ src/app.py              →  ├─ src/chat/server/app.py
├─ src/political_analyzer  →  ├─ src/flows/data_ingestion/app.py  
├─ src/workflow/           →  ├─ src/chat/agent/orchestrator.py
├─ src/analysis/           →  ├─ src/etl/collectors/
└─ src/scoring/            →  └─ src/graphrag/
```

## File Structure Patterns

### Chat Interface
```
src/chat/
├── server/app.py           # FastAPI server with OpenAI-compatible API
├── agent/orchestrator.py   # LangGraph multi-agent workflow
├── agent/agents.py         # 4 specialized agents
└── tools/                  # 15 knowledge graph tools
```

### Kodosumi Flows (v0.2.0)
```
src/flows/data_ingestion/
├── app.py                  # Kodosumi flow endpoint
├── document_processor.py   # Core processing logic
└── report_generator.py     # Output generation
```

### ETL Pipelines
```
src/etl/
├── dags/                   # Airflow DAG definitions
├── collectors/             # News/policy data collection
└── transformers/           # Markdown conversion
```

## Deployment Patterns

### Ray Services Architecture
```yaml
ray_serve:
  chat-server:              # Port 8001
    route: /v1/chat/completions
    replicas: 1
  flow1-data-ingestion:     # Port 8001  
    route: /data-ingestion
    replicas: 1
```

### Service Dependencies
```
Open WebUI (3000) → Chat API (8001) → Neo4j (7687)
Kodosumi (3370) → Data Ingestion Flow (8001) → Azurite (10000)
Airflow (8080) → ETL Collectors → Exa.ai API
```

## Development Patterns

### Two-File Kodosumi Pattern (v0.2.0)
```python
# src/flows/data_ingestion/app.py - Kodosumi endpoint
app = ServeAPI()

@app.enter(path="/", model=form, version="0.2.0")
async def enter(request, inputs):
    return Launch("src.flows.data_ingestion.document_processor:process_documents")

# src/flows/data_ingestion/document_processor.py - Business logic
async def process_documents(inputs: dict, tracer: Tracer):
    # Use tracer.markdown() for progress
    # Return core.response.Markdown() for display
```

### Multi-Agent Chat Pattern
```python
# 4-agent workflow: understand → plan → execute → synthesize
workflow = StateGraph(MultiAgentState)
workflow.add_node("query_understanding", self._query_understanding_node)
workflow.add_node("tool_planning", self._tool_planning_node)
workflow.add_node("tool_execution", self._tool_execution_node)
workflow.add_node("response_synthesis", self._response_synthesis_node)
```

## Configuration Patterns

### Client Context Structure
```yaml
# data/context/client.yaml
company_terms: ["company_name"]
core_industries: ["industry"]
topic_patterns:
  data-protection: ["gdpr", "privacy"]
  ecommerce-regulation: ["dsa", "marketplace"]
```

### ETL Collection Flows
```
Flow 1: Policy Landscape (Weekly)
└── EU regulations → data/input/policy/YYYY-MM/

Flow 2: Client News (Daily)  
└── Company news → data/input/news/YYYY-MM/
```

## Storage Patterns

### Document Processing Pipeline
```
Input: data/input/policy/2025-05/document.md
Process: Graphiti temporal knowledge graph
Output: Neo4j entities + relationships
Query: Chat interface with 15 tools
```

### Azure Storage Integration
```
Local Development: Azurite (localhost:10000)
Production: Azure Blob Storage
Containers: input-documents, reports, checkpoints, contexts
```

## Integration Patterns

### Knowledge Graph Tools (15 total)
- **Entity Tools**: Details, relationships, timeline, search
- **Network Tools**: Traversal, centrality, paths, communities  
- **Temporal Tools**: Changes, timeline, comparison
- **Search Tools**: Semantic, reranking, exploration

### LLM Observability
- **Langfuse Integration**: Prompt management + tracing
- **Local Fallback**: YAML frontmatter prompts in src/prompts/
- **Memory Caching**: PromptManager with fallback hierarchy

## Testing Patterns

### Component Testing
```python
# Test chat interface end-to-end
async def test_chat_workflow():
    response = await chat_client.complete("What is EU AI Act?")
    assert "thinking" in response
    assert "tools_used" in response.metadata

# Test ETL collectors  
async def test_policy_collection():
    collector = PolicyLandscapeCollector()
    results = await collector.collect_documents()
    assert results['documents_saved'] > 0
```

### Integration Testing
- **Multi-agent workflows**: Full chat pipeline testing
- **Knowledge graph tools**: Tool execution validation
- **ETL pipelines**: End-to-end data collection
- **Ray deployment**: Service health and communication

## Common Anti-Patterns to Avoid

❌ **Using legacy v0.1.0 patterns**:
- Don't create src/app.py + src/political_analyzer.py
- Don't use src/workflow/ LangGraph structure
- Don't implement hybrid scoring in src/scoring/

❌ **Wrong Kodosumi patterns**:
- Don't put business logic in app.py endpoint
- Don't forget tracer.markdown() progress updates
- Don't return raw dict instead of core.response.Markdown()

❌ **Chat interface mistakes**:
- Don't create multiple <think> blocks in streaming
- Don't use fixed routing instead of Command handoffs
- Don't dump raw JSON state in reasoning

## v0.2.0 Success Metrics

### Architecture Health
- **Services Running**: 8 Docker services + Ray + chat server
- **API Response**: <2s for chat queries, <30s for document processing
- **Knowledge Graph**: >1000 entities, >5000 relationships
- **ETL Pipeline**: Daily news collection, weekly policy updates

### User Experience  
- **Chat Interface**: Natural language queries with tool recommendations
- **Document Processing**: Batch upload via Kodosumi with progress tracking
- **Data Quality**: >90% entity extraction accuracy, <5% duplicate documents