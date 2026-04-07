# Document Processing Pipeline - Comprehensive Guide

## Overview

The document processing pipeline transforms raw markdown documents into a high-quality temporal knowledge graph. The pipeline is designed with multiple quality layers that work together to maximize entity/relationship extraction accuracy while controlling LLM costs.

**Key Design Principles:**
1. **Small chunk sizes** for better entity and edge detection quality
2. **Intelligent chunk limiting** to control LLM costs (each chunk triggers ~5-10 LLM calls)
3. **Multi-layer deduplication** at document, entity, and alias levels
4. **Preserve all content** even when chunk limits are hit (embed-only fallback)
5. **Political domain schema** with 28 entity types and 52 relationship types

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT PROCESSING PIPELINE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. FILE DISCOVERY & DEDUPLICATION CHECK                            │
│     └── DocumentTracker (JSON-based, file-locked)                   │
│                                                                     │
│  2. DOCUMENT READING & ENCODING DETECTION                           │
│     └── UTF-8 → Latin-1 fallback                                    │
│                                                                     │
│  3. QUALITY VALIDATION                                              │
│     └── Min 200 chars, paragraph check, not aggregation page        │
│                                                                     │
│  4. PREPROCESSING                                                   │
│     ├── Frontmatter extraction (YAML metadata preserved)            │
│     ├── HTML entity decoding                                        │
│     ├── Promotional content removal                                 │
│     ├── Link removal (images, markdown, bare URLs)                  │
│     ├── Duplicate line removal                                      │
│     └── Whitespace normalization                                    │
│                                                                     │
│  5. ENTITY NAME NORMALIZATION                                       │
│     └── 81 abbreviation mappings (EU, GDPR, company names, etc.)    │
│                                                                     │
│  6. HYBRID CHUNKING (3-Tier Strategy)                               │
│     ├── Tier 1: Semantic (markdown headers)                         │
│     ├── Tier 2: Paragraph boundaries                                │
│     ├── Tier 3: Fixed-size token splitting                          │
│     ├── Adaptive chunk sizing (for large documents)                 │
│     └── Chunk limit fallback (smart_sample_embed, etc.)             │
│                                                                     │
│  7. GRAPHITI PROCESSING (per chunk)                                 │
│     ├── Full extraction: Entity + relationship extraction via LLM   │
│     ├── Embed-only: Content embedding without LLM extraction        │
│     ├── Chain linking (previous_episode_uuids)                      │
│     └── Custom political schema (28 entities, 52 edges)             │
│                                                                      │
│  8. ENTITY DEDUPLICATION (Phase 2)                                  │
│     ├── EntityNormalizer (pre-extraction text normalization)         │
│     ├── EntityRegistry (Neo4j canonical entity tracking)            │
│     └── DeduplicatingGraphitiClient (post-extraction resolution)    │
│                                                                      │
│  9. EPISODE EMBEDDING                                               │
│     └── Content embedding for semantic search (1536-dim, cosine)    │
│                                                                      │
│  10. TRACKING & METRICS                                             │
│      ├── DocumentTracker (per-chunk metrics, canonical UUIDs)       │
│      └── Cross-chunk duplicate detection                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Configuration Reference

