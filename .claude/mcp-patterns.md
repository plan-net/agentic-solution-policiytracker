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

### Graph Retrieval MCP Server
**Purpose**: Knowledge graph search and retrieval with hybrid semantic search
**Port**: 8003 (SSE transport)
**Location**: `src/mcp/graph_retrieval/server.py`

**Key Operations**:
- `search_knowledge_graph` - Search entities, relationships, and source documents
- `search_documents` - Semantic search over episodic nodes (source documents)
- `analyze_query` - Understand query intent before searching
- `get_entity_info` - Get detailed information about a specific entity
- `find_relationships` - Explore connections between entities
- `graph_statistics` - Get knowledge graph statistics

**Hybrid Search Architecture** (v0.2.1):
The MCP server now supports hybrid search combining:
1. **BM25 fulltext search** - Keyword-based matching on content and names
2. **Vector similarity search** - Semantic search using embeddings (1536-dim, cosine)

Score fusion weights:
- Entity search: 0.4 * keyword + 0.6 * vector
- Relationship search: 0.3 * keyword + 0.7 * vector
- Episode search: 0.3 * BM25 + 0.7 * vector

### Graphiti MCP Server (Legacy)
**Purpose**: Temporal knowledge graph operations
**Port**: 8000 (SSE transport)

**Key Operations**:
- `add_episode()` - Add documents/events with timestamps
- `search()` - Temporal and semantic search
- `get_entity_mentions()` - Entity history over time
- `delete_episode()` - Remove temporal data
- `clear()` - Clear entire graph

**Example Usage**:
```python
# Direct MCP communication (Claude Code)
# MCP server accessible when Docker containers running

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
**Deployment**: Docker container via docker-compose.yml

**Key Operations**:
- `create_entity()` - Create political entities
- `add_observation()` - Track changes/events
- `create_relation()` - Link entities
- `search_nodes()` - Find entities
- `read_graph()` - Explore relationships

**Example Usage**:
```python
# Direct MCP communication (Claude Code)
# Available when MCP servers running in Docker

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

## Episode Semantic Search (v0.2.1)

### Overview
Episodic nodes contain the chunked source documents used to build the knowledge graph. These nodes now support semantic search via content embeddings, enabling retrieval of relevant source passages alongside entities and relationships.

### Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    Graph Retrieval MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│  search_knowledge_graph()                                        │
│    ├── _search_entities_hybrid()   (keyword + vector)           │
│    ├── _search_relationships_hybrid() (keyword + vector)        │
│    └── _search_episodes()          (BM25 + vector)              │
│                                                                  │
│  search_documents()  ──────────────► _search_episodes()         │
└─────────────────────────────────────────────────────────────────┘
```

### Database Indexes
```sql
-- Vector index for semantic search on episode content
CREATE VECTOR INDEX episodic_content_embedding_index IF NOT EXISTS
FOR (ep:Episodic) ON (ep.content_embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}

-- Fulltext index for BM25 search
CREATE FULLTEXT INDEX episodic_content_fulltext IF NOT EXISTS
FOR (ep:Episodic) ON EACH [ep.content, ep.name]
```

### Episode Embedding Management
**File**: `src/graphrag/episode_embedding_manager.py`

```python
from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager

# Initialize manager
manager = EpisodeEmbeddingManager()

# Add embedding to existing episode
await manager.add_content_embedding(episode_uuid, content)

# Check embedding coverage
stats = await manager.get_embedding_stats()
# Returns: {total_episodes, episodes_with_embeddings, coverage_percentage}

# Find episodes without embeddings (for backfill)
episodes = await manager.get_episodes_without_embeddings(limit=100)
```

### Backfill Script
**File**: `scripts/backfill_episode_embeddings.py`

```bash
# Dry run to estimate cost
just backfill-episodes-dry

# Full backfill with default batch size (50)
just backfill-episodes

# Custom batch size
just backfill-episodes 100

# Backfill limited episodes (testing)
just backfill-episodes-test 50

# Check embedding coverage
just check-episode-embeddings
```

**Cost Estimate**:
- Initial backfill: ~$0.19 (7,611 episodes, ~9.5M tokens)
- Ongoing: ~$0.50/month (~173 new episodes/day)
- Model: text-embedding-3-small at $0.02/1M tokens

### MCP Tool Usage

**search_documents** - Direct semantic search over source documents:
```python
# Via Claude agent
result = await mcp_client.call_tool("search_documents", {
    "query": "GDPR compliance requirements for data processors",
    "limit": 5
})
# Returns: List of episodic nodes with content previews and relevance scores
```

**search_knowledge_graph** - Unified search (entities + relationships + documents):
```python
# Now automatically includes source documents in results
result = await mcp_client.call_tool("search_knowledge_graph", {
    "query": "EU AI Act enforcement mechanisms"
})
# Returns: entities, relationships, AND source_documents
```

### Integration with Document Processor
New episodes automatically receive embeddings during ingestion:

```python
# In document_processor.py
from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager

embedding_manager = EpisodeEmbeddingManager()

# After adding episode via Graphiti
episode_uuid = result.episode.uuid
await embedding_manager.add_content_embedding(episode_uuid, chunk_text)
```

### Hybrid Search Query Pattern
```cypher
-- Example: Hybrid BM25 + Vector search on episodes
CALL {
    // BM25 fulltext search
    CALL db.index.fulltext.queryNodes('episodic_content_fulltext', $query)
    YIELD node, score AS bm25_score
    RETURN node, bm25_score, 0.0 AS vector_score
    LIMIT $limit

    UNION ALL

    // Vector similarity search
    MATCH (ep:Episodic)
    WHERE ep.content_embedding IS NOT NULL
    WITH ep, vector.similarity.cosine(ep.content_embedding, $embedding) AS vec_score
    WHERE vec_score > 0.3
    RETURN ep AS node, 0.0 AS bm25_score, vec_score AS vector_score
    ORDER BY vec_score DESC
    LIMIT $limit
}
WITH node, max(bm25_score) AS bm25, max(vector_score) AS vector
WITH node,
     CASE WHEN bm25 > 0 AND vector > 0 THEN (0.3 * bm25 + 0.7 * vector)
          WHEN vector > 0 THEN vector
          ELSE bm25 END AS combined_score
ORDER BY combined_score DESC
LIMIT $limit
RETURN node.uuid, node.name, node.content, combined_score
```