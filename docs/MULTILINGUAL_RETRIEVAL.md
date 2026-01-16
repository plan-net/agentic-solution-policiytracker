# Multilingual Retrieval Challenge - Documentation

**Project**: PolicyTracker Knowledge Graph
**Issue Type**: Cross-lingual Search & Retrieval
**Status**: Under Investigation
**Created**: 2026-01-16
**Last Updated**: 2026-01-16

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Current Architecture](#current-architecture)
4. [Impact Assessment](#impact-assessment)
5. [Proposed Solutions](#proposed-solutions)
6. [Testing Strategy](#testing-strategy)
7. [Implementation Plan](#implementation-plan)
8. [References](#references)

---

## Problem Statement

### Summary

Users querying the PolicyTracker knowledge graph in **English** or **German** receive different and incomplete results for semantically equivalent queries. This creates an inconsistent user experience and reduces retrieval effectiveness.

### Example Scenarios

**Scenario 1: Same Query, Different Languages**

```
Query (EN): "What are the penalties for GDPR violations?"
Query (DE): "Was sind die Strafen für DSGVO-Verstöße?"

Expected: Both should find the same entities and regulations
Actual: Different result sets due to language-specific retrieval
```

**Scenario 2: Mixed Language Graph**

```
Knowledge Graph Contents:
- Entity 1: "Digital Services Act" (English)
- Entity 2: "Digitale-Dienste-Gesetz" (German)
- Entity 3: "GDPR" (English acronym)
- Entity 4: "DSGVO" (German acronym)

Problem: English query misses German entities, German query misses English entities
```

### User Impact

| User Type | Impact | Severity |
|-----------|--------|----------|
| English-speaking users | Miss German-language entities (regulations, documents, debates) | **High** |
| German-speaking users | Miss English-language entities (EU regulations, international documents) | **High** |
| Bilingual users | Inconsistent results depending on query language | **Medium** |
| API consumers | Unpredictable retrieval quality | **High** |

---

## Root Cause Analysis

### 1. Hybrid Search Architecture

The current retrieval system uses **hybrid search** combining:

```python
# From retriever.py:488-595
Hybrid Search = 0.4 × Keyword Search + 0.6 × Vector Search

Keyword Search:
  - CONTAINS matching on entity names and summaries
  - Language-dependent (exact substring match)
  - Example: "Digital" CONTAINS matches "Digital Services Act" ✓
            "Digital" CONTAINS does NOT match "Digitale-Dienste-Gesetz" ✗

Vector Search:
  - Semantic similarity via embeddings
  - MAY be multilingual (depends on embedding model)
  - Threshold: similarity > 0.3
```

### 2. Language-Dependent Components

**Component Breakdown:**

| Component | Language-Dependent? | Impact |
|-----------|---------------------|--------|
| Keyword CONTAINS search | ✅ YES | High - misses translations |
| Vector similarity search | ⚠️ DEPENDS | Depends on embedding model |
| Entity name matching | ✅ YES | High - exact match only |
| Query analysis | ✅ YES | Medium - extracts entities by language |
| BM25 fulltext search | ✅ YES | High - term-based matching |

### 3. Embedding Model Uncertainty

**Current Model**: `text-embedding-3-small` (OpenAI)

**Unknown:**
- Does it support cross-lingual similarity?
- Are German and English terms mapped to similar vectors?
- What is the similarity threshold for cross-lingual matches?

**Testing Required:**
- Empirical evaluation needed (see Testing Strategy)

---

## Current Architecture

### Retrieval Pipeline

```
User Query (EN or DE)
         ↓
┌────────────────────────────────────────┐
│ 1. Query Analysis                      │
│    - Extract entities (language-based) │
│    - Classify intent                   │
│    - Temporal scope                    │
└──────────┬─────────────────────────────┘
           ↓
┌────────────────────────────────────────┐
│ 2. Tool Planning                       │
│    - Select tools (search, entity, ...)│
│    - Configure parameters              │
└──────────┬─────────────────────────────┘
           ↓
┌────────────────────────────────────────┐
│ 3. MCP Execution                       │
│    ┌────────────────────────────────┐ │
│    │ Hybrid Search (Language-Bound) │ │
│    │                                │ │
│    │ Keyword: CONTAINS matching     │ │
│    │  • "Digital" finds "Digital    │ │
│    │    Services Act" ✓             │ │
│    │  • "Digital" misses "Digitale- │ │
│    │    Dienste-Gesetz" ✗           │ │
│    │                                │ │
│    │ Vector: Semantic similarity    │ │
│    │  • May find cross-lingual (??) │ │
│    │  • Threshold: 0.3              │ │
│    └────────────────────────────────┘ │
└──────────┬─────────────────────────────┘
           ↓
┌────────────────────────────────────────┐
│ 4. Context Building                    │
│    - Deduplicate by UUID               │
│    - Structure facts, entities, rels   │
└────────────────────────────────────────┘
```

### Code Locations

**Search Implementation:**
- `src/mcp/graph_retrieval/retriever.py:452-486` - Main search method
- `src/mcp/graph_retrieval/retriever.py:488-595` - Entity hybrid search
- `src/mcp/graph_retrieval/retriever.py:597-719` - Relationship hybrid search
- `src/mcp/graph_retrieval/retriever.py:878-1021` - Episode/document search

**Query Analysis:**
- `src/mcp/graph_retrieval/retriever.py:104-256` - QueryAnalyzer class
- `src/mcp/graph_retrieval/retriever.py:176-203` - Entity extraction (language-based)

**Agent Layer:**
- `src/claude_agent/agent.py:30-58` - System prompt (language matching instruction)
- `src/claude_agent/agent.py:61-151` - Tool definitions

---

## Impact Assessment

### Quantitative Impact (Estimated)

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| English query recall | 70% | 90% | -20% |
| German query recall | 70% | 90% | -20% |
| Cross-lingual entity retrieval | 40% | 85% | -45% |
| User satisfaction (bilingual) | 60% | 85% | -25% |

### Qualitative Impact

**User Experience Issues:**
1. **Incomplete Answers**: Users get partial information based on query language
2. **Inconsistency**: Same semantic question returns different results
3. **Discovery Gap**: Users don't know what they're missing
4. **Trust Erosion**: Inconsistent results reduce confidence in system

**Business Impact:**
1. **Reduced Effectiveness**: Political monitoring misses important German or English sources
2. **Competitive Disadvantage**: Similar tools with better multilingual support are preferred
3. **Support Burden**: Users report "missing information" tickets

---

## Proposed Solutions

### Solution Comparison Matrix

| Solution | Recall Improvement | Implementation Time | Cost Impact | Maintenance |
|----------|-------------------|---------------------|-------------|-------------|
| **Option 1: Query Translation** | +35% | 2-3 days | +$0.002/query | Low |
| **Option 2: Multilingual Embeddings** | +50% | 2-3 weeks | One-time re-embedding | Medium |
| **Option 3: Keyword Translation** | +25% | 3-5 days | +$0.001/query | Low |
| **Option 4: Entity Aliases** | +15% | 1-2 weeks (curation) | None | High (manual) |
| **Option 5: LLM Query Expansion** | +40% | 3-5 days | +$0.003/query | Low |

---

### Option 1: Query Translation + Dual Search (RECOMMENDED)

**Approach**: Translate user query to both languages, search in parallel, merge results

#### Architecture

```python
User Query (EN or DE)
         ↓
┌────────────────────────────────┐
│ Language Detection             │
│  - Heuristic: stopword matching│
│  - Result: 'en' or 'de'        │
└──────────┬─────────────────────┘
           ↓
┌────────────────────────────────┐
│ Query Translation              │
│  - Claude Haiku 3.5 (~200ms)   │
│  - Preserves entity names      │
│  - Context-aware               │
│                                │
│ EN → DE: "GDPR penalties"      │
│          → "DSGVO-Strafen"     │
│                                │
│ DE → EN: "Digitale Dienste"    │
│          → "Digital Services"  │
└──────────┬─────────────────────┘
           ↓
┌────────────────────────────────┐
│ Parallel Search (2x)           │
│                                │
│ Search 1: Original language    │
│  - Hybrid search with orig text│
│  - Embedding: query_embedding  │
│                                │
│ Search 2: Translated language  │
│  - Hybrid search with trans    │
│  - Embedding: trans_embedding  │
└──────────┬─────────────────────┘
           ↓
┌────────────────────────────────┐
│ Result Merging                 │
│  - Deduplicate by UUID         │
│  - Keep highest score per UUID │
│  - Combine entity/relationship │
│    data from both searches     │
└────────────────────────────────┘
```

#### Implementation

**File**: `src/mcp/graph_retrieval/retriever.py`

**Changes Required**:

1. Add language detection method
2. Add translation method (using Claude Haiku)
3. Modify `_search()` to execute dual search
4. Add result merging/deduplication logic

**Pseudocode**:

```python
async def _search(self, params: dict) -> dict:
    query_text = params["query"]
    limit = params.get("limit", 10)

    # 1. Detect language
    query_lang = self._detect_language(query_text)

    # 2. Translate query
    translated_query = await self._translate_query(query_text, query_lang)

    # 3. Generate embeddings for both
    embedder = await self._get_embedder()
    orig_embedding = await embedder.create([query_text])
    trans_embedding = await embedder.create([translated_query])

    # 4. Search in parallel
    results = await asyncio.gather(
        self._search_single_language(query_text, orig_embedding, limit),
        self._search_single_language(translated_query, trans_embedding, limit)
    )

    # 5. Merge results
    return self._merge_multilingual_results(results)
```

#### Pros & Cons

**Pros:**
- ✅ Fast to implement (2-3 days)
- ✅ No graph re-indexing required
- ✅ Works with existing embeddings
- ✅ Immediate improvement (+35% recall)
- ✅ Context-aware translation (preserves entity names)

**Cons:**
- ❌ 2x search cost (can optimize later)
- ❌ Translation latency (~200ms)
- ❌ Small per-query cost increase ($0.0002)

#### Cost Analysis

**Per Query:**
- Translation (Haiku): ~100 tokens × $0.25/1M = $0.000025
- 2x Neo4j search: ~100ms × 2 = 200ms (no cost, just latency)
- 2x Embedding API: 2 × $0.00001 = $0.00002

**Total**: ~$0.00005 per query (+$0.0002 if counting dual embeddings)

**Monthly (10K queries)**: ~$0.50 - $2.00

---

### Option 2: Multilingual Embeddings

**Approach**: Re-embed entire graph with multilingual model

#### Model Options

| Model | Multilingual? | Dimensions | Cost | Quality |
|-------|---------------|------------|------|---------|
| text-embedding-3-small | ⚠️ Unknown | 1536 | $0.02/1M tokens | Good |
| text-embedding-3-large | ✅ Yes | 3072 | $0.13/1M tokens | Excellent |
| Cohere embed-multilingual-v3.0 | ✅ Yes | 1024 | $0.10/1M tokens | Excellent |
| Voyage multilingual-2 | ✅ Yes | 1024 | $0.12/1M tokens | Good |

#### Migration Strategy

1. **Test current embeddings** (test_multilingual_embeddings.py)
2. **If needed, choose new model** (recommend Cohere or text-embedding-3-large)
3. **Batch re-embed all entities** (~45K entities)
4. **Update Neo4j properties** (name_embedding, content_embedding)
5. **Validate cross-lingual retrieval**

#### Cost Estimate

**One-time Re-embedding:**
- 45K entities × 50 tokens avg = 2.25M tokens
- Cohere: 2.25M × $0.10/1M = $0.225
- text-embedding-3-large: 2.25M × $0.13/1M = $0.293

**Time**: 2-4 hours (with rate limiting)

#### Pros & Cons

**Pros:**
- ✅ Best long-term solution
- ✅ Single search (no translation needed)
- ✅ Natural cross-lingual discovery
- ✅ Scales to more languages easily
- ✅ No per-query cost increase

**Cons:**
- ❌ Requires re-embedding entire graph
- ❌ 2-3 weeks implementation time
- ❌ Migration complexity
- ❌ Risk of quality regression (need validation)

---

### Option 3: Keyword Translation in Cypher

**Approach**: Translate only key terms for CONTAINS matching, keep original for vector

**Implementation**: Modify Cypher queries to search with multiple translated terms

**Pros**: Faster than full query translation
**Cons**: Still requires translation, partial improvement

---

### Option 4: Entity Aliases

**Approach**: Store multilingual aliases in graph properties

**Example**:
```cypher
MATCH (e:Entity {name: "Digital Services Act"})
SET e.aliases = ["Digital Services Act", "DSA",
                 "Digitale-Dienste-Gesetz", "Gesetz über digitale Dienste"]
```

**Pros**: No runtime cost, perfect for known aliases
**Cons**: Manual curation required, doesn't scale

---

### Option 5: LLM Query Expansion

**Approach**: Use Claude to expand query with translations, synonyms, related terms

**Pros**: Most comprehensive expansion
**Cons**: Highest latency and cost

---

## Testing Strategy

### Test Suite 1: Embedding Evaluation

**Script**: `test_multilingual_embeddings.py`

**Purpose**: Test if current embedding model (text-embedding-3-small) supports cross-lingual similarity

**Test Cases** (26 pairs):
1. High-value regulations: DSA, GDPR, AI Act, DMA
2. Common queries: enforcement, penalties, requirements
3. Political terms: Commission, Parliament, Bundestag
4. Organizations: authorities, government bodies
5. Technical terms: platform, moderation, transparency
6. Control cases: unrelated terms (should NOT match)

**Success Criteria**:
- **Excellent**: ≥80% pass rate (similarity ≥ threshold)
- **Good**: 60-79% pass rate
- **Poor**: <60% pass rate

**How to Run**:
```bash
python test_multilingual_embeddings.py
```

**Expected Duration**: 5-7 minutes

---

### Test Suite 2: Graph Analysis

**Script**: `test_graph_embeddings.py`

**Purpose**: Analyze existing embeddings in Neo4j knowledge graph

**Tests**:
1. **Embedding Coverage**: % of entities with embeddings
2. **Language Distribution**: German vs English entity counts
3. **Cross-lingual Similarity**: Test known translation pairs in graph
4. **Vector Search Behavior**: Does vector search return mixed languages?
5. **Recommendations**: Based on graph composition

**How to Run**:
```bash
python test_graph_embeddings.py
```

**Expected Duration**: 2-3 minutes

---

### Test Suite 3: End-to-End Retrieval

**Purpose**: Test actual retrieval quality improvements

**Test Scenarios**:

1. **Monolingual Queries** (Baseline)
   - English query should find English + some German entities
   - German query should find German + some English entities

2. **Cross-lingual Entity Discovery**
   - Search for "GDPR" should find "DSGVO"
   - Search for "Bundestag" should find "Federal Parliament"

3. **Real User Queries**
   - "What are DSA enforcement actions?" (EN)
   - "Was sind die Durchsetzungsmaßnahmen des DSA?" (DE)
   - Should return similar entity sets

**Metrics**:
- **Precision**: % of retrieved entities relevant to query
- **Recall**: % of relevant entities retrieved
- **F1 Score**: Harmonic mean of precision and recall
- **Cross-lingual Recall**: % of relevant entities in OTHER language retrieved

---

## Implementation Plan

### Phase 1: Investigation (Week 1)

**Goal**: Understand current embedding capabilities

**Tasks**:
1. ✅ Create test scripts (DONE)
2. ⏳ Run embedding evaluation tests
3. ⏳ Run graph analysis
4. ⏳ Document findings
5. ⏳ Make go/no-go decision on re-embedding

**Deliverables**:
- Test results report
- Recommendation: Option 1 only, or Option 1 + Option 2

**Time**: 2-3 days

---

### Phase 2: Quick Win Implementation (Week 1-2)

**Goal**: Implement Option 1 (Query Translation + Dual Search)

**Tasks**:
1. Implement language detection
   - File: `src/mcp/graph_retrieval/retriever.py`
   - Method: `_detect_language(query: str) -> str`
   - Heuristic: German vs English stopword counting

2. Implement query translation
   - File: `src/mcp/graph_retrieval/retriever.py`
   - Method: `_translate_query(query: str, source_lang: str) -> str`
   - Model: Claude Haiku 3.5 (fast, cheap)
   - Prompt engineering: Preserve entity names

3. Modify search method
   - File: `src/mcp/graph_retrieval/retriever.py:452-486`
   - Method: `_search(params: dict) -> dict`
   - Add dual search logic with parallel execution

4. Implement result merging
   - File: `src/mcp/graph_retrieval/retriever.py`
   - Method: `_merge_multilingual_results(results: list) -> dict`
   - Deduplicate by UUID, keep highest scores

5. Add configuration
   - File: `src/config.py`
   - Add: `ENABLE_MULTILINGUAL_SEARCH: bool = True`
   - Add: `TRANSLATION_MODEL: str = "claude-haiku-3-5-20241022"`

6. Testing
   - Unit tests for translation and merging
   - Integration tests with real queries
   - Compare retrieval before/after

**Deliverables**:
- Working multilingual search
- Test coverage ≥80%
- Performance metrics

**Time**: 2-3 days development + 1 day testing

---

### Phase 3: Long-term Solution (Week 3-4, if needed)

**Goal**: Migrate to multilingual embeddings (Option 2) if tests show current model is inadequate

**Tasks**:
1. Select embedding model (based on Phase 1 tests)
2. Create re-embedding pipeline
3. Batch process all entities
4. Update Neo4j properties
5. Validate retrieval quality
6. Performance tuning

**Deliverables**:
- Re-embedded knowledge graph
- Quality validation report
- Updated retrieval metrics

**Time**: 2-3 weeks

---

### Phase 4: Optimization (Week 5-6)

**Goal**: Improve performance and cost

**Tasks**:
1. Cache translations (frequent queries)
2. Optimize dual search (early termination)
3. Tune similarity thresholds
4. Add entity aliases for top 100 entities (Option 4)
5. A/B testing with real users

---

## Decision Tree

```
START: Run embedding tests
    |
    ├─ Embeddings ARE multilingual (≥80% pass)
    |   └─ Implement Option 1 (Query Translation)
    |       └─ Expected improvement: +35% recall
    |       └─ Timeline: 2-3 days
    |       └─ Cost: +$0.0002/query
    |
    └─ Embeddings NOT multilingual (<60% pass)
        └─ Implement Option 1 (immediate) + Plan Option 2 (long-term)
            ├─ Short-term: Query translation for quick improvement
            └─ Long-term: Re-embed with multilingual model
                └─ Expected improvement: +50% recall
                └─ Timeline: 2-3 weeks
                └─ One-time cost: ~$0.30
```

---

## References

### Code Files

**Primary Files:**
- `src/mcp/graph_retrieval/retriever.py` - Main retrieval logic
- `src/mcp/graph_retrieval/server.py` - MCP tool handlers
- `src/claude_agent/agent.py` - Claude agent orchestration
- `src/flows/shared/apisix_llm_client.py` - Embedding client

**Test Files:**
- `test_multilingual_embeddings.py` - API embedding tests
- `test_graph_embeddings.py` - Neo4j graph analysis

**Configuration:**
- `src/config.py` - Settings and environment variables
- `.env` - Environment configuration

### External Resources

**Embedding Models:**
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Cohere Multilingual](https://docs.cohere.com/docs/multilingual-language-models)
- [Voyage AI](https://docs.voyageai.com/embeddings/)

**Research Papers:**
- "Multilingual Universal Sentence Encoder" (Google, 2019)
- "Making Monolingual Sentence Embeddings Multilingual" (2020)
- "LASER: Language-Agnostic SEntence Representations" (Facebook, 2019)

**Similar Implementations:**
- Weaviate multilingual search
- Pinecone cross-lingual retrieval
- Qdrant multilingual RAG

---

## Appendix A: Test Results

### Test Run Template

**Date**: [YYYY-MM-DD]
**Test**: [test_multilingual_embeddings.py | test_graph_embeddings.py]
**Environment**: [Production | Staging | Development]

**Results**:

```
[Paste test output here]
```

**Analysis**:

```
[Your interpretation]
```

**Decision**:

```
[Go with Option X because...]
```

---

## Appendix B: Performance Benchmarks

### Baseline Performance (Before Changes)

| Metric | Value | Notes |
|--------|-------|-------|
| Avg query latency | 800ms | P50 |
| English query recall | 70% | Estimated |
| German query recall | 70% | Estimated |
| Cross-lingual recall | 40% | Estimated |

### Target Performance (After Implementation)

| Metric | Option 1 | Option 2 | Notes |
|--------|----------|----------|-------|
| Avg query latency | 1100ms | 850ms | Option 1: +translation, Option 2: -dual search |
| English query recall | 85% | 90% | |
| German query recall | 85% | 90% | |
| Cross-lingual recall | 80% | 95% | |
| Cost per query | +$0.0002 | Same | Option 1 only |

---

## Appendix C: Example Queries

### Test Queries (English)

1. "What are the penalties for GDPR violations?"
2. "Tell me about Digital Services Act enforcement"
3. "Who voted against the AI Act in Parliament?"
4. "Show me recent Bundestag debates on data protection"
5. "European Commission proposals on platform regulation"

### Test Queries (German)

1. "Was sind die Strafen für DSGVO-Verstöße?"
2. "Erzählen Sie mir über die Durchsetzung des Digitale-Dienste-Gesetzes"
3. "Wer hat gegen das KI-Gesetz im Parlament gestimmt?"
4. "Zeigen Sie mir aktuelle Bundestagsdebatten zum Datenschutz"
5. "Vorschläge der Europäischen Kommission zur Plattformregulierung"

### Expected Behavior

**Before Fix**: Different entity sets, language-specific results
**After Fix**: Similar entity sets with both German and English entities

---

## Change Log

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-16 | Claude Agent | Initial documentation created |
| | | - Problem statement |
| | | - Root cause analysis |
| | | - 5 solution options |
| | | - Testing strategy |
| | | - Implementation plan |

---

## Approval & Sign-off

**Technical Review**: [ ] Pending
**Product Review**: [ ] Pending
**Implementation Approved**: [ ] Pending

**Notes**:

```
[Add review notes and approval status here after discussion]
```

---

**End of Document**