All settings are in `src/config.py` (class `GraphRAGSettings`) and `.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_EPISODE_TOKENS` | 1500 | Max tokens per chunk. **Intentionally small** for better extraction quality |
| `CHUNK_OVERLAP_PERCENTAGE` | 10 | Overlap between chunks (%) for context preservation |
| `MIN_CHUNK_TOKENS` | 50 | Minimum viable chunk size |
| `MAX_CHUNKS_PER_DOCUMENT` | 0 (unlimited) | Limits chunks per document. Set to 5-20 to control cost |
| `ADAPTIVE_CHUNK_SIZE_ENABLED` | true | Dynamically increase chunk size for large documents |
| `MAX_ADAPTIVE_TOKENS` | 3000-8000 | Ceiling for adaptive chunk sizing |
| `CHUNK_LIMIT_FALLBACK_STRATEGY` | `smart_sample_embed` | What to do when adaptive sizing still exceeds limit |
| `ENABLE_DEDUPLICATION` | true | Phase 2 entity deduplication via EntityRegistry |
| `ENABLE_FUZZY_MATCHING` | true | Levenshtein fuzzy matching in EntityRegistry |
| `ENABLE_PROMPT_CACHE_OPTIMIZATION` | true | LLM prompt caching (50-90% cost reduction) |
| `ENABLE_LINK_REMOVAL` | true | Remove URLs from content before processing |
| `GRAPHITI_LLM_PROVIDER` | openai | LLM provider for entity extraction |

---

## Stage 1: File Discovery & Deduplication

### Source Directories
```
data/input/
├── news/YYYY-MM/          # ETL-collected news articles
├── policy/YYYY-MM/         # ETL-collected policy documents
└── documents_md/           # Manual uploads
```

Supported extensions: `.txt`, `.md`

### Deduplication Check
**File:** `src/flows/data_ingestion/document_tracker.py`

Before processing, `DocumentTracker` checks a JSON state file (`data/processed_documents.json`) to skip already-processed documents. Uses `fcntl` file locking for concurrent Ray actor access.

```python
if not self.clear_mode and self.tracker.is_processed(str(doc_path)):
    return {"status": "skipped", "reason": "already_processed"}
```

---

## Stage 2: Document Reading

**File:** `document_processor.py:_read_document()`

Reads with UTF-8, falls back to Latin-1 for legacy documents.

---

## Stage 3: Quality Validation

**File:** `src/flows/data_ingestion/document_preprocessor.py:validate_document_quality()`

Documents are rejected if they fail quality checks:

| Check | Threshold | Purpose |
|-------|-----------|---------|
| Minimum content | 200 characters | Skip empty/tiny documents |
| Paragraph check | At least 1 paragraph > 100 chars | Skip list-only content |
| Aggregation detection | Pattern matching | Skip news aggregation pages (mostly headlines) |
| Content ratio | Enough real text vs. short lines | Skip low-content documents |

Rejected documents are marked as `skipped` with reason in the tracker.

---

## Stage 4: Preprocessing

**File:** `src/flows/data_ingestion/document_preprocessor.py:preprocess_document()`

A 7-step cleaning pipeline that typically achieves **15-50% token reduction**:

### 4.1 Frontmatter Extraction
Preserves YAML frontmatter (`---` delimited) as metadata, processes only the body.

### 4.2 HTML Entity Decoding
Converts `&amp;`, `&lt;`, `&gt;`, `&nbsp;` etc. to their character equivalents.

### 4.3 Promotional Content Removal
Removes 8 common marketing patterns found in scraped web content:
- "7 Best Stocks for the Next 30 Days"
- "Want the latest recommendations"
- "Click to get this free report"
- etc.

### 4.4 Link Removal
Strips three types of links:
- Image links: `![alt](url)` → removed entirely
- Markdown links: `[text](url)` → removed (both text and URL)
- Bare URLs: `https://...`, `www....` → removed

**Why:** URLs add noise to entity extraction and waste tokens.

### 4.5 Duplicate Line Removal
Consecutive identical lines are collapsed to one. Common in scraped content where navigation elements repeat.

### 4.6 Whitespace Normalization
Multiple blank lines → single blank line. Trailing whitespace removed per line.

### 4.7 Document Reassembly
Frontmatter is prepended back to the cleaned body.

---

## Stage 5: Entity Name Normalization

**File:** `src/flows/data_ingestion/entity_normalizer.py`

Applied to text **before** Graphiti extraction to reduce duplicate entity creation at the source.

### 81 Default Mappings (highlights)

