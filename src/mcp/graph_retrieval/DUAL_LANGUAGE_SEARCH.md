# Dual Language Search Documentation

## Overview

The Dual Language Search feature enables automatic cross-lingual retrieval for German-English knowledge graphs. It allows users to query in either language and retrieve relevant results regardless of which language the content was originally indexed in.

## Architecture

### Components

The dual language search system consists of five key components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Query (EN or DE)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. Language Detection (_detect_language)                       │
│    - Stopword-based heuristics                                 │
│    - Returns 'en' or 'de'                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Query Translation (_translate_query)                        │
│    - Claude 3.5 Haiku translation                              │
│    - Preserves entities & technical terms                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Embedding Generation                                        │
│    - Original query → embedding_1                              │
│    - Translated query → embedding_2                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Parallel Search Execution (asyncio.gather)                  │
│    ┌─────────────────────┐     ┌─────────────────────┐        │
│    │ Search A (Original) │     │ Search B (Translated)│        │
│    │ - Keyword matching  │     │ - Keyword matching   │        │
│    │ - Vector similarity │     │ - Vector similarity  │        │
│    └─────────────────────┘     └─────────────────────┘        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Result Merging (_merge_multilingual_results)                │
│    - Deduplicate by UUID                                       │
│    - Keep highest scores                                       │
│    - Return combined nodes/edges/episodes                      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Methods

#### 1. `_detect_language(text: str) -> str`

**Purpose**: Detect if text is German or English using stopword heuristics.

**Algorithm**:
- Splits query into words
- Counts matches against German stopword set
- Counts matches against English stopword set
- Returns 'de' if German count > English count, else 'en'

**Example**:
```python
# German query
detected = self._detect_language("Was ist die DSGVO?")
# Returns: 'de'

# English query
detected = self._detect_language("What is the GDPR?")
# Returns: 'en'
```

#### 2. `_translate_query(query: str, source_lang: str) -> str`

**Purpose**: Translate query to opposite language using Claude Haiku.

**Features**:
- Uses Claude 3.5 Haiku for fast, cost-effective translation
- Preserves entity names (GDPR, DSGVO, DSA, AI Act, etc.)
- Maintains technical and political terminology
- Fallback to original query if translation fails

**Example**:
```python
# English → German
translated = await self._translate_query(
    "What is the GDPR regulation about?",
    source_lang="en"
)
# Returns: "Was ist die DSGVO-Verordnung?"

# German → English
translated = await self._translate_query(
    "Wie funktioniert der Digital Services Act?",
    source_lang="de"
)
# Returns: "How does the Digital Services Act work?"
```

**Cost**: ~$0.0001 per translation (Claude Haiku pricing)

#### 3. `_search_single_language(query_text, query_embedding, limit) -> dict`

**Purpose**: Execute search for a single language query.

**Process**:
1. Search entities with hybrid keyword + vector similarity
2. Search relationships with hybrid keyword + vector similarity
3. Search episodes (document chunks) with BM25 + vector
4. Return combined results

**Returns**:
```python
{
    "nodes": [
        {"uuid": "...", "name": "GDPR", "summary": "...", "score": 0.92},
        ...
    ],
    "edges": [
        {"uuid": "...", "fact": "...", "relationship_type": "REGULATES", "score": 0.85},
        ...
    ],
    "episodes": [
        {"uuid": "...", "content": "...", "score": 0.78},
        ...
    ]
}
```

#### 4. `_merge_multilingual_results(results1, results2) -> dict`

**Purpose**: Merge and deduplicate results from dual-language search.

**Algorithm**:
```python
for each item in results1 + results2:
    if uuid not in merged:
        merged[uuid] = item
    else:
        # Keep item with highest score
        if item.score > merged[uuid].score:
            merged[uuid] = item

# Sort by score descending
return sorted(merged.values(), key=lambda x: x.score, reverse=True)
```

