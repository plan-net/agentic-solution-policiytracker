# Neo4j GraphRAG Implementation Patterns

## Overview
This document captures our learnings and patterns for implementing Neo4j GraphRAG in the Political Monitoring Agent v0.2.0.

## Key Resources
- **GitHub Repository**: https://github.com/neo4j/neo4j-graphrag-python
- **Blog Post**: https://neo4j.com/blog/news/graphrag-python-package/
- **Official Documentation**: https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_kg_builder.html

## SimpleKGPipeline Architecture

### Core Components
1. **LLM**: For entity and relationship extraction
2. **Embedder**: For vector similarity search
3. **Neo4j Driver**: Database connection
4. **Schema Definition**: Guides extraction process

### Initialization Pattern
```python
from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.llm import OpenAILLM

# Initialize components
driver = GraphDatabase.driver(NEO4J_URI, auth=(username, password))
llm = OpenAILLM(model_name="gpt-4o-mini", api_key=api_key)
embedder = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)

# Create pipeline
kg_pipeline = SimpleKGPipeline(
    llm=llm,               # Required first parameter
    driver=driver,         # Required second parameter  
    embedder=embedder,     # Required third parameter
    from_pdf=False,        # Set to False for text files
    neo4j_database="neo4j" # Optional database name
)
```

## Schema Configuration

### Entity Definition Formats
```python
# Simple string format
ENTITIES = ["Person", "Organization", "Policy"]

# Dictionary format with description
ENTITIES = [
    {"label": "Person", "description": "Individual people mentioned"},
    {"label": "Organization", "description": "Companies, agencies, NGOs"}
]

# Dictionary format with properties
ENTITIES = [
    {
        "label": "Policy", 
        "properties": [
            {"name": "title", "type": "STRING"},
            {"name": "status", "type": "STRING"}
        ]
    }
]
```

### Relationship Definition Formats
```python
# Simple string format
RELATIONS = ["WORKS_FOR", "PROPOSED", "SUPPORTS"]

# Dictionary format with description
RELATIONS = [
    {"label": "PROPOSED", "description": "Policy proposed by person"},
    {"label": "AFFECTS", "description": "Policy affects organization"}
]
```

### Potential Schema (Relationship Constraints)
```python
POTENTIAL_SCHEMA = [
    ("Person", "WORKS_FOR", "Organization"),
    ("Person", "PROPOSED", "Policy"),
    ("Policy", "AFFECTS", "Organization")
]
```

## Political Domain Schema

### Recommended Entity Types
```python
POLITICAL_ENTITIES = [
    "Policy",        # Laws, regulations, directives
    "Politician",    # Individual political figures
    "Organization",  # Government agencies, NGOs, companies
    "Regulation",    # Specific regulatory frameworks
    "Event",         # Political events, elections, hearings
    "Topic",         # Policy areas (privacy, AI, cybersecurity)
    "Jurisdiction",  # Geographic/legal jurisdictions
    "Amendment",     # Policy changes and updates
    "Compliance"     # Compliance requirements and obligations
]
```

### Recommended Relationship Types
```python
POLITICAL_RELATIONS = [
    "AUTHORED_BY",        # Who created/proposed
    "AFFECTS",           # Impact relationships
    "SUPPORTS",          # Political support
    "OPPOSES",           # Political opposition
    "RELATES_TO",        # Topical connections
    "REFERENCES",        # Document citations
    "IMPLEMENTS",        # Implementation relationships
    "SUPERSEDES",        # Replacement relationships
    "AMENDS",            # Modification relationships
    "REQUIRES_COMPLIANCE", # Compliance obligations
    "GOVERNS",           # Regulatory authority
    "APPLIES_TO"         # Jurisdictional application
]
```

## Pipeline Execution Patterns

### Async Execution (Recommended)
```python
async def process_documents(file_paths):
    for file_path in file_paths:
        try:
            result = await kg_pipeline.run_async(file_path=str(file_path))
            print(f"Processed: {file_path}")
        except Exception as e:
            print(f"Failed to process {file_path}: {e}")
```

### Thread Pool Execution (For Mixed Async/Sync)
```python
import asyncio

def _run_pipeline_sync(file_path):
    return asyncio.run(kg_pipeline.run_async(file_path=file_path))

async def process_documents(file_paths):
    loop = asyncio.get_event_loop()
    for file_path in file_paths:
        result = await loop.run_in_executor(None, _run_pipeline_sync, file_path)
```

## Error Handling Patterns

### Error Handling Configuration
```python
from neo4j_graphrag.experimental.components.entity_relation_extractor import OnError

kg_pipeline = SimpleKGPipeline(
    llm=llm,
    driver=driver,
    embedder=embedder,
    on_error=OnError.IGNORE  # Options: IGNORE, RAISE
)
```