| Category | Examples |
|----------|---------|
| **EU Institutions** | EU → European Union, EC → European Commission, EP → European Parliament, ECJ → European Court of Justice |
| **US/UK** | US/U.S./USA → United States, UK/U.K. → United Kingdom |
| **German Politics** | BT → Bundestag, BR → Bundesrat, SPD/CDU/CSU/FDP/Grüne → full names |
| **Regulations** | GDPR → General Data Protection Regulation, DSA → Digital Services Act, DMA → Digital Markets Act |
| **Tech Companies** | Meta Platforms/Facebook → Meta, Google LLC/Alphabet Inc. → Google, Amazon.com → Amazon |

### Normalization Features
- **Case-insensitive** matching by default
- **Longest-first** replacement to avoid partial matches
- **Possessive handling**: "EU's" → "European Union's"
- **Whitespace normalization**: tabs/multiple spaces → single space
- **Pre-compiled regex** patterns for performance

---

## Stage 6: Hybrid Chunking

**File:** `src/flows/data_ingestion/document_chunker.py`

This is the most sophisticated stage, designed to balance extraction quality against cost.

### 6.1 Three-Tier Chunking Strategy

```
Document Text
     │
     ▼
┌─────────────────────────┐
│ Tier 1: Semantic Split  │  Split by markdown headers (#, ##, ###)
│ (Header-based)          │  Preserves document structure
└────────────┬────────────┘
             │ If section > max_tokens
             ▼
┌─────────────────────────┐
│ Tier 2: Paragraph Split │  Split by \n\n, \n, ". ", " "
│ (Recursive)             │  Maintains semantic coherence
└────────────┬────────────┘
             │ If still > max_tokens
             ▼
┌─────────────────────────┐
│ Tier 3: Fixed-Size      │  Token-based splitting with overlap
│ (Token-accurate)        │  Guarantees all chunks fit
└─────────────────────────┘
```

**Why small chunks (1500 tokens)?** Smaller chunks produce better entity and relationship extraction because:
- LLMs can focus on fewer entities per chunk
- Edge detection is more accurate with focused context
- Reduces hallucination of non-existent relationships
- Each chunk triggers ~5-10 sequential LLM calls via `add_episode()`

### 6.2 Chunk Output Structure

Each chunk includes rich metadata:

```python
{
    "text": "chunk content...",
    "metadata": {"Header 2": "Section Title"},  # From markdown headers
    "boundary_type": "header|paragraph|fixed_size",
    "chunk_index": 0,
    "total_chunks": 5,
    "token_count": 1234,
    "has_frontmatter": True,
    "processing_mode": "full|embed_only",  # From fallback strategy
}
```

### 6.3 Adaptive Chunk Sizing

When a document would produce more chunks than `MAX_CHUNKS_PER_DOCUMENT`, the chunker dynamically increases chunk size:

```
Example: 50,000 token document, MAX_CHUNKS=5, default max_tokens=1500
  → Would produce ~33 chunks (too many)
  → Adaptive: new_max_tokens = ceil(50000 / 5) = 10000
  → Capped at MAX_ADAPTIVE_TOKENS (e.g., 3000-8000)
  → Re-chunk with larger token limit
```

**Formula:** `new_step = (total_tokens + max_chunks - 1) // max_chunks`

Capped at `MAX_ADAPTIVE_TOKENS` to prevent unreasonably large chunks that degrade extraction quality.

### 6.4 Chunk Limit Fallback Strategies

When adaptive sizing still produces too many chunks, a fallback strategy is applied:

| Strategy | Behavior | Content Loss | Best For |
|----------|----------|-------------|----------|
| `truncate` | Keep first N chunks only | Drops end of document | Quick processing, less important docs |
| `smart_sample` | Keep first 30% + last 20% + sampled middle | Drops unsampled middle | Important docs, cost-sensitive |
| `embed_only` | First N chunks get full extraction, rest saved as episodes without LLM | None (all content preserved as episodes) | Content preservation, cost-sensitive |
| `smart_sample_embed` | Smart-selected chunks get full extraction, all remaining saved as embed-only episodes | **None** (all content preserved) | **Recommended** - best balance |

