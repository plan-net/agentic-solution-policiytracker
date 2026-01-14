# Graphiti Implementation Patterns

## Overview
Graphiti is a temporal knowledge graph system that provides advanced entity extraction, relationship mapping, and community detection. This document captures our learnings for implementing Graphiti in the Political Monitoring Agent v0.2.0.

## Key Architecture Decision

### Direct API vs MCP Server
**✅ RECOMMENDED: Direct Graphiti API**
- Full access to custom entity types
- Advanced search capabilities  
- Community detection for policy clustering
- Complete CRUD operations
- Better performance (no network overhead)

**⚠️ SUPPLEMENTARY: MCP Server**
- Limited to predefined entity types (Requirement, Preference, Procedure)
- Good for Claude Code interactions
- Simplified interface for basic operations

## Core Implementation Patterns

### 1. Client Initialization
```python
from graphiti_core import Graphiti
from datetime import datetime

# Initialize client
client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
await client.build_indices_and_constraints()
```

### 2. Episode Creation (Basic)
```python
result = await client.add_episode(
    name="Political Document Analysis",
    episode_body=document_text,
    source="text",
    source_description="Political document for entity extraction",
    reference_time=datetime.now()
)
```

### 3. Entity Extraction Results
Episodes automatically extract entities and create relationships:
```python
# Result contains extracted entities
print(f"Extracted entities: {len(result.nodes)}")
for node in result.nodes:
    print(f"- {node.name} (Type: {node.labels})")
```

### 4. Search Operations
```python
# Basic search (no 'limit' parameter)
results = await client.search("EU Digital Services Act")

# Results contain relevant entities and relationships
for node in results.nodes:
    print(f"Found: {node.name}")
```

### 5. Custom Entity Types (✅ CONFIRMED - In Production)
**Graphiti supports custom entity types via `political_schema_v4.py`**

We pass custom schema registries directly to `add_episode()`:

```python
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from src.graphrag.political_schema_v5 import (
    ENTITY_TYPE_REGISTRY_FULL,  # 28 entity types (20 general + 8 German Bundestag)
    EDGE_TYPE_REGISTRY_FULL,    # 52 edge types (37 v3 + 15 v4)
    EDGE_TYPE_MAP_FULL,         # Valid source-target-edge combinations
)

# Initialize Graphiti client
client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, llm_client=llm_client)
await client.build_indices_and_constraints()

# Add episode with custom schema
result = await client.add_episode(
    name="political_doc_example",
    episode_body=document_text,
    source=EpisodeType.text,
    source_description="Political document",
    reference_time=datetime.now(),
    group_id="political_monitoring_v2",

    # ✅ Custom schema parameters
    entity_types=ENTITY_TYPE_REGISTRY_FULL,  # Dict[str, Type[BaseModel]]
    edge_types=EDGE_TYPE_REGISTRY_FULL,      # Dict[str, Type[BaseModel]]
    edge_type_map=EDGE_TYPE_MAP_FULL,        # Dict[Tuple[str, str], List[str]]
)

# Result contains entities conforming to our schema
print(f"Extracted {len(result.nodes)} entities")
for node in result.nodes:
    print(f"- {node.name} (Type: {node.labels})")  # Labels match our 28 entity types
```

**Schema Structure (political_schema_v4.py):**
- **28 Entity Types**: 20 v3 (EU/multi-jurisdiction) + 8 German Bundestag
- **52 Edge Types**: 37 v3 + 15 German Bundestag
- **Edge Type Map**: Defines valid (source, target) → [edge_types] combinations

## Political Domain Schema (v4.0)

### Entity Types Registry (28 Total)
**Production schema from `src/graphrag/political_schema_v4.py`:**

```python
# V3 Entities (20) - EU and Multi-Jurisdiction
TIER_1_LEGISLATIVE = [
    "LegislativeProposal", "LegislativeBody", "Committee", "Document", "Vote"
]
TIER_2_OUTCOMES = ["Policy", "Regulation"]
TIER_3_ACTORS = [
    "Politician", "Person", "PoliticalParty", "GovernmentAgency", "LobbyGroup"
]
TIER_4_BUSINESS = ["Company", "Industry", "ComplianceObligation"]
TIER_5_PROCESS = ["ConsultationProcess", "EnforcementAction"]
TIER_6_GEOGRAPHIC = ["Jurisdiction"]
TIER_7_TECHNICAL = ["LegalFramework", "TechnicalStandard"]

# V4 German Bundestag Entities (8) - NEW
GERMAN_BUNDESTAG = [
    "Drucksache",          # Parliamentary documents (bills, motions, reports)
    "DrucksachePage",      # Individual pages from Drucksache PDFs
    "Plenarprotokoll",     # Plenary session transcripts
    "Vorgang",             # Legislative procedures/processes
    "Vorgangsposition",    # Stages within a Vorgang
    "Aktivitaet",          # Parliamentary activities
    "Wahlperiode",         # Electoral periods
    "BundestagPerson",     # Members of Bundestag
    "BundestagFraktion",   # Parliamentary groups
]
```

