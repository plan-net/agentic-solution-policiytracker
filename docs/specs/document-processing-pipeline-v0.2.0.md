# Document Processing Pipeline v0.2.0 - Complete Plan

## Overview
Complete plan for implementing the document processing pipeline using Graphiti temporal knowledge graphs via MCP with fallback to direct API for advanced features.

## Key Insights from Graphiti Documentation

### Core Capabilities
- **Custom Entity Types**: Pydantic models for schema-driven extraction
- **Communities**: Automatic clustering of related entities using Leiden algorithm
- **Fact Triples**: Direct relationship creation between entities
- **Graph Namespacing**: Isolated knowledge graphs via `group_id`
- **Advanced Search**: Hybrid, node-distance, community-based retrieval
- **CRUD Operations**: Full management of nodes, edges, and episodes

### MCP Server Limitations
**Supported via MCP:**
- ✅ Episode creation (`add_episode`) with group_id namespacing
- ✅ Basic search (`search_nodes`, `search_facts`)
- ✅ Episode management (`get_episodes`, `delete_episode`)
- ✅ Basic edge operations (`get_entity_edge`, `delete_entity_edge`)

**Requires Direct API:**
- ❌ Custom entity type registration in episodes
- ❌ Community detection (`build_communities`)
- ❌ Direct fact triple creation (`add_triplet`)
- ❌ Advanced search strategies
- ❌ Full CRUD operations

## Architecture Design

### Hybrid Approach
```
Document → LLM Entity Extraction → Structured Episode → Graphiti (MCP + Direct API) → Knowledge Graph
                                                              ↓
                                                    Community Detection → Advanced Search
```

### Core Components

1. **Schema Layer** (Pydantic Models)
2. **LLM Extraction Engine** (Political Entity Recognition)
3. **Episode Constructor** (Structured Data + Metadata)
4. **Graphiti Integration** (MCP Primary + Direct API Fallback)
5. **Analysis Layer** (Communities + Advanced Search)

## Implementation Todo List

### Phase 1: Foundation (High Priority)
- [ ] **dp_1**: Convert political_schema_v2.py to Graphiti-compatible Pydantic models
- [ ] **dp_2**: Design LLM entity extraction prompt templates for political documents  
- [ ] **dp_3**: Create core document processor with LLM entity extraction
- [ ] **dp_4**: Implement episode structuring logic (text + extracted entities)
- [ ] **dp_5**: Build Graphiti episode creation with custom entity types

### Phase 2: Integration (Medium Priority)
- [ ] **dp_6**: Test entity extraction accuracy with sample political documents
- [ ] **dp_7**: Implement batch document processing with progress tracking
- [ ] **dp_8**: Build community detection and analysis for policy clusters
- [ ] **dp_9**: Implement advanced search strategies for document queries
- [ ] **dp_10**: Create temporal-aware document processing (avoid reprocessing)

### Phase 3: Enhancement (Low Priority)
- [ ] **dp_11**: Design document metadata extraction and episode naming strategy
- [ ] **dp_12**: Build processing statistics and reporting system
- [ ] **dp_13**: Create validation system for entity extraction quality
- [ ] **dp_14**: Implement error handling and retry logic for LLM calls
- [ ] **dp_15**: Design reusable core for Client Context workflow

## Technical Implementation Strategy

### 1. Custom Schema (dp_1)
Convert our political schema to Graphiti Pydantic models:
```python
class Policy(BaseModel):
    name: str = Field(..., description="Policy or regulation name")
    status: str | None = Field(None, description="Status: proposed, enacted, repealed")
    jurisdiction: str | None = Field(None, description="Geographic jurisdiction")
    effective_date: str | None = Field(None, description="When policy becomes effective")

class Organization(BaseModel):
    name: str = Field(..., description="Organization name")
    type: str | None = Field(None, description="Type: company, government, NGO") 
    sector: str | None = Field(None, description="Industry sector")
    
class Politician(BaseModel):
    name: str = Field(..., description="Full name")
    role: str | None = Field(None, description="Current political role")
    party: str | None = Field(None, description="Political party")
```