#### `smart_sample_embed` (Recommended)

This is the default strategy. It works in two passes:

1. **Selection pass**: Identifies "important" chunks using smart sampling (first 30%, last 20%, evenly-sampled middle)
2. **Processing pass**: Selected chunks → full LLM extraction (entities, relationships). All remaining chunks → saved as lightweight episodes with content embeddings only

**Benefits:**
- All document content is searchable via semantic search
- Important sections (start, end, sampled middle) get full entity extraction
- Dramatically reduces LLM costs for large documents
- No content is ever lost

#### Lightweight Episodes (embed-only mode)

When a chunk is marked as `embed_only`:

```python
# Creates an EpisodicNode directly (no LLM calls)
episode = EpisodicNode(
    name=episode_name,
    group_id=group_id,
    source=EpisodeType.text,
    content=chunk_text,
    valid_at=reference_time,
    entity_edges=[],  # No entity extraction
)
await episode.save(driver)

# Still generates content embedding for semantic search
await embedding_manager.add_content_embedding(episode.uuid, chunk_text)
```

**Cost comparison:**
- Full extraction: ~5-10 LLM calls per chunk ($0.01-0.05 per chunk)
- Embed-only: 1 embedding API call per chunk ($0.000004 per chunk)
- **~2,500-12,500x cheaper per chunk**

---

## Stage 7: Graphiti Processing

**File:** `document_processor.py:_process_chunked_document()`

Each chunk is processed through Graphiti's `add_episode()` with the custom political schema.

### 7.1 Custom Political Schema

**File:** `src/graphrag/political_schema_v5.py`

**28 Entity Types** organized in tiers:

| Tier | Category | Entity Types |
|------|----------|-------------|
| 1 | Legislative Process | LegislativeProposal, LegislativeBody, Committee, Document, Vote |
| 2 | Outcomes | Policy, Regulation |
| 3 | Actors | Politician, Person, PoliticalParty, GovernmentAgency, LobbyGroup |
| 4 | Business | Company, Industry, ComplianceObligation |
| 5 | Process | ConsultationProcess, EnforcementAction |
| 6 | Geographic | Jurisdiction |
| 7 | Technical | LegalFramework, TechnicalStandard |
| 8 | German Bundestag | Drucksache, DrucksachePage, Plenarprotokoll, Vorgang, Vorgangsposition, Aktivitaet, Wahlperiode, BundestagPerson, BundestagFraktion |

**52 Edge Types** defining valid relationships between entity pairs, with an edge type map that constrains which edges can connect which entity types.

### 7.2 Chain Linking

Multi-chunk documents are linked sequentially via `previous_episode_uuids`:

```
Chunk 0 ──→ Chunk 1 ──→ Chunk 2 ──→ Chunk 3
(prev=None)  (prev=[0])  (prev=[1])  (prev=[2])
```

This preserves document coherence in the knowledge graph and enables traversal of related episodes.

### 7.3 LLM Pipeline per Chunk

Each `add_episode()` call triggers approximately:
1. **Entity extraction** - LLM identifies entities matching the 28-type schema
2. **Entity type classification** - LLM classifies each entity
3. **Relationship extraction** - LLM identifies edges matching the 52-edge schema
4. **Entity resolution** - Graphiti matches against existing entities in Neo4j
5. **Edge deduplication** - Graphiti merges duplicate relationships
6. **Community updates** - (if enabled) Update community memberships

**This is why small chunks and chunk limiting are critical for cost control.**

### 7.4 Prompt Cache Optimization

When `ENABLE_PROMPT_CACHE_OPTIMIZATION=true`:
- **OpenAI**: Moves schema definitions to developer message for automatic prefix caching (50% discount on cached tokens)
- **Anthropic**: Injects `cache_control` breakpoints on schema blocks (90% discount on cached tokens)

