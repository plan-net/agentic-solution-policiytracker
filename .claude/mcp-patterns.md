# MCP (Model Context Protocol) Patterns

## Overview
For v0.2.0, we're using MCP servers to interact with Graphiti and Neo4j, avoiding Python dependency conflicts while providing clean API boundaries.

## Architecture
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Python App     │     │  Claude Code    │     │  Other Clients  │
│  (LangChain)    │     │  (Direct MCP)   │     │  (Future)       │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         └───────────────────────┴─────────────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   MCP Protocol  │
                        └────────┬────────┘
                                 │
                ┌────────────────┴────────────────┐
                │                                 │
        ┌───────▼────────┐               ┌───────▼────────┐
        │  Graphiti MCP  │               │ Neo4j Memory   │
        │  Server        │               │ MCP Server     │
        │  (Port 8765)   │               │ (Port 8766)    │
        └───────┬────────┘               └───────┬────────┘
                │                                 │
                └─────────────┬───────────────────┘
                              │
                      ┌───────▼────────┐
                      │    Neo4j DB    │
                      │ (Port 7687)    │
                      └────────────────┘
```

## MCP Server Usage

### Graphiti MCP Server
**Purpose**: Temporal knowledge graph operations
**Port**: 8765

**Key Operations**:
- `add_episode()` - Add documents/events with timestamps
- `search()` - Temporal and semantic search
- `get_entity_mentions()` - Entity history over time
- `delete_episode()` - Remove temporal data
- `clear()` - Clear entire graph

**Example Usage**:
```python
# Via LangChain MCP adapter
from langchain_mcp_adapters import GraphitiMCPClient

client = GraphitiMCPClient(host="localhost", port=8765)

# Add political document as episode
await client.add_episode(
    name="EU_AI_Act_Amendment",
    content=document_text,
    timestamp=datetime(2024, 3, 15),
    metadata={"type": "legislation", "jurisdiction": "EU"}
)

# Search with time range
results = await client.search(
    query="AI regulation changes",
    time_range=(start_date, end_date)
)
```

### Neo4j Memory MCP Server
**Purpose**: Entity tracking with observations
**Installation**: Via uvx (mcp-neo4j-memory@0.1.3)

**Key Operations**:
- `create_entity()` - Create political entities
- `add_observation()` - Track changes/events
- `create_relation()` - Link entities
- `search_nodes()` - Find entities
- `read_graph()` - Explore relationships

**Example Usage**:
```python
# Via LangChain MCP adapter
from langchain_mcp_adapters import Neo4jMemoryMCPClient

client = Neo4jMemoryMCPClient(host="localhost", port=8766)

# Track policy evolution
await client.create_entity(
    name="EU AI Act",
    type="Policy",
    properties={"status": "proposed", "jurisdiction": "EU"}
)

# Add temporal observation
await client.add_observation(
    entity="EU AI Act",
    observation="Parliament approved with amendments",
    timestamp=datetime.now()
)
```

## Integration Patterns

### Pattern 1: Document Processing Pipeline
```python
async def process_political_document(doc_path: str):
    # 1. Extract text
    content = extract_text(doc_path)
    
    # 2. Add to Graphiti as episode
    episode_id = await graphiti_client.add_episode(
        name=doc_path.stem,
        content=content,
        timestamp=extract_date(content)
    )
    
    # 3. Extract entities via Graphiti
    entities = await graphiti_client.extract_entities(episode_id)
    
    # 4. Track key entities in Neo4j Memory
    for entity in entities:
        if entity.type in ["Policy", "Politician", "Organization"]:
            await neo4j_client.create_entity(
                name=entity.name,
                type=entity.type,
                properties=entity.properties
            )
```

### Pattern 2: Temporal Query
```python
async def what_changed_this_week(client_name: str):
    # 1. Query Graphiti for recent changes
    changes = await graphiti_client.search(
        query=f"{client_name} regulatory changes",
        time_range=(datetime.now() - timedelta(days=7), datetime.now())
    )
    
    # 2. Get entity observations from Neo4j
    for change in changes:
        observations = await neo4j_client.get_observations(
            entity=change.entity,
            since=datetime.now() - timedelta(days=7)
        )
```

### Pattern 3: Relevance Assessment
```python
async def assess_relevance(event: dict, client: dict):
    # 1. Check temporal proximity via Graphiti
    related_events = await graphiti_client.search(
        query=event["description"],
        time_range=(event["date"] - timedelta(days=30), event["date"])
    )
    
    # 2. Check entity relationships via Neo4j
    impact_paths = await neo4j_client.find_paths(
        from_entity=event["entity"],
        to_entities=client["key_entities"],
        max_hops=3
    )
```

## Best Practices

### 1. Use Both Servers Complementarily
- Graphiti: Document ingestion, temporal queries
- Neo4j Memory: Entity state, relationship tracking

### 2. Error Handling
```python
try:
    result = await client.operation()
except MCPConnectionError:
    # Fallback to direct Neo4j queries
    result = await direct_neo4j_query()
```

### 3. Batch Operations
```python
# Good: Batch entity creation
entities = [...]
await neo4j_client.create_entities_batch(entities)

# Bad: Individual calls in loop
for entity in entities:
    await neo4j_client.create_entity(entity)
```

### 4. Claude Code Integration
When working in Claude Code:
- MCP servers must be running in Docker
- Use .mcp.json configuration (note the dot!)
- Claude can directly query both servers
- Test queries before implementing in code

## Troubleshooting

### Connection Issues
```bash
# Check if MCP servers are running
docker ps | grep mcp

# Test Graphiti connection
curl http://localhost:8765/health

# Test Neo4j Memory connection
curl http://localhost:8766/health
```

### Performance Optimization
- Use time ranges to limit query scope
- Cache frequently accessed entities
- Batch operations when possible
- Monitor Neo4j query performance

## Migration from Direct Neo4j
```python
# Old: Direct Neo4j GraphRAG
kg_pipeline = SimpleKGPipeline(driver=driver)
result = kg_pipeline.run(file_path)

# New: Via MCP
episode_id = await graphiti_client.add_episode(
    name=file_path.name,
    content=read_file(file_path)
)
entities = await graphiti_client.extract_entities(episode_id)
```