### Edge Types Registry (52 Total)
**Valid relationship types:**

```python
# V3 Edges (37) - Cross-Jurisdiction
JURISDICTION_EDGES = ["IN_JURISDICTION", "MEMBER_OF", "REPRESENTS"]
LEGISLATIVE_EDGES = ["PROPOSES", "SUBMITS_TO", "EXAMINES", "AMENDS_PROPOSAL", "VOTES_ON", "BECOMES"]
EU_GERMANY_EDGES = ["TRANSPOSES", "GOLD_PLATES", "INFRINGEMENT_AGAINST", "PRELIMINARY_REFERENCE"]
INFLUENCE_EDGES = ["INFLUENCES", "LOBBIES_FOR", "LOBBIES_AGAINST", "HAS_POSITION", "CONTRIBUTES", "AFFILIATED_WITH"]
BUSINESS_EDGES = ["AFFECTS", "SUBJECT_TO", "REQUIRES_COMPLIANCE", "OPERATES_IN", "COMPETES_IN"]
REGULATORY_EDGES = ["IMPLEMENTS", "ENFORCES", "DELEGATES_TO"]
TEMPORAL_EDGES = ["SUPERSEDES", "AMENDS", "TRIGGERS", "PRECEDES"]
REFERENCE_EDGES = ["REFERENCES", "HARMONIZES_WITH", "CONFLICTS_WITH"]
STAKEHOLDER_EDGES = ["ADVISES", "MONITORS"]

# V4 German Bundestag Edges (15) - NEW
GERMAN_EDGES = [
    "PART_OF_VORGANG",         # Vorgangsposition/Aktivität → Vorgang
    "INITIATES_VORGANG",       # Person/Fraktion → Vorgang
    "RELATES_TO_DRUCKSACHE",   # Vorgang → Drucksache
    "DEBATED_IN_PLENUM",       # Vorgang → Plenarprotokoll
    "SPEAKS_IN_PLENUM",        # Person → Plenarprotokoll
    "IN_WAHLPERIODE",          # Entity → Wahlperiode
    "MEMBER_OF_FRAKTION",      # Person → Fraktion
    "LEADS_FRAKTION",          # Person → Fraktion
    "REPRESENTS_WAHLKREIS",    # Person → Jurisdiction
    "BUNDESRAT_INVOLVEMENT",   # Vorgang → LegislativeBody
    "BECOMES_BUNDESGESETZ",    # Vorgang → Policy
    "AUTHORS_DRUCKSACHE",      # Person → Drucksache
    "AMENDS_DRUCKSACHE",       # Drucksache → Drucksache
    "REFERENCES_VORGANG",      # Drucksache/Plenarprotokoll → Vorgang
    "ACTIVITY_IN_VORGANG",     # Aktivität → Vorgang
]
```

### Edge Type Map (Valid Combinations)
**Defines which edges can connect which entity pairs:**

```python
from src.graphrag.political_schema_v4 import (
    EDGE_TYPE_MAP_V4,
    get_valid_edges_for_entity_pair_v4,
    validate_edge_pattern_v4,
)

# Example: What edges can connect BundestagPerson to Vorgang?
valid_edges = get_valid_edges_for_entity_pair_v4("BundestagPerson", "Vorgang")
# Returns: ["INITIATES_VORGANG"]

# Validate a specific pattern
is_valid = validate_edge_pattern_v4("Drucksache", "IN_WAHLPERIODE", "Wahlperiode")
# Returns: True
```

### Episode Naming Strategy
```python
def generate_episode_name(doc_path: str, timestamp: datetime) -> str:
    """Generate consistent episode names for documents."""
    return f"political_doc_{doc_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
```

## Integration with Existing System

### Document Processing Pipeline (Production Implementation)
**From `src/flows/data_ingestion/document_processor.py`:**

