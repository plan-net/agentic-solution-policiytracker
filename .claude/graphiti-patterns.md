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

### 5. Custom Entity Types (To Investigate)
Based on documentation, custom entity types should be possible:
```python
# Example from docs (API needs verification)
from pydantic import BaseModel, Field

class Policy(BaseModel):
    name: str = Field(..., description="Policy name")
    status: str = Field(default="", description="Policy status")
    jurisdiction: str = Field(default="", description="Geographic jurisdiction")

# Usage pattern to be confirmed
entity_types = {"Policy": Policy}
# Method signature investigation needed
```

## Political Domain Patterns

### Entity Types for Political Analysis
```python
# Core political entities we want to extract
POLITICAL_ENTITIES = [
    "Policy",           # Laws, regulations, directives
    "Organization",     # Government agencies, companies, NGOs
    "Politician",       # Individual decision makers
    "Jurisdiction",     # Geographic/legal territories
    "ComplianceRequirement",  # Specific obligations
    "EnforcementAction",      # Fines, sanctions
    "PolicyArea",       # Regulatory domains (AI, privacy, etc.)
]
```

### Relationship Types
```python
POLITICAL_RELATIONSHIPS = [
    "AFFECTS",          # Policy affects Company
    "REQUIRES_COMPLIANCE", # Regulation requires Company compliance
    "ENFORCES",         # Agency enforces Regulation
    "OPERATES_IN",      # Company operates in Jurisdiction
    "INFLUENCES",       # Lobbyist influences Politician
    "SUPERSEDES",       # New policy replaces old policy
]
```

### Episode Naming Strategy
```python
def generate_episode_name(doc_path: str, timestamp: datetime) -> str:
    """Generate consistent episode names for documents."""
    return f"political_doc_{doc_path.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
```

## Integration with Existing System

### Document Processing Pipeline
```python
async def process_political_document(doc_path: str, client: Graphiti):
    """Process a political document through Graphiti."""
    
    # 1. Extract text content
    content = extract_document_text(doc_path)
    
    # 2. Add episode to Graphiti
    result = await client.add_episode(
        name=generate_episode_name(doc_path, datetime.now()),
        episode_body=content,
        source="text",
        source_description=f"Political document: {doc_path.name}",
        reference_time=extract_document_date(content) or datetime.now()
    )
    
    # 3. Return extracted entities for further processing
    return {
        "episode_id": result.episode.uuid,
        "entities": result.nodes,
        "entity_count": len(result.nodes)
    }
```

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

## Next Implementation Steps

1. **Custom Entity Types**: Investigate exact API for political domain entities
2. **Document Pipeline**: Build core document processing with Graphiti
3. **Community Detection**: Implement policy clustering
4. **Search Interface**: Create advanced search for political analysis
5. **Integration Testing**: Validate with real political documents

---

**Status**: Direct API approach validated and ready for implementation
**Last Updated**: 2025-05-27
**Version**: 1.0