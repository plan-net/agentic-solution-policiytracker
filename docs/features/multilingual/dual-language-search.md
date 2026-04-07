# Dual Language Search Feature

**Version**: 1.0
**Status**: Production
**Implementation**: `src/mcp/graph_retrieval/retriever.py`

## Overview

The Dual Language Search feature enables automatic cross-lingual retrieval for German and English queries in the Political Monitoring Agent. Users can query in either language and retrieve relevant results regardless of which language the content was originally indexed in.

## Key Benefits

- **Language-Agnostic Retrieval**: Users can query in either German or English
- **Improved Recall**: Finds relevant content regardless of indexing language
- **Cross-Lingual Discovery**: Connects German and English documents automatically
- **Preserves Relevance**: Score-based deduplication maintains ranking quality
- **Zero Configuration**: Works automatically without user intervention

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Query (EN or DE)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. Language Detection (_detect_language)                       │
│    • Stopword-based heuristics                                 │
│    • Returns 'en' or 'de'                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Query Translation (_translate_query)                        │
│    • Claude 3.5 Haiku translation                              │
│    • Preserves entities & technical terms                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Embedding Generation                                        │
│    • Original query → embedding_1                              │
│    • Translated query → embedding_2                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Parallel Search Execution (asyncio.gather)                  │
│    ┌─────────────────────┐     ┌─────────────────────┐        │
│    │ Search A (Original) │     │ Search B (Translated)│        │
│    │ • Keyword matching  │     │ • Keyword matching   │        │
│    │ • Vector similarity │     │ • Vector similarity  │        │
│    └─────────────────────┘     └─────────────────────┘        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Result Merging (_merge_multilingual_results)                │
│    • Deduplicate by UUID                                       │
│    • Keep highest scores                                       │
│    • Return combined nodes/edges/episodes                      │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Language Detection

**Method**: `_detect_language(text: str) -> str`

**Algorithm**:
- Splits query into individual words
- Counts matches against German stopword set (76 words)
- Counts matches against English stopword set (78 words)
- Returns 'de' if German count > English count, else 'en'

**German Stopwords Sample**:
```python
{'der', 'die', 'das', 'und', 'ist', 'von', 'mit', 'für', 'auf', ...}
```

**English Stopwords Sample**:
```python
{'the', 'and', 'is', 'of', 'with', 'for', 'on', 'a', 'an', ...}
```

**Example**:
```python
detected = _detect_language("Was ist die DSGVO?")
# Returns: 'de' (German detected)

detected = _detect_language("What is the GDPR?")
# Returns: 'en' (English detected)
```

#### 2. Query Translation

**Method**: `_translate_query(query: str, source_lang: str) -> str`

**Model**: Claude 3.5 Haiku (`claude-3-5-haiku-20241022`)

**Features**:
- Fast translation (200-500ms average)
- Cost-effective (~$0.0001 per query)
- Preserves entity names (GDPR, DSGVO, DSA, AI Act)
- Maintains technical and political terminology
- Fallback to original query if translation fails

**Translation Prompt**:
```
Translate the following text to {target_lang}.
Preserve entity names, acronyms (like GDPR, DSGVO, DSA, AI Act), and technical terms.
Output ONLY the translation, nothing else.

Text: {query}
```

**Example**:
```python
# English → German
translated = await _translate_query(
    "What is the GDPR regulation about?",
    source_lang="en"
)
# Returns: "Was ist die DSGVO-Verordnung?"

# German → English
translated = await _translate_query(
    "Wie funktioniert der Digital Services Act?",
    source_lang="de"
)
# Returns: "How does the Digital Services Act work?"
```

#### 3. Parallel Search Execution

**Method**: `_search_single_language(query_text, query_embedding, limit) -> dict`

**Process**:
1. Search entities with hybrid keyword + vector similarity
2. Search relationships with hybrid keyword + vector similarity
3. Search episodes (document chunks) with BM25 + vector
4. Return combined results

**Parallel Execution**:
```python
original_results, translated_results = await asyncio.gather(
    _search_single_language(query_text, query_embedding, limit),
    _search_single_language(translated_query, translated_embedding, limit)
)
```

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

