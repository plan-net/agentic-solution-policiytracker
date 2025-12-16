# Community Generation Patterns

This document describes the community detection and summarization patterns used in the PolicyTracker knowledge graph.

## Overview

Communities are clusters of related entities in the knowledge graph, automatically detected using the Leiden algorithm and enriched with LLM-generated summaries for semantic search.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Community Generation Pipeline                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Entity     │───▶│   Leiden     │───▶│   Community Nodes    │  │
│  │   Nodes      │    │   Algorithm  │    │   (with member_count)│  │
│  └──────────────┘    │   (via GDS)  │    └──────────────────────┘  │
│                      └──────────────┘              │                │
│                                                    ▼                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    LLM Summarization                          │  │
│  │  ┌─────────────────────────────────────────────────────────┐ │  │
│  │  │  Entity Text  ──▶  Pairwise Merge  ──▶  Community Name  │ │  │
│  │  │  (fallback)        (hierarchical)       (one-liner)     │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                    │                │
│                                                    ▼                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Search Indices                             │  │
│  │  • Fulltext index on community names (BM25)                  │  │
│  │  • Vector index on name_embedding (cosine similarity)        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Scripts

### Primary Script: `scripts/build_communities_gds.py`

Uses Neo4j Graph Data Science (GDS) directly for efficient community detection on large graphs (22K+ entities).

```bash
# Full run: Leiden clustering + LLM summarization + embeddings
python scripts/build_communities_gds.py --summarize

# Add summaries to existing communities (skip clustering)
python scripts/build_communities_gds.py --summarize-only

# Control cost with limits
python scripts/build_communities_gds.py --summarize-only --max-summarize 10 --max-members 50

# Clustering only (no LLM calls)
python scripts/build_communities_gds.py --min-size 5
```

### Legacy Script: `scripts/build_communities.py`

Uses Graphiti's built-in `build_communities()` function. **Not recommended for large graphs** due to OOM bug (#992).

## Text Field Fallback System

### Problem

~46% of Entity nodes don't have a `summary` property. German Bundestag data (Drucksache, Vorgang, etc.) stores descriptive text in different properties.

### Solution

The summarization query uses a priority-based fallback system:

| Priority | Field | Source | Typical Length |
|----------|-------|--------|----------------|
| 1 | `summary` | Standard Graphiti Entity summary | Variable |
| 2 | `abstract` | Vorgang (legislative proceedings) | ~400 chars |
| 3 | `titel` | Drucksache (documents) | ~200 chars |
| 4 | `description` | Fraktion (political parties) | ~57 chars |
| 5 | `content` | Episodic (raw document text) | Truncated to 500 chars |
| 6 | `name` | Fallback for entities with long names | > 10 chars |

### Cypher Query

```cypher
MATCH (c:Community {uuid: $uuid})<-[:MEMBER_OF]-(e:Entity)
WITH e,
     CASE
         WHEN e.summary IS NOT NULL AND e.summary <> '' THEN e.summary
         WHEN e.abstract IS NOT NULL AND e.abstract <> '' THEN e.abstract
         WHEN e.titel IS NOT NULL AND e.titel <> '' THEN e.titel
         WHEN e.description IS NOT NULL AND e.description <> '' THEN e.description
         WHEN e.content IS NOT NULL AND e.content <> '' THEN left(e.content, 500)
         WHEN e.name IS NOT NULL AND size(e.name) > 10 THEN e.name
         ELSE NULL
     END as text_content
WHERE text_content IS NOT NULL
RETURN text_content as summary
LIMIT $max_members
```

## LLM Summarization Algorithm

Uses the same hierarchical pairwise summarization as Graphiti:

```
Input: [summary1, summary2, summary3, summary4, summary5]

Round 1: Pair and merge
  • merge(summary1, summary2) → merged_1
  • merge(summary3, summary4) → merged_2
  • summary5 (odd one out, kept for next round)

Round 2: Pair and merge
  • merge(merged_1, merged_2) → merged_3
  • merge(merged_3, summary5) → final_summary

Output: final_summary
```

### LLM Prompts

**Pairwise Merge:**
```
System: You are a helpful assistant that combines summaries.
        Always output in English, even if inputs contain German text.

User: Synthesize the information from the following two summaries into a single succinct summary.
      Output the summary in English, translating any German content.
      Summaries must be under 250 words.

      Summaries:
      [{"summary": "..."}, {"summary": "..."}]
```

**Community Name Generation:**
```
System: You are a helpful assistant that describes provided contents in a single sentence.
        Always output in English.

User: Create a short one sentence description in English that explains what kind of information is summarized.

      Summary: "..."
```

## Community Node Schema

```python
CommunityNode:
    uuid: str                    # Unique identifier
    communityId: int             # Leiden cluster ID
    name: str                    # LLM-generated one-liner description
    summary: str                 # Full merged summary from entity texts
    name_embedding: list[float]  # 1536-dim vector for semantic search
    member_count: int            # Number of member entities
    group_id: str                # Inherited from member entities
    created_at: datetime         # Creation timestamp
```

## Search Indices

