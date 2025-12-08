# Weekly Report Flow Tool Strategy v1.0

## Overview

The Weekly Regulatory Intelligence Digest flow uses specialized search strategies for each category research agent. This document details the tool architecture, search recipe mapping, and implementation strategy.

**File Location**: `src/flows/weekly_report/agents/category_researchers.py`

---

## Tool Architecture

### Search Tool Integration

The Weekly Report flow reuses the `GraphitiSearchTool` from `src/chat/tools/search.py` to leverage:
- 7 pre-configured search recipes
- Relevance scoring (0.0-1.0)
- Source extraction from Episodic nodes
- Structured JSON output with graph data

### Category Agent Structure

```
BaseCategoryResearchAgent (abstract)
├── search_type (abstract property) → returns search recipe name
├── _execute_search() → uses GraphitiSearchTool with category-specific recipe
├── _process_results() → LLM extraction with relevance + source metadata
└── 5 concrete implementations:
    ├── LegislativeResearchAgent  → "comprehensive"
    ├── PersonnelResearchAgent    → "entity_focused"
    ├── ComplianceResearchAgent   → "relationship_focused"
    ├── PolicyResearchAgent       → "rrf_balanced"
    └── EventsResearchAgent       → "episode_focused"
```

---

## Category-to-Recipe Mapping

| Category | Agent | Search Type | Graphiti Recipe | Rationale |
|----------|-------|-------------|-----------------|-----------|
| **Legislative** | `LegislativeResearchAgent` | `comprehensive` | `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` | Laws and regulations need comprehensive search with cross-encoder reranking for accuracy |
| **Personnel** | `PersonnelResearchAgent` | `entity_focused` | `NODE_HYBRID_SEARCH_RRF` | People and positions are entity-centric; node search finds people, ministries, committees |
| **Compliance** | `ComplianceResearchAgent` | `relationship_focused` | `EDGE_HYBRID_SEARCH_NODE_DISTANCE` | Enforcement actions are relationships: company→fine→regulator; edge search with node distance |
| **Policy** | `PolicyResearchAgent` | `rrf_balanced` | `COMBINED_HYBRID_SEARCH_RRF` | Policy needs balanced entity+relationship results; RRF fusion balances both |
| **Events** | `EventsResearchAgent` | `episode_focused` | `EDGE_HYBRID_SEARCH_EPISODE_MENTIONS` | Time-sensitive document-based events; episode mentions preserve temporal context |

---

## Search Recipe Details

### Recipe 1: `comprehensive` (Legislative)
**Graphiti Config**: `COMBINED_HYBRID_SEARCH_CROSS_ENCODER`

**How It Works**:
- Combines node (entity) and edge (relationship) search
- Uses cross-encoder neural reranking for high precision
- Best for complex queries requiring accuracy over speed

**Use Case**: Legislative research needs to find specific laws, directives, and regulations with high accuracy. Cross-encoder reranking ensures the most relevant legal documents surface first.

**Example Queries**:
- "new regulation law enacted passed proposed legislation"
- "DSA DMA Digital Services Act Digital Markets Act compliance"
- "AI Act artificial intelligence governance regulation"

---

### Recipe 2: `entity_focused` (Personnel)
**Graphiti Config**: `NODE_HYBRID_SEARCH_RRF`

**How It Works**:
- Focuses on entity nodes (people, organizations, positions)
- Uses Reciprocal Rank Fusion (RRF) for result combination
- Prioritizes entity summaries over relationship facts

**Use Case**: Personnel changes are entity-centric—appointments, resignations, committee memberships. Node search finds the people and positions directly.

**Example Queries**:
- "appointed minister ministry new position"
- "committee chair member leadership change"
- "EU Commissioner appointment"

---

### Recipe 3: `relationship_focused` (Compliance)
**Graphiti Config**: `EDGE_HYBRID_SEARCH_NODE_DISTANCE`

**How It Works**:
- Focuses on relationship edges (facts connecting entities)
- Uses node distance scoring for relevance
- Best for finding connections and actions between entities

**Use Case**: Compliance and enforcement actions are inherently relational—a company receives a fine from a regulator for violating a law. Edge search captures these connections.

**Example Queries**:
- "fine penalty enforcement action platform"
- "GDPR violation fine million euro"
- "competition antitrust investigation ruling"

---

### Recipe 4: `rrf_balanced` (Policy)
**Graphiti Config**: `COMBINED_HYBRID_SEARCH_RRF`

**How It Works**:
- Balances node and edge results using RRF fusion
- No neural reranking (faster than cross-encoder)
- Good for broad queries needing both entities and relationships