```python
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from src.graphrag.political_schema_v4 import (
    ENTITY_TYPE_REGISTRY_V4,
    EDGE_TYPE_REGISTRY_V4,
    EDGE_TYPE_MAP_V4,
)
from src.flows.data_ingestion.document_chunker import HybridDocumentChunker

async def process_political_document(doc_path: Path, graphiti_client: Graphiti):
    """Production document processing with chunking and custom schema."""

    # 1. Read and preprocess document
    content = read_document(doc_path)
    from src.flows.data_ingestion.document_preprocessor import preprocess_document
    content = preprocess_document(content, enable_link_removal=True)

    # 2. Chunk document (ALWAYS chunk for consistency)
    chunker = HybridDocumentChunker(max_tokens=120000, overlap_ratio=0.10)
    chunks = chunker.create_chunks(content)

    # 3. Process each chunk through Graphiti with custom schema
    results = []
    previous_episode_uuid = None

    for chunk in chunks:
        episode_name = f"political_doc_{doc_path.stem}_{datetime.now():%Y%m%d_%H%M%S}_chunk_{chunk['chunk_index']}"

        result = await graphiti_client.add_episode(
            name=episode_name,
            episode_body=chunk['text'],
            source=EpisodeType.text,
            source_description=f"Political document chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']}: {doc_path.name}",
            reference_time=extract_document_date(chunk['text']) or datetime.now(),
            group_id=GROUP_ID,  # "political_monitoring_v2"

            # ✅ Custom schema for political domain
            entity_types=ENTITY_TYPE_REGISTRY_V4,
            edge_types=EDGE_TYPE_REGISTRY_V4,
            edge_type_map=EDGE_TYPE_MAP_V4,

            # Chain linking for multi-chunk documents
            previous_episode_uuids=[previous_episode_uuid] if previous_episode_uuid else None,
        )

        # Track for chain linking
        previous_episode_uuid = result.episode.uuid if hasattr(result, "episode") else None

        results.append({
            "chunk_index": chunk["chunk_index"],
            "episode_uuid": previous_episode_uuid,
            "entities": len(result.nodes) if hasattr(result, "nodes") else 0,
            "relationships": len(result.edges) if hasattr(result, "edges") else 0,
        })

    return {
        "status": "success",
        "path": str(doc_path),
        "total_chunks": len(chunks),
        "episode_uuids": [r["episode_uuid"] for r in results],
        "total_entities": sum(r["entities"] for r in results),
        "total_relationships": sum(r["relationships"] for r in results),
    }
```

**Key Features:**
1. **Hybrid Chunking**: Always chunks documents (120K tokens, 10% overlap)
2. **Custom Schema**: Uses political_schema_v4.py entities/edges
3. **Chain Linking**: Links chunks via `previous_episode_uuids`
4. **Preprocessing**: Removes links, deduplicates content
5. **Group ID**: Organizes episodes under "political_monitoring_v2"

### Hybrid Architecture Pattern
```python
class PoliticalKnowledgeBuilder:
    """Hybrid Graphiti + MCP architecture for political analysis."""
    
    def __init__(self):
        # Direct API for document processing
        self.graphiti_client = Graphiti(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
        
        # MCP available for Claude Code interactions
        self.mcp_available = True  # MCP servers running in Docker
    
    async def process_documents(self, document_paths: List[str]):
        """Process documents using direct API."""
        results = []
        for doc_path in document_paths:
            result = await process_political_document(doc_path, self.graphiti_client)
            results.append(result)
        return results
    
    async def search_entities(self, query: str):
        """Search using direct API for full capabilities."""
        return await self.graphiti_client.search(query)
```

## Testing and Validation

### Test Pattern for Entity Extraction
```python
async def test_political_entity_extraction():
    """Test that political entities are extracted correctly."""
    
    test_content = """
    The EU Digital Services Act requires large platforms like Meta and Google 
    to implement content moderation systems. Commissioner Thierry Breton will 
    enforce these requirements starting February 2024.
    """
    
    result = await client.add_episode(
        name="DSA Test",
        episode_body=test_content,
        source="text",
        source_description="Test political content",
        reference_time=datetime.now()
    )
    
    # Verify expected entities were extracted
    entity_names = [node.name for node in result.nodes]
    assert "European Union" in entity_names or "EU" in entity_names
    assert "Meta" in entity_names
    assert "Google" in entity_names
    assert "Thierry Breton" in entity_names
```

## Performance Considerations

### Batch Processing
```python
async def batch_process_documents(documents: List[str], batch_size: int = 5):
    """Process documents in batches to avoid overwhelming the system."""
    results = []
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        batch_results = await asyncio.gather(*[
            process_political_document(doc, client) 
            for doc in batch
        ])
        results.extend(batch_results)
        # Small delay between batches
        await asyncio.sleep(1)
    return results
```