This significantly reduces cost since the schema is large and identical across all chunks.

---

## Stage 8: Entity Deduplication (Phase 2)

A three-layer deduplication system prevents the knowledge graph from being polluted with duplicate entities.

### Layer 1: Pre-extraction Normalization
**Component:** `EntityNormalizer` (applied in Stage 5)
- Normalizes text before Graphiti sees it
- "EU" in document → "European Union" in text → Graphiti extracts "European Union"

### Layer 2: EntityRegistry (Neo4j-backed)
**File:** `src/flows/data_ingestion/entity_registry.py`

Maintains a registry of canonical entities and aliases in Neo4j:

```
CanonicalEntity {uuid, name, entity_type, usage_count}
    ↑
    └── ALIAS_OF ── EntityAlias {alias, confidence, source}
```

**3-step resolution strategy:**
1. **Exact match** (case-insensitive) on canonical name
2. **Alias match** with confidence score
3. **Fuzzy match** using Levenshtein similarity ≥ 0.85 (requires APOC)

### Layer 3: DeduplicatingGraphitiClient
**File:** `src/flows/data_ingestion/deduplicating_graphiti_client.py`

Wraps the base Graphiti client:

```
Text → EntityNormalizer → Graphiti (extract entities) → EntityRegistry (resolve to canonical) → Neo4j
```

For each extracted entity:
1. Validate entity name (≥ 2 chars, ≥ 2 alphanumeric)
2. Check EntityRegistry for canonical match
3. If match found: reuse canonical UUID, register as alias
4. If no match: register as new canonical entity

---

## Stage 9: Episode Embedding

**File:** `src/graphrag/episode_embedding_manager.py`

After each episode is saved (both full and embed-only), a content embedding is generated for semantic search.

- **Model:** `text-embedding-3-small` (1536 dimensions)
- **Index:** `episodic_content_embedding_index` (vector, cosine similarity)
- **Fulltext index:** `episodic_content_fulltext` (BM25 on content + name)

This enables hybrid search:
- BM25 keyword search (weight: 0.3)
- Vector similarity search (weight: 0.7)
- Score fusion for combined ranking

---

## Stage 10: Tracking & Metrics

**File:** `src/flows/data_ingestion/document_tracker.py`

After processing, detailed metrics are recorded per document:

```json
{
  "doc_path": {
    "status": "completed",
    "processed_at": "2025-01-14T10:30:00",
    "total_chunks": 5,
    "successful_chunks": 5,
    "chunk_results": {
      "chunk_0": {
        "episode_uuid": "uuid",
        "entities": ["European Union", "Digital Services Act"],
        "entity_uuids": ["uuid1", "uuid2"],
        "canonical_uuids": ["c-uuid1", "c-uuid2"],
        "entity_count": 2,
        "relationships": 3,
        "boundary_type": "header"
      }
    },
    "cross_chunk_duplicates": {
      "European Union": ["chunk_0", "chunk_2", "chunk_4"]
    },
    "canonical_entity_count": 8
  }
}
```

---

## Parallel Processing with Ray

**File:** `document_processor.py` (both `DocumentProcessorActor` and `SimpleDocumentProcessor`)

### Ray Actor Architecture

```
SimpleDocumentProcessor (coordinator)
    │
    ├── DocumentProcessorActor (actor 0) ──→ Batch [doc1, doc2, ...]
    ├── DocumentProcessorActor (actor 1) ──→ Batch [doc3, doc4, ...]
    └── DocumentProcessorActor (actor 2) ──→ Batch [doc5, doc6, ...]
```

Each actor:
- Maintains its own Graphiti client connection
- Processes documents sequentially within its batch
- Reports progress via `get_progress()` method
- Tracks entities/relationships/chunks independently

**Typical throughput:** 20-40 documents/minute with 3 Ray actors.