### Fulltext Index (BM25)
```cypher
CREATE FULLTEXT INDEX community_name IF NOT EXISTS
FOR (c:Community) ON EACH [c.name]
```

### Vector Index (Cosine Similarity)
```cypher
CREATE VECTOR INDEX community_embedding IF NOT EXISTS
FOR (c:Community) ON (c.name_embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1536,
    `vector.similarity_function`: 'cosine'
}}
```

## Example Output

```
[12:00:11]    [1/3] Community 3141 (8073 members)
[12:00:11]       Found 30 text entries (1001 abstract, 7071 titel)
[12:00:11]       Estimated LLM calls: ~6
[12:00:11]       Generating summary...
[12:00:38]       Generating name...
[12:00:40]       Generating embedding...
[12:00:40]       ✓ Germany's legislative priorities during the 21st period...
```

The source breakdown `(1001 abstract, 7071 titel)` shows:
- 1001 entities contributed via `abstract` field (Vorgang nodes)
- 7071 entities contributed via `titel` field (Drucksache nodes)

## Cost Estimation

For a graph with 54 communities:
- **LLM calls per community**: ~log2(max_members) pairwise + 1 naming ≈ 6-10 calls
- **Embedding calls**: 1 per community
- **Total for 54 communities**: ~540 LLM calls + 54 embedding calls

Use `--max-summarize` and `--max-members` flags to control costs.

## Integration with Chat Tools

The community search tools in `src/chat/tools/community.py` automatically use:
- `name` for fulltext search
- `summary` for display
- `name_embedding` for semantic similarity

Example query:
```cypher
CALL db.index.fulltext.queryNodes('community_name', 'policy')
YIELD node, score
RETURN node.name, node.summary, score
```

## Troubleshooting

### "No text content found" Warning

If a community shows this warning, its member entities lack all fallback text fields. Check:
```cypher
MATCH (c:Community {communityId: $id})<-[:MEMBER_OF]-(e:Entity)
RETURN
    sum(CASE WHEN e.summary IS NOT NULL THEN 1 ELSE 0 END) as has_summary,
    sum(CASE WHEN e.abstract IS NOT NULL THEN 1 ELSE 0 END) as has_abstract,
    sum(CASE WHEN e.titel IS NOT NULL THEN 1 ELSE 0 END) as has_titel
```

### Graphiti OOM Bug

If using Graphiti's `build_communities()` on large graphs (1000+ entities), you may encounter OOM errors. This is a known bug (#992). Use `build_communities_gds.py` instead.

### DateTime Parsing Errors

If you see `'str' object has no attribute 'to_native'`, ensure graphiti_patches are applied:
```python
from chat.utils.graphiti_patches import apply_graphiti_patches
apply_graphiti_patches()
```

## Bilingual Text Handling (English + German)

The PolicyTracker graph contains text in both English and German. Here's how each component handles this:

### Impact by Component

| Component | Impact | Handling |
|-----------|--------|----------|
| **Leiden Clustering** | ✅ None | Structure-based, language-agnostic |
| **LLM Summarization** | ✅ Handled | Prompts enforce English output |
| **Embeddings** | ⚠️ ~75% effective | Cross-lingual similarity works but is reduced |
| **Fulltext Search (BM25)** | ⚠️ Language-dependent | Works best with English queries |

### English Output Enforcement

LLM prompts are configured to always output in English, even when input text is German:

```python
# In summarize_pair()
"Always output in English, even if inputs contain German text."
"Output the summary in English, translating any German content."

# In generate_community_name()
"Always output in English."
"Create a short one sentence description in English..."
```

This ensures:
- Consistent language across all community names and summaries
- Better search quality (queries match results in same language)
- Improved embedding similarity (same-language matching)

### Cross-Lingual Search Considerations

When searching:
- **English queries** work well against English community names
- **German entity names** (e.g., "Klimapolitik") may not match English community names
- **Vector search** partially bridges the language gap (~75% effectiveness)
- **Hybrid search** (BM25 + vector) provides best coverage

### Future Enhancements (Optional)

For improved bilingual search, consider:
1. **Bilingual names**: Store both `name_en` and `name_de` on Community nodes
2. **Language-specific indices**: Create German and English fulltext indices
3. **Language detection**: Add `dominant_language` property to Community nodes

```cypher
-- Optional: Language-specific fulltext indices
CREATE FULLTEXT INDEX community_name_de IF NOT EXISTS
FOR (c:Community) ON EACH [c.name_de]
OPTIONS {indexConfig: {`fulltext.analyzer`: 'german'}}

CREATE FULLTEXT INDEX community_name_en IF NOT EXISTS
FOR (c:Community) ON EACH [c.name_en]
OPTIONS {indexConfig: {`fulltext.analyzer`: 'english'}}
```

## Related Files

- `scripts/build_communities_gds.py` - Main community generation script
- `scripts/build_communities.py` - Legacy Graphiti-based script
- `src/chat/tools/community.py` - Community search tools for chat
- `src/chat/utils/graphiti_patches.py` - Patches for Graphiti edge cases
- `.claude/graphiti-patterns.md` - General Graphiti patterns