### Memory Management
```python
async def cleanup_graphiti_client():
    """Proper cleanup of Graphiti resources."""
    if hasattr(client, 'close'):
        await client.close()
```

## Advanced Features (Future Implementation)

### Community Detection
```python
# Method signature to be verified
async def build_policy_communities():
    """Build communities of related policies and organizations."""
    try:
        communities = await client.build_communities()
        return communities
    except Exception as e:
        logger.warning(f"Community detection failed: {e}")
        return None
```

### Temporal Queries
```python
async def get_policy_timeline(policy_name: str):
    """Get temporal evolution of a policy."""
    results = await client.search(f"{policy_name} timeline")
    # Process results to build timeline
    return build_timeline_from_results(results)
```

## Error Handling Patterns

### Robust Episode Creation
```python
async def safe_add_episode(client: Graphiti, **kwargs):
    """Add episode with error handling and retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await client.add_episode(**kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to add episode after {max_retries} attempts: {e}")
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Configuration Management

### Environment Setup
```python
class GraphitiConfig:
    """Centralized configuration for Graphiti connections."""
    
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    @classmethod
    async def create_client(cls) -> Graphiti:
        """Create and initialize Graphiti client."""
        client = Graphiti(cls.NEO4J_URI, cls.NEO4J_USER, cls.NEO4J_PASSWORD)
        await client.build_indices_and_constraints()
        return client
```

## Migration from Neo4j GraphRAG

### Replacement Strategy
```python
# OLD: Neo4j GraphRAG SimpleKGPipeline
# kg_pipeline = SimpleKGPipeline(llm=llm, driver=driver, embedder=embedder)
# result = kg_pipeline.run(file_path=document_path)

# NEW: Graphiti Direct API
client = await GraphitiConfig.create_client()
result = await client.add_episode(
    name=f"doc_{document_path.stem}",
    episode_body=read_document(document_path),
    source="text",
    source_description=f"Political document: {document_path}",
    reference_time=datetime.now()
)
```

## Success Metrics

### Quality Indicators
- **Entity Extraction Accuracy**: >90% for political entities (Policy, Organization, Politician)
- **Relationship Detection**: >85% for key relationships (AFFECTS, REQUIRES_COMPLIANCE)
- **Processing Speed**: <30 seconds per document
- **Memory Usage**: <2GB for 100 documents

### Validation Approach
1. **Test Documents**: Use enhanced test documents from `/data/input/examples/`
2. **Manual Review**: Validate entity extraction on sample documents
3. **Performance Monitoring**: Track processing times and memory usage
4. **Error Rates**: Monitor failed episode creation attempts

## Production Status & Implementation

### ✅ Completed (In Production)

1. **✅ Custom Entity Types**: Full political_schema_v4.py with 28 entities, 52 edges
2. **✅ Document Pipeline**: Production implementation in `src/flows/data_ingestion/`
   - Hybrid chunking (120K tokens, 10% overlap)
   - Chain linking for multi-chunk documents
   - Ray-based parallel processing
   - Document tracking and deduplication
3. **✅ Schema Integration**: Custom registries passed to `add_episode()`
4. **✅ APISIX LLM Routing**: Cost tracking via APISIX gateway
5. **✅ Preprocessing Pipeline**: Link removal, deduplication, encoding detection

### ✅ Episode Semantic Search (v0.2.1 - NEW)

6. **Episode Content Embeddings**: Semantic search over source documents
   - Vector embeddings on `Episodic.content_embedding` (1536-dim, cosine)
   - Hybrid BM25 + vector search for improved retrieval
   - `EpisodeEmbeddingManager` class for embedding operations
   - Backfill script for existing episodes
   - Integrated with MCP Graph Retrieval server

### 🚧 Planned Future Enhancements

1. **Community Detection**: Implement policy clustering via Graphiti
2. **Graph Type Differentiation**: Separate lexical (internet research) from domain (Bundestag DIP) graphs
3. **Schema Evolution**: Add DrucksachePage entities for page-level navigation

### 📊 Performance Metrics (Current)

- **Processing Speed**: 20-40 documents/minute with Ray actors
- **Chunk Size**: 120K tokens per episode (safe margin under 128K limit)
- **Overlap**: 10% for context preservation
- **Schema Coverage**: 28 entity types, 52 relationship types
- **Boundary Types**: Header → Paragraph → Fixed-size (hybrid strategy)

## Episode Semantic Search (v0.2.1)

### Overview
Episodic nodes contain chunked source documents. To enable semantic retrieval of source content alongside entities, we add vector embeddings to episode content.

### Database Schema Extensions
```sql
-- Vector index for semantic search on episode content
CREATE VECTOR INDEX episodic_content_embedding_index IF NOT EXISTS
FOR (ep:Episodic) ON (ep.content_embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}