**Use Case**: Policy research needs both entities (ministries, agencies) and relationships (policy initiatives, government programs). RRF provides balanced coverage.

**Example Queries**:
- "ministry policy initiative announcement"
- "digital strategy digitalization government"
- "e-government digital transformation"

---

### Recipe 5: `episode_focused` (Events)
**Graphiti Config**: `EDGE_HYBRID_SEARCH_EPISODE_MENTIONS`

**How It Works**:
- Prioritizes episode (document) mentions
- Preserves temporal context from source documents
- Best for time-sensitive, document-anchored content

**Use Case**: Upcoming events and deadlines are tied to specific documents and dates. Episode-focused search preserves the temporal context needed to identify deadlines.

**Example Queries**:
- "deadline compliance effective date implementation"
- "public consultation comment period"
- "regulation effective date coming into force"

---

## Implementation Details

### `_execute_search()` Method
**Location**: `category_researchers.py` (Lines 130-182)

```python
@langwatch_config.trace(name="graphiti_search")
async def _execute_search(
    self, query: str, week_start: datetime, week_end: datetime
) -> list[dict[str, Any]]:
    """Execute search using GraphitiSearchTool with category-specific recipe."""
    try:
        # Create search tool with the shared Graphiti client
        search_tool = GraphitiSearchTool(graphiti_client=self.client)

        # Build temporal query
        temporal_query = f"{query} {week_start.year}"

        # Use structured output to get relevance scores and sources
        result = await search_tool._arun(
            query=temporal_query,
            limit=20,
            search_type=self.search_type,  # Category-specific recipe
            output_format="structured",
        )

        # Process structured results
        if isinstance(result, dict) and "results" in result:
            return [
                {
                    "type": r.get("type", "fact"),
                    "content": r.get("content", ""),
                    "relevance_score": r.get("relevance_score"),
                    "source": r.get("source"),
                    "name": r.get("name", "Unknown"),
                }
                for r in result["results"]
            ]

        return []

    except Exception as e:
        logger.error(f"Graphiti search failed: {e}")
        return []
```

### Result Format

Each search result includes:
- `type`: "relationship" or "entity"
- `content`: The fact or entity summary
- `relevance_score`: 0.0-1.0 score based on query term matching
- `source`: Dict with `title`, `url`, `date` from Episodic nodes
- `name`: Entity or relationship name

### LLM Processing with Metadata

The `_process_results()` method (Lines 169-259) formats results for LLM extraction:

```
- [relationship] [Relevance: 0.43] The European Commission fined Meta €1.2B... [Source: reuters.com: Meta faces record EU fine...]
- [entity] [Relevance: 0.29] Digital Services Act enforcement authority... [Source: ec.europa.eu: DSA implementation update]
```

The LLM extracts structured findings including:
- Title, Content, Date, Priority, Forward-looking flag
- **NEW**: Source attribution from search results

---

## Benefits of This Approach

### 1. Single Source of Truth
All search logic centralized in `src/chat/tools/search.py`. Improvements to `GraphitiSearchTool` automatically benefit both chat agent and weekly report.

### 2. Relevance Scoring
Results include `relevance_score` (0.0-1.0) calculated from query term matching. LLM can prioritize higher-relevance results.

### 3. Source Attribution
Automatic extraction of URLs, titles, and dates from Episodic nodes. Findings include source citations for verification.

### 4. Optimal Recipes
Each category uses the best-fit search strategy:
- Legislative: High-precision cross-encoder
- Personnel: Entity-focused node search
- Compliance: Relationship-focused edge search
- Policy: Balanced RRF fusion
- Events: Document-anchored episode search

### 5. Consistency
Same search behavior and quality in chat agent and weekly report. Users get consistent results regardless of interface.

### 6. Observability
All search operations traced via LangWatch:
- `@langwatch_config.trace(name="graphiti_search")`
- Enables monitoring of search performance by category

---

## Performance Characteristics

| Category | Recipe | Avg Latency | Precision | Coverage |
|----------|--------|-------------|-----------|----------|
| Legislative | Cross-Encoder | ~500ms | Highest | Medium |
| Personnel | Node RRF | ~200ms | High | High |
| Compliance | Edge Distance | ~300ms | High | High |
| Policy | Combined RRF | ~250ms | Medium | Highest |
| Events | Episode Mentions | ~200ms | Medium | High |

**Notes**:
- Cross-encoder is slower but more accurate (use for high-stakes legal content)
- RRF variants are faster, good for broader coverage
- Episode mentions preserve temporal context critical for events

---

## Query Templates by Category