#### 4. Result Merging

**Method**: `_merge_multilingual_results(results1, results2) -> dict`

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

# Results from German search (same entity, different name)
results2 = {
    "nodes": [
        {"uuid": "123", "name": "DSGVO", "score": 0.95},  # Higher score
        {"uuid": "789", "name": "Bundestag", "score": 0.7}
    ],
    "edges": [{"uuid": "456", "fact": "...", "score": 0.85}]  # Higher score
}

merged = _merge_multilingual_results(results1, results2)
# Result:
# nodes: [
#   {"uuid": "123", "name": "DSGVO", "score": 0.95},  # Higher score kept
#   {"uuid": "789", "name": "Bundestag", "score": 0.7}
# ]
# edges: [
#   {"uuid": "456", "fact": "...", "score": 0.85}  # Higher score kept
# ]
```

## Configuration

### Global Configuration

**File**: `src/config.py`

```python
class GraphRAGSettings:
    ENABLE_MULTILINGUAL_SEARCH: bool = True  # Default
```

**Environment Variable** (optional):
```bash
ENABLE_MULTILINGUAL_SEARCH=true
```

### Per-Query Configuration

You can override the global setting for specific queries:

```python
# Enable for this query
results = await executor._search({
    "query": "What is the GDPR?",
    "limit": 10,
    "multilingual": True  # Override global setting
})

# Disable for this query (single language only)
results = await executor._search({
    "query": "What is the GDPR?",
    "limit": 10,
    "multilingual": False
})
```

## Usage Examples

### Example 1: Basic English Query

```python
from src.mcp.graph_retrieval.retriever import GraphContextRetriever

# Initialize retriever
retriever = GraphContextRetriever()

# Query in English
context = await retriever.retrieve("What is the Digital Services Act?")

# Internally:
# 1. Detects language: "en"
# 2. Translates to: "Was ist das Digitale-Dienste-Gesetz?"
# 3. Searches both versions
# 4. Merges results
# 5. Returns combined context

print(f"Found {len(context.entities)} entities")
# Output: Found 15 entities (from both EN and DE searches)
```

### Example 2: Basic German Query

```python
# Query in German
context = await retriever.retrieve("Wie funktioniert die DSGVO?")

# Internally:
# 1. Detects language: "de"
# 2. Translates to: "How does the GDPR work?"
# 3. Searches both versions
# 4. Merges and returns combined results
```

### Example 3: Direct MCP Executor API

```python
from src.mcp.graph_retrieval.retriever import MCPExecutor, Neo4jConfig

executor = MCPExecutor(Neo4jConfig())
await executor.initialize()

# Multilingual search (default)
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

### Example 4: Integration with Claude Agent

```python
# In Claude agent context (via MCP server)
from src.claude_agent.agent import PolicyTrackerAgent

agent = PolicyTrackerAgent()

# User queries in German - automatic dual language search
response = await agent.query("Was sind die wichtigsten DSGVO-Anforderungen?")

# Agent internally:
# 1. Calls search_knowledge_graph MCP tool
# 2. Tool detects German, translates to English
# 3. Searches in both languages
# 4. Returns merged results
# 5. Agent synthesizes answer using both English and German sources
```

## Performance Characteristics

### Latency Breakdown

| Component | Typical Latency | Notes |
|-----------|----------------|-------|
| Language Detection | <1ms | Stopword matching is very fast |
| Query Translation | 200-500ms | Claude Haiku API call |
| Embedding Generation (Original) | 50-150ms | text-embedding-ada-002 |
| Embedding Generation (Translated) | 50-150ms | text-embedding-ada-002 |
| Parallel Search Execution | 200-800ms | Both searches run concurrently |
| Result Merging | <10ms | UUID-based dictionary operations |
| **Total Overhead** | ~400-1400ms | Primarily translation + embeddings |

**Note**: The parallel search means the dual-language overhead is mainly translation + 1 extra embedding (not 2x search time).

### Cost Analysis