**Example**:
```python
# Results from English search
results1 = {
    "nodes": [{"uuid": "123", "name": "GDPR", "score": 0.9}],
    "edges": [{"uuid": "456", "fact": "...", "score": 0.8}]
}

# Results from German search
results2 = {
    "nodes": [
        {"uuid": "123", "name": "DSGVO", "score": 0.95},  # Same entity
        {"uuid": "789", "name": "Bundestag", "score": 0.7}
    ],
    "edges": [{"uuid": "456", "fact": "...", "score": 0.85}]
}

merged = self._merge_multilingual_results(results1, results2)
# Result:
# nodes: [
#   {"uuid": "123", "name": "DSGVO", "score": 0.95},  # Higher score kept
#   {"uuid": "789", "name": "Bundestag", "score": 0.7}
# ]
# edges: [
#   {"uuid": "456", "fact": "...", "score": 0.85}  # Higher score kept
# ]
```

#### 5. `_search(params: dict) -> dict`

**Purpose**: Main search entry point with multilingual orchestration.

**Flow**:
```python
async def _search(params):
    # 1. Generate embedding for original query
    query_embedding = await embedder.create([query_text])

    if multilingual_enabled:
        # 2. Detect language
        source_lang = self._detect_language(query_text)

        # 3. Translate query
        translated_query = await self._translate_query(query_text, source_lang)

        # 4. Generate embedding for translated query
        translated_embedding = await embedder.create([translated_query])

        # 5. Execute both searches in parallel
        original_results, translated_results = await asyncio.gather(
            self._search_single_language(query_text, query_embedding, limit),
            self._search_single_language(translated_query, translated_embedding, limit)
        )

        # 6. Merge and deduplicate
        return self._merge_multilingual_results(original_results, translated_results)
    else:
        # Single-language search
        return await self._search_single_language(query_text, query_embedding, limit)
```

## Configuration

### Global Configuration

Set in `graphrag_settings`:

```python
# Enable/disable dual language search globally
ENABLE_MULTILINGUAL_SEARCH = True  # Default
```

### Per-Query Configuration

Override via `params` dictionary:

```python
# Enable for this query
await executor._search({
    "query": "What is the GDPR?",
    "limit": 10,
    "multilingual": True  # Override global setting
})

# Disable for this query (single language only)
await executor._search({
    "query": "What is the GDPR?",
    "limit": 10,
    "multilingual": False
})
```

## Usage Examples

### Example 1: Basic Multilingual Search

```python
from src.mcp.graph_retrieval.retriever import GraphContextRetriever

# Initialize retriever
retriever = GraphContextRetriever()

# Query in English
context = await retriever.retrieve("What is the Digital Services Act?")

# Internally:
# 1. Detects language: "en"
# 2. Translates: "Was ist das Digitale-Dienste-Gesetz?"
# 3. Searches both versions
# 4. Merges results
# 5. Returns combined context with entities, facts, relationships

print(f"Found {len(context.entities)} entities")
print(f"Found {len(context.facts)} facts")
```

### Example 2: German Query

```python
# Query in German
context = await retriever.retrieve("Wie funktioniert die DSGVO?")

# Internally:
# 1. Detects language: "de"
# 2. Translates: "How does the GDPR work?"
# 3. Searches both versions
# 4. Merges results
```

### Example 3: Direct Search API

```python
from src.mcp.graph_retrieval.retriever import MCPExecutor, Neo4jConfig

executor = MCPExecutor(Neo4jConfig())
await executor.initialize()

# Multilingual search
results = await executor._search({
    "query": "European Commission AI regulation",
    "limit": 10,
    "multilingual": True
})

print(f"Nodes: {len(results['nodes'])}")
print(f"Edges: {len(results['edges'])}")
print(f"Episodes: {len(results['episodes'])}")

# Single-language search
results_single = await executor._search({
    "query": "European Commission AI regulation",
    "limit": 10,
    "multilingual": False
})
```

### Example 4: Custom Tool Configuration