### Legislative Research Queries
```python
[
    "new regulation law enacted passed proposed legislation",
    "DSA DMA Digital Services Act Digital Markets Act compliance",
    "GDPR data protection regulation enforcement deadline",
    "AI Act artificial intelligence governance regulation",
    "NIS2 cybersecurity directive implementation",
    "regulatory guidance compliance requirement",
    "platform regulation gatekeeper designation",
]
```

### Personnel Research Queries
```python
[
    "appointed minister ministry new position",
    "resigned departure leaving position",
    "committee chair member leadership change",
    "regulatory body director appointed",
    "EU Commissioner appointment",
    "parliamentary committee changes",
    "state secretary appointment ministry",
]
```

### Compliance Research Queries
```python
[
    "fine penalty enforcement action platform",
    "GDPR violation fine million euro",
    "DSA DMA compliance investigation",
    "competition antitrust investigation ruling",
    "platform gatekeeper compliance",
    "data breach notification penalty",
    "content moderation enforcement",
]
```

### Policy Research Queries
```python
[
    "ministry policy initiative announcement",
    "digital strategy digitalization government",
    "coalition agreement policy position",
    "e-government digital transformation",
    "federal ministry strategy program",
    "data economy policy framework",
    "infrastructure investment digital",
]
```

### Events Research Queries
```python
[
    "deadline compliance effective date implementation",
    "public consultation comment period",
    "parliamentary hearing vote scheduled",
    "conference summit event regulatory",
    "court hearing ruling expected date",
    "regulation effective date coming into force",
    "submission deadline registration required",
]
```

---

## Future Enhancements

### Phase 1: Temporal Filtering (Planned)
**Issue**: Current search uses year in query string (`{query} {week_start.year}`) instead of actual date filtering.

**Solution**: Use `search_by_date_range` tool once Issue #2 (temporal filtering) in `tool-strategy.md` is resolved.

```python
# Future implementation
result = await temporal_search_tool._arun(
    query=query,
    start_date=week_start,
    end_date=week_end,
    search_type=self.search_type,
)
```

### Phase 2: Category-Specific Recipes (Planned)
Consider creating new Graphiti recipes optimized for regulatory content:
- `REGULATORY_LEGISLATIVE_SEARCH` - Optimized for laws/directives
- `REGULATORY_ENFORCEMENT_SEARCH` - Optimized for fines/penalties
- `REGULATORY_TEMPORAL_SEARCH` - Optimized for deadlines/events

### Phase 3: Result Caching (Planned)
Add caching for repeated queries within the same report generation:
- Cache key: `(category, query_hash, week_start, week_end)`
- TTL: Duration of report generation (~5 minutes)
- Reduces API calls for similar queries

### Phase 4: Parallel Search (Planned)
Execute searches for all 5 categories in parallel:
```python
results = await asyncio.gather(
    legislative_agent.research(week_start, week_end),
    personnel_agent.research(week_start, week_end),
    compliance_agent.research(week_start, week_end),
    policy_agent.research(week_start, week_end),
    events_agent.research(week_start, week_end),
)
```

---

## Testing Strategy

### Unit Tests
- Test each `search_type` property returns correct value
- Test `_execute_search()` with mocked `GraphitiSearchTool`
- Test `_process_results()` with structured result format

### Integration Tests
- Test full `research()` method with real Graphiti client
- Verify correct recipe is used for each category
- Check relevance scores and source extraction

### Performance Tests
- Benchmark search latency by category/recipe
- Monitor LangWatch traces for bottlenecks
- Compare result quality across recipes

---

## Troubleshooting

### Issue: Low Relevance Scores
**Symptom**: Most results have `relevance_score < 0.2`
**Solution**:
- Check query terms are specific enough
- Consider using `comprehensive` search type
- Review query templates for category

### Issue: Missing Sources
**Symptom**: `source` is `None` for most results
**Solution**:
- Verify Episodic nodes have `source_description` property
- Check `_extract_source_from_episodes()` parsing logic
- Ensure documents were ingested with source metadata

### Issue: Wrong Recipe Used
**Symptom**: Category agent uses unexpected search behavior
**Solution**:
- Verify `search_type` property returns correct string
- Check `_get_search_config()` mapping in `search.py`
- Add logging to trace recipe selection

---

## References

- **GraphitiSearchTool**: `src/chat/tools/search.py` (Lines 38-637)
- **Category Researchers**: `src/flows/weekly_report/agents/category_researchers.py`
- **Chat Agent Tool Strategy**: `.claude/tool-strategy.md`
- **Tool Integration Patterns**: `.claude/tool-integration-patterns.md`
- **Graphiti Search Recipes**: `graphiti_core.search.search_config_recipes`

---

**Document Version**: 1.0
**Created**: 2025-12-04
**Last Updated**: 2025-12-04
**Status**: Implemented