**Per Query with Multilingual Search**:

```
Translation (Claude Haiku):     ~$0.0001
Embeddings (2 queries):         ~$0.0002  (text-embedding-ada-002)
Neo4j queries:                  No additional cost
-----------------------------------------------------------
Total per query:                ~$0.0003
```

**Volume Estimates**:
- 1,000 queries/month: ~$0.30/month
- 10,000 queries/month: ~$3.00/month
- 100,000 queries/month: ~$30.00/month

### Trade-offs

#### Advantages ✅

1. **Language-Agnostic**: Users can query in either German or English
2. **Improved Recall**: Finds content regardless of indexing language
3. **Cross-Lingual Discovery**: Connects German and English documents
4. **Automatic**: No user configuration needed
5. **Minimal Latency**: Parallel execution keeps overhead low (~500ms avg)
6. **Smart Deduplication**: UUID-based merging preserves relevance

#### Disadvantages ❌

1. **Slight Cost Increase**: ~$0.0003 per query (translation + extra embedding)
2. **Added Latency**: ~400-1400ms overhead (mostly translation)
3. **Translation Errors**: Rare but possible misinterpretations of complex terms
4. **Increased API Calls**: 2x embeddings + 1 translation per query

## Integration with Hybrid Search

The dual language search integrates seamlessly with the hybrid search (keyword + vector) feature:

```
For each language (original + translated):
    ┌─────────────────────────────────────┐
    │  Keyword Search (CONTAINS)          │
    │  • Exact term matching              │
    │  • Entity name matching             │
    └──────────────┬──────────────────────┘
                   │
                   ↓
    ┌─────────────────────────────────────┐
    │  Vector Search (cosine similarity)  │
    │  • Semantic matching                │
    │  • Conceptual similarity            │
    └──────────────┬──────────────────────┘
                   │
                   ↓
    ┌─────────────────────────────────────┐
    │  Score Fusion                       │
    │  • Entities: 0.4×keyword + 0.6×vec  │
    │  • Edges: 0.3×keyword + 0.7×vec     │
    │  • Episodes: 0.3×BM25 + 0.7×vec     │
    └─────────────────────────────────────┘
```

**Result**: Each language search provides both exact term matches AND semantically similar content, with results merged across both languages.

## Troubleshooting

### Issue 1: Translation Returns Original Query

**Symptoms**: Query is not translated, only original language is searched

**Cause**: Claude API error or timeout

**Solution**:
1. Check logs for translation errors:
   ```bash
   grep "Translation failed" logs/retriever.log
   ```
2. Verify APISIX/Claude API gateway health
3. The system automatically falls back to original query, so search still works (single-language mode)

### Issue 2: Duplicate Results in Response

**Symptoms**: Same entity appears multiple times with different names

**Cause**: Merging logic not working correctly due to inconsistent UUIDs

**Solution**:
1. Verify entities have consistent UUIDs across languages:
   ```cypher
   MATCH (e:Entity)
   WHERE e.name IN ['GDPR', 'DSGVO']
   RETURN e.uuid, e.name
   ```
2. If UUIDs differ, entities are truly different (not duplicates)
3. If UUIDs should be same, re-ingest documents to fix

### Issue 3: High Latency

**Symptoms**: Queries take >2 seconds consistently

**Cause**: Translation or embedding generation taking too long

**Solutions**:
1. Check APISIX/API gateway health
2. Consider disabling multilingual search for time-sensitive queries:
   ```python
   results = await executor._search({
       "query": "urgent query",
       "multilingual": False  # Disable for this query
   })
   ```
3. Monitor Claude API response times:
   ```bash
   grep "Translated query" logs/retriever.log | grep -o "time=[0-9]*ms"
   ```

### Issue 4: Poor Translation Quality

**Symptoms**: Complex technical terms or queries translated incorrectly

**Cause**: Claude Haiku struggling with ambiguous or very technical language