```python
from src.mcp.graph_retrieval.retriever import ToolPlanner, QueryAnalysis, QueryIntent

planner = ToolPlanner()
analysis = QueryAnalysis(
    original_query="GDPR compliance requirements",
    intent=QueryIntent.INFORMATION_SEEKING,
    entities=["GDPR"],
    complexity="simple"
)

plan = planner.create_plan(analysis)

# Execute with multilingual search
executor = MCPExecutor(Neo4jConfig())
results = await executor.execute_plan(plan)
# Each tool execution will use multilingual search
```

## Performance Characteristics

### Latency

| Component | Typical Latency | Notes |
|-----------|----------------|-------|
| Language Detection | <1ms | Stopword matching is very fast |
| Query Translation | 200-500ms | Claude Haiku API call |
| Embedding Generation | 50-150ms | Per query (2 queries = 100-300ms) |
| Parallel Search | 200-800ms | Both searches run concurrently |
| Result Merging | <10ms | UUID-based dictionary operations |
| **Total Overhead** | ~400-1400ms | Mostly translation + embeddings |

### Cost

Per query with multilingual search enabled:

```
Translation:     ~$0.0001 (Claude Haiku)
Embeddings (2):  ~$0.0002 (text-embedding-ada-002)
Neo4j queries:   No additional cost (same number of queries)
---------------------------------------------------
Total:           ~$0.0003 per multilingual query
```

### Trade-offs

**Advantages:**
- ✅ Language-agnostic: Users can query in either German or English
- ✅ Improved recall: Finds content regardless of indexing language
- ✅ Cross-lingual discovery: Connects German and English documents
- ✅ Automatic: No user configuration needed
- ✅ Minimal latency: Parallel execution keeps overhead low

**Disadvantages:**
- ❌ Slight cost increase: ~$0.0003 per query
- ❌ Added latency: ~400-1400ms (mostly translation)
- ❌ Translation errors: Rare but possible misinterpretations
- ❌ Increased API calls: 2x embeddings, 1x translation

## Hybrid Search Integration

The dual language search integrates seamlessly with the hybrid search (keyword + vector) feature:

```
For each language:
    Keyword Search (CONTAINS)
         +
    Vector Search (cosine similarity)
         ↓
    Score Fusion: 0.4 * keyword + 0.6 * vector
```

This means each language search provides:
1. **Keyword matching**: Exact term matches (GDPR, DSGVO, etc.)
2. **Semantic matching**: Conceptually similar content
3. **Combined scoring**: Best of both approaches

## Troubleshooting

### Issue: Translation returns original query

**Cause**: Claude API error or timeout

**Solution**: Check logs for translation errors. The system automatically falls back to original query, so search still works (single-language mode).

### Issue: Duplicate results in response

**Cause**: Merging logic not working correctly

**Check**: Verify that entities have consistent UUIDs across languages

### Issue: High latency

**Cause**: Translation or embedding generation taking too long

**Solutions**:
- Check APISIX/API gateway health
- Consider disabling multilingual search for time-sensitive queries
- Use `params['multilingual'] = False` for specific queries

### Issue: Poor translation quality

**Cause**: Complex technical terms or ambiguous phrasing

**Solution**: The system preserves known entities (GDPR, DSA, etc.), but complex sentences may need improvement. Consider enhancing the translation prompt in `_translate_query()`.

## Future Enhancements

1. **Caching translations**: Cache common query translations to reduce latency
2. **More languages**: Extend beyond German-English (French, Spanish, etc.)
3. **Custom stopwords**: Allow domain-specific stopword sets
4. **Translation quality metrics**: Log and monitor translation accuracy
5. **A/B testing**: Compare multilingual vs single-language search effectiveness

## References

- Main implementation: `retriever.py` (lines 452-665)
- Language detection: `_detect_language()` (lines 456-488)
- Translation: `_translate_query()` (lines 490-536)
- Merging: `_merge_multilingual_results()` (lines 538-573)
- Search orchestration: `_search()` (lines 597-665)