### 2. LLM Entity Extraction (dp_2 + dp_3)
**Prompt Strategy:**
- Use political schema as extraction guidance
- Output structured JSON with entities and relationships
- Include confidence scores and context snippets

**Example Output:**
```json
{
  "entities": [
    {"type": "Policy", "name": "EU AI Act", "status": "enacted", "jurisdiction": "EU"},
    {"type": "Organization", "name": "Apple", "type": "company", "sector": "technology"}
  ],
  "relationships": [
    {"source": "Apple", "target": "EU AI Act", "type": "MUST_COMPLY_WITH", "confidence": 0.95}
  ]
}
```

### 3. Episode Creation (dp_4 + dp_5)
**Hybrid Approach:**
- **Try MCP first**: Basic episode creation
- **Fallback to Direct API**: If custom entity types needed

```python
# Episode structure
episode_data = {
    "name": f"policy_doc_{timestamp}",
    "episode_body": full_document_text,
    "source": "text",
    "group_id": "political_monitoring",
    "entity_types": custom_entity_types,  # May require direct API
    "reference_time": document_date
}
```

### 4. Community Detection (dp_8)
**Post-Processing Analysis:**
- Build communities after episode ingestion
- Identify policy clusters, organization networks
- Generate cluster summaries for insights

### 5. Reusability Design (dp_15)
**Core Processing Components:**
```python
class DocumentProcessor:
    async def extract_entities(text: str) -> EntityExtractionResult
    async def create_episode(entities: List, text: str) -> EpisodeResult
    async def build_communities() -> CommunityResult
```

**Shared by Both Workflows:**
- Data Ingestion: Process regulatory documents
- Client Context: Process client research and web data

## Graph Namespacing Strategy

### Namespace Design
- **`political_docs`**: Regulatory documents and policy analysis
- **`client_{client_id}`**: Client-specific context and research
- **`relevance_assessment`**: Assessment results and insights

### Benefits
- Data isolation between clients
- Simplified queries and management
- Multi-tenant architecture support

## Success Metrics

### Quality Indicators
- **Entity Extraction Accuracy**: >90% precision for political entities
- **Relationship Detection**: >85% accuracy for key relationships
- **Community Coherence**: Meaningful policy/organization clusters
- **Temporal Tracking**: Accurate timeline construction

### Performance Targets
- **Processing Speed**: <30 seconds per document
- **Memory Usage**: <2GB for 100 documents
- **Graph Growth**: Controlled entity deduplication

## Risk Mitigation

### Technical Risks
- **MCP Limitations**: Fallback to direct API implemented
- **LLM Accuracy**: Validation and retry logic included
- **Graph Complexity**: Community detection for organization

### Operational Risks
- **Data Quality**: Comprehensive entity validation
- **Processing Failures**: Robust error handling and recovery
- **Schema Evolution**: Pydantic model versioning

## Next Steps

1. **Start with dp_1**: Convert political schema to Pydantic models
2. **Validate MCP**: Test custom entity type support
3. **Build Core**: Implement LLM extraction + episode creation
4. **Test & Iterate**: Use enhanced test documents for validation
5. **Scale**: Implement batch processing and optimization

## Integration Points

### With Existing System
- **Replace**: Current neo4j GraphRAG approach entirely
- **Maintain**: Kodosumi app structure and Ray integration
- **Extend**: Add new temporal and community capabilities

### With Future Workflows
- **Client Context**: Reuse entity extraction and episode creation
- **Relevance Assessment**: Leverage temporal queries and communities
- **Reporting**: Build on community insights and relationship analysis

---

*This plan represents Phase 1 of the three-workflow architecture as specified in feature-split-graph-processing.md*