**Solution**:
1. The system already preserves known entities (GDPR, DSA, AI Act, etc.)
2. For complex sentences, consider enhancing the translation prompt in `_translate_query()`:
   ```python
   prompt = f"""Translate the following text to {target_lang}.
   This is a political/regulatory domain query.
   Preserve entity names, acronyms (like GDPR, DSGVO, DSA, AI Act), and technical terms.
   Maintain the original query intent and technical precision.
   Output ONLY the translation, nothing else.

   Text: {query}"""
   ```
3. Add domain-specific examples to the prompt for better accuracy

### Issue 5: Embeddings Not Generated

**Symptoms**: Vector search portion returns no results

**Cause**: APISIX embedder not initialized or OpenAI API issues

**Solution**:
1. Check embedder initialization:
   ```python
   embedder = await executor._get_embedder()
   if embedder is None:
       print("Embedder not initialized - check APISIX configuration")
   ```
2. Verify OpenAI API key in environment
3. The system gracefully falls back to keyword-only search

## Monitoring and Observability

### Key Metrics to Monitor

1. **Translation Success Rate**:
   ```bash
   # Count successful translations
   grep "Translated query" logs/retriever.log | wc -l

   # Count translation failures
   grep "Translation failed" logs/retriever.log | wc -l
   ```

2. **Language Distribution**:
   ```bash
   # Count German queries
   grep "Detected language: de" logs/retriever.log | wc -l

   # Count English queries
   grep "Detected language: en" logs/retriever.log | wc -l
   ```

3. **Average Latency**:
   ```bash
   # Extract translation times
   grep "Translated query" logs/retriever.log | grep -o "[0-9]*ms"
   ```

4. **Merge Statistics**:
   ```bash
   # See merged result counts
   grep "Merged multilingual results" logs/retriever.log
   ```

### Logging

The feature logs comprehensive information:

```python
logger.info(f"Multilingual search enabled. Detected language: {source_lang}")
logger.info(f"Translated query [{source_lang}→{target_lang}]: '{query[:50]}...' → '{translated[:50]}...'")
logger.info(f"Merged multilingual results: {len(merged['nodes'])} nodes, {len(merged['edges'])} edges, {len(merged['episodes'])} episodes")
```

### LangWatch Integration

All translation and search operations are tracked through APISIX, providing:
- Cost tracking per query
- Latency metrics
- Error rates
- Model usage statistics

Access LangWatch dashboard at: `http://localhost:3001` (if configured)

## Future Enhancements

### Planned Features

1. **Translation Caching**:
   - Cache common query translations to reduce latency
   - Redis-backed cache with TTL
   - Estimated improvement: 200-400ms saved on cached queries

2. **More Languages**:
   - Extend beyond German-English (French, Spanish, Italian)
   - Configurable language pairs
   - Multi-language search (3+ languages simultaneously)

3. **Custom Stopwords**:
   - Allow domain-specific stopword sets
   - Configurable via `config.yaml`
   - Better detection for political/legal terminology

4. **Translation Quality Metrics**:
   - Log and monitor translation accuracy
   - A/B testing of different translation prompts
   - Feedback loop for improving translations

5. **Adaptive Search Strategy**:
   - Disable translation for queries with high-confidence language detection
   - Use single-language search when query is very technical
   - Optimize based on query characteristics

## References

### Implementation Files

- **Main Implementation**: `src/mcp/graph_retrieval/retriever.py` (lines 452-665)
- **Language Detection**: `_detect_language()` (lines 456-488)
- **Translation**: `_translate_query()` (lines 490-536)
- **Merging**: `_merge_multilingual_results()` (lines 538-573)
- **Search Orchestration**: `_search()` (lines 597-665)

### Related Documentation

- [MCP Patterns](../../../.claude/mcp-patterns.md) - MCP server integration
- [Graphiti Patterns](../../../.claude/graphiti-patterns.md) - Knowledge graph patterns
- [Hybrid Search](./hybrid-search.md) - Keyword + vector search details

### External Resources

- [Claude 3.5 Haiku Documentation](https://docs.anthropic.com/claude/docs/models-overview)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [Neo4j Vector Search](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-13
**Maintained By**: Political Monitoring Agent Team
**Status**: Production Feature