### Robust Processing Pattern
```python
async def robust_document_processing(file_paths):
    results = []
    for file_path in file_paths:
        try:
            result = await kg_pipeline.run_async(file_path=file_path)
            results.append({
                "file_path": file_path,
                "status": "success",
                "result": result
            })
        except Exception as e:
            results.append({
                "file_path": file_path,
                "status": "error",
                "error": str(e)
            })
    return results
```

## Integration with Existing Systems

### Async Context Manager Pattern
```python
class PoliticalKnowledgeBuilder:
    def __init__(self, ...):
        self.driver = GraphDatabase.driver(...)
        self.kg_pipeline = SimpleKGPipeline(...)
    
    async def __aenter__(self):
        # Initialize vector indexes, etc.
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()
```

### Thread Pool Integration
```python
async def process_documents(self, document_paths):
    def _run_pipeline():
        results = []
        for doc_path in document_paths:
            result = asyncio.run(self.kg_pipeline.run_async(file_path=doc_path))
            results.append(result)
        return results
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_pipeline)
```

## Configuration Best Practices

### Environment-Based Configuration
```python
import os

class GraphRAGConfig:
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
```

### Schema Validation
```python
def validate_schema(entities, relations, potential_schema):
    """Validate schema configuration before pipeline creation."""
    # Check entity format
    for entity in entities:
        if isinstance(entity, dict) and "label" not in entity:
            raise ValueError(f"Entity missing 'label': {entity}")
    
    # Check potential schema references valid entities/relations
    entity_labels = [e["label"] if isinstance(e, dict) else e for e in entities]
    relation_labels = [r["label"] if isinstance(r, dict) else r for r in relations]
    
    for source, relation, target in potential_schema:
        if source not in entity_labels:
            raise ValueError(f"Unknown entity in schema: {source}")
        if target not in entity_labels:
            raise ValueError(f"Unknown entity in schema: {target}")
        if relation not in relation_labels:
            raise ValueError(f"Unknown relation in schema: {relation}")
```

## Performance Considerations

### Chunking Strategy
- Default chunk size is appropriate for most documents
- Political documents may benefit from larger chunks (1000-2000 tokens)
- Overlap helps maintain context across chunks

### Batch Processing
- Process documents sequentially to avoid API rate limits
- Monitor memory usage with large document sets
- Consider parallel processing for independent documents

### Vector Index Optimization
```python
# Create optimized vector index
CREATE VECTOR INDEX chunk_embeddings IF NOT EXISTS
FOR (c:Chunk) ON (c.embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}
```

## Limitations and Considerations

### Current Limitations
1. **Experimental Status**: API may change between versions
2. **LLM Dependency**: Extraction quality depends on LLM performance
3. **Cost Considerations**: OpenAI API costs for large document sets
4. **Schema Rigidity**: Schema enforcement can miss nuanced relationships

### Recommended Mitigations
1. **Version Pinning**: Pin specific package versions in production
2. **Fallback Strategies**: Implement traditional extraction as backup
3. **Cost Monitoring**: Track API usage and implement budgets
4. **Hybrid Approach**: Combine GraphRAG with domain-specific rules

## Testing Strategies

### Unit Testing Pattern
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_kg_pipeline():
    pipeline = MagicMock()
    pipeline.run_async = AsyncMock(return_value={"status": "success"})
    return pipeline

async def test_document_processing(mock_kg_pipeline):
    builder = PoliticalKnowledgeBuilder(...)
    builder.kg_pipeline = mock_kg_pipeline
    
    results = await builder.process_documents(["test.txt"])
    assert results["successful"] == 1
```

### Integration Testing
```python
async def test_end_to_end_processing():
    """Test with real Neo4j and mock LLM."""
    builder = PoliticalKnowledgeBuilder(
        openai_api_key="test",  # Mock key
        # ... other config
    )
    
    # Test with small document
    test_doc = "test_document.txt"
    results = await builder.process_documents([test_doc])
    
    # Verify graph state
    stats = await builder.get_graph_stats()
    assert stats["documents"] > 0
```

## Future Enhancements

### Planned Improvements
1. **Custom Entity Resolution**: Domain-specific entity merging
2. **Temporal Relationships**: Track changes over time
3. **Multi-Document Linking**: Cross-document relationship detection
4. **Quality Metrics**: Extraction confidence scoring

### Integration Roadmap
1. **Phase 1**: Basic pipeline with simple schema
2. **Phase 2**: Political domain schema refinement
3. **Phase 3**: Custom retrievers and search optimization
4. **Phase 4**: Advanced entity resolution and temporal tracking