---

## Cost Control Summary

The pipeline has multiple cost control mechanisms:

| Mechanism | Savings | Where |
|-----------|---------|-------|
| **Preprocessing** | 15-50% token reduction | Stage 4 |
| **Entity normalization** | Fewer duplicate entities | Stage 5 |
| **Small chunk size** (1500 tokens) | Better extraction quality per LLM call | Stage 6 |
| **Chunk limiting** (`MAX_CHUNKS_PER_DOCUMENT`) | Caps LLM calls per document | Stage 6 |
| **Adaptive sizing** | Fewer, larger chunks for big docs | Stage 6 |
| **smart_sample_embed fallback** | Only important chunks get LLM extraction | Stage 6 |
| **Embed-only episodes** | 2,500-12,500x cheaper per overflow chunk | Stage 7 |
| **Prompt cache optimization** | 50-90% on repeated schema tokens | Stage 7 |
| **Entity deduplication** | Fewer redundant Neo4j writes | Stage 8 |

### Cost Estimation

For a typical batch of 100 documents:

| Component | Cost (OpenAI) | Notes |
|-----------|--------------|-------|
| Entity extraction (full chunks) | $1-5 | ~5-10 LLM calls per chunk |
| Embeddings (all chunks) | $0.02 | text-embedding-3-small |
| Prompt cache savings | -30-50% | On extraction cost |
| **Total per batch** | **$0.50-3.00** | With MAX_CHUNKS=5, smart_sample_embed |

---

## File Reference

| File | Purpose |
|------|---------|
| `src/flows/data_ingestion/document_processor.py` | Main orchestrator (Ray actors + SimpleDocumentProcessor) |
| `src/flows/data_ingestion/document_chunker.py` | HybridDocumentChunker with adaptive sizing |
| `src/flows/data_ingestion/document_preprocessor.py` | 7-step cleaning pipeline + quality validation |
| `src/flows/data_ingestion/entity_normalizer.py` | 81 abbreviation mappings + text normalization |
| `src/flows/data_ingestion/entity_registry.py` | Neo4j canonical entity + alias management |
| `src/flows/data_ingestion/deduplicating_graphiti_client.py` | Graphiti wrapper with entity deduplication |
| `src/flows/data_ingestion/document_tracker.py` | JSON-based processing tracker with file locking |
| `src/graphrag/political_schema_v5.py` | 28 entity types, 52 edge types, edge type map |
| `src/graphrag/episode_embedding_manager.py` | Episode content embedding for semantic search |
| `src/config.py` | GraphRAGSettings with all configurable parameters |
| `src/flows/shared/apisix_llm_client.py` | LLM client factory with APISIX cost tracking |

---

## Environment Variables

Key `.env` settings for document processing:

```bash
# Chunk sizing
MAX_EPISODE_TOKENS=1500              # Small for quality
CHUNK_OVERLAP_PERCENTAGE=10          # Context preservation
MAX_CHUNKS_PER_DOCUMENT=5            # Cost control
ADAPTIVE_CHUNK_SIZE_ENABLED=false    # Dynamic sizing
MAX_ADAPTIVE_TOKENS=3000             # Adaptive ceiling
CHUNK_LIMIT_FALLBACK_STRATEGY=smart_sample_embed  # Recommended

# Features
ENABLE_DEDUPLICATION=true            # Phase 2 entity dedup
ENABLE_FUZZY_MATCHING=true           # Levenshtein matching
ENABLE_PROMPT_CACHE_OPTIMIZATION=true  # LLM cache savings

# LLM Provider
GRAPHITI_LLM_PROVIDER=openai         # or "anthropic"

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=politicalmonitoring.v3
```

---

**Version:** 0.2.2
**Last Updated:** 2026-03-17
**Status:** Production
**Supersedes:** `.claude/markdown-ingestion-patterns.md` (basic pipeline overview)