-- Fulltext index for BM25 search on episode content
CREATE FULLTEXT INDEX episodic_content_fulltext IF NOT EXISTS
FOR (ep:Episodic) ON EACH [ep.content, ep.name]
```

### Episode Embedding Manager
**File**: `src/graphrag/episode_embedding_manager.py`

```python
from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager

# Initialize manager (uses APISIX for cost tracking)
manager = EpisodeEmbeddingManager(
    neo4j_uri=NEO4J_URI,
    neo4j_user=NEO4J_USER,
    neo4j_password=NEO4J_PASSWORD,
    neo4j_database=NEO4J_DATABASE,
)

# Add embedding to existing episode
success = await manager.add_content_embedding(episode_uuid, content_text)

# Check embedding coverage statistics
stats = await manager.get_embedding_stats()
# Returns: {
#   total_episodes: 7611,
#   episodes_with_embeddings: 7500,
#   episodes_without_embeddings: 111,
#   coverage_percentage: 98.54
# }

# Find episodes needing embeddings (for backfill)
episodes = await manager.get_episodes_without_embeddings(limit=100)
# Returns: [{uuid, content, name}, ...]

# Generate query embedding for search
query_embedding = await manager.generate_query_embedding("GDPR enforcement")

# Cleanup
await manager.close()
```

### Integration with Document Processor
Episodes automatically receive embeddings during ingestion:

```python
# In src/flows/data_ingestion/document_processor.py
from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager

class DocumentProcessorActor:
    def __init__(self):
        # ... existing initialization ...
        self.embedding_manager = EpisodeEmbeddingManager()

    async def process_chunk(self, chunk_text: str, ...):
        # Add episode via Graphiti
        result = await self.graphiti_client.add_episode(...)

        # Generate and store content embedding
        if result.episode and result.episode.uuid:
            await self.embedding_manager.add_content_embedding(
                result.episode.uuid,
                chunk_text
            )
```

### Backfill Operations
**File**: `scripts/backfill_episode_embeddings.py`

```bash
# Check embedding coverage
just check-episode-embeddings

# Dry run (estimate cost without generating embeddings)
just backfill-episodes-dry

# Full backfill with default batch size (50)
just backfill-episodes

# Custom batch size for faster processing
just backfill-episodes 100

# Test with limited episodes
just backfill-episodes-test 50
```

**Cost Estimation**:
- Model: `text-embedding-3-small` at $0.02/1M tokens
- ~7,611 episodes × ~5K chars avg = ~38M chars
- ~38M chars / 4 chars per token = ~9.5M tokens
- **Initial backfill cost**: ~$0.19
- **Ongoing cost**: ~$0.50/month (~173 new episodes/day)

### Hybrid Search Pattern
The MCP Graph Retrieval server combines BM25 + vector search:

```python
# In src/mcp/graph_retrieval/retriever.py
async def _search_episodes(self, params: dict) -> dict:
    """Hybrid BM25 + vector search on episodic nodes."""
    query_text = params["query"]
    limit = params.get("limit", 5)

    # Generate query embedding
    embedder = await self._get_embedder()
    query_embedding = await embedder.create(input_data=[query_text])

    # Execute hybrid search with score fusion
    # BM25 weight: 0.3, Vector weight: 0.7
    query = """
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
    RETURN node.uuid, node.name, node.content, node.source_description,
           node.valid_at, combined_score AS score
    """
```

### Claude Agent Integration
The `search_documents` tool is available in the Claude agent:

```python
# In src/claude_agent/agent.py - TOOLS list
{
    "name": "search_documents",
    "description": "Search source documents (episodic nodes) using semantic similarity...",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }
}

# In SYSTEM_PROMPT - Available Tools
# 2. search_documents - Use this to search source documents using semantic similarity

# Best Practice
# - For finding specific passages or quotes from source documents, use search_documents
```

---

**Status**: ✅ Production-ready with custom schema and semantic search
**Last Updated**: 2025-01-14
**Version**: 2.1
**Implementation**: `src/flows/data_ingestion/document_processor.py`, `src/graphrag/episode_embedding_manager.py`