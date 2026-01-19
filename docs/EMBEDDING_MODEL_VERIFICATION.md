# Embedding Model Verification Guide

This document explains how to verify which embedding model is being used for vector search operations in the PolicyTracker system.

## Quick Verification

Run the verification script:

```bash
just check-embedding-model
```

Or directly:

```bash
.venv/bin/python scripts/check_embedding_model.py
```

## Expected Output

All components should show ✅ and use **text-embedding-ada-002**:

```
✅ Episode Embedding Manager: text-embedding-ada-002
✅ Default Embedder Function: text-embedding-ada-002
✅ MCP Graph Retriever: text-embedding-ada-002
✅ Document Processor: Uses default (text-embedding-ada-002)
✅ Chat Server: Uses default (text-embedding-ada-002)
```

## Component Overview

### 1. Default Embedder Function
**File**: `src/flows/shared/apisix_llm_client.py:401`

```python
def create_apisix_graphiti_embedder(
    embedding_model: str = "text-embedding-ada-002",
):
```

This is the default embedder used by most components. Any component that calls `create_apisix_graphiti_embedder()` without specifying a model will use ada-002.

### 2. Episode Embedding Manager
**File**: `src/graphrag/episode_embedding_manager.py:23`

```python
EMBEDDING_MODEL = "text-embedding-ada-002"
```

Manages content embeddings for Episodic nodes in the knowledge graph.

### 3. MCP Graph Retriever
**File**: `src/mcp/graph_retrieval/retriever.py:871`

```python
self._embedder = create_apisix_graphiti_embedder(
    embedding_model="text-embedding-ada-002"
)
```

Handles vector search for user queries in the MCP (Model Context Protocol) interface.

### 4. Document Processor
**File**: `src/flows/data_ingestion/document_processor.py:154`

```python
embedder = create_apisix_graphiti_embedder()  # Uses default (ada-002)
```

Processes and embeds new documents during ingestion.

### 5. Chat Server
**File**: `src/chat/server/app.py:128`

```python
embedder = create_apisix_graphiti_embedder()  # Uses default (ada-002)
```

Handles embeddings for chat interactions.

## Why ada-002?

We switched from `text-embedding-3-small` to `text-embedding-ada-002` because:

- ✅ **100% cross-lingual similarity** (vs 13% with text-embedding-3-small)
- ✅ **Perfect multilingual support** for English-German query matching
- ✅ **Same 1536 dimensions** (fully compatible with existing infrastructure)
- ✅ **Better semantic understanding** for specialized legal/political terminology

## Verification in Production

### 1. Check Embedding Dimensions

All embeddings in Neo4j should have 1536 dimensions (ada-002 dimension):

```cypher
MATCH (e:Entity)
WHERE e.name_embedding IS NOT NULL
RETURN size(e.name_embedding) as dimension_count
LIMIT 1
```

Expected: `1536`

### 2. Check Migration Status

See how many entities/relationships have been migrated to ada-002:

```bash
just reembed-status
```

Expected output:
```
Entity Migration:
  Total: 31,129
  Migrated (ada-002): 25,308 (81.3%)
  Pending: 5,821 (18.7%)
```

### 3. Run Multilingual Tests

Verify ada-002 is working correctly for cross-lingual queries:

```bash
just verify-ada002
```

Expected: 100% test pass rate with 12/12 test cases passing.

### 4. Check New Embeddings

Verify that newly created entities use ada-002:

```cypher
MATCH (e:Entity)
WHERE e.embedding_migrated_at IS NOT NULL
  OR e.created_at > datetime('2026-01-19T00:00:00')
RETURN e.name, e.embedding_model
LIMIT 5
```

Expected: All should have `embedding_model = "text-embedding-ada-002"`

## Troubleshooting

### Problem: Component still using text-embedding-3-small

1. Check if the file was properly updated
2. Restart the application/service
3. Clear any caches
4. Run `just check-embedding-model` to verify

### Problem: Vector search returning poor results

1. Check if embeddings were re-embedded:
   ```bash
   just reembed-status
   ```

2. Verify cross-lingual similarity:
   ```bash
   just verify-ada002
   ```

3. If migration incomplete, continue re-embedding:
   ```bash
   just reembed-phase1  # Entities + Relationships
   just reembed-episodic  # Episodic nodes
   ```

### Problem: Mixed models (some ada-002, some 3-small)

This is expected during migration. The system is designed to be resume-safe:

- Old entities: text-embedding-3-small (no `embedding_model` marker)
- Migrated entities: text-embedding-ada-002 (with `embedding_model` marker)
- New entities: text-embedding-ada-002 (from new code)

Continue migration to completion:
```bash
just reembed-phase1
```

## Migration Timeline

1. **Entities**: 81.3% complete (25,308/31,129 migrated)
2. **Relationships**: ~2% complete (partial migration)
3. **Episodic**: 0% complete (ready to start)

## Related Commands

```bash
# Check embedding model configuration
just check-embedding-model

# Check migration status
just reembed-status
just reembed-status-detailed

# Verify ada-002 performance
just verify-ada002
just verify-ada002-quick

# Continue migration
just reembed-entities         # Finish entities
just reembed-relationships    # Finish relationships
just reembed-episodic        # Start episodic migration
just reembed-phase1          # Entities + Relationships together

# Backup before changes
just backup-embeddings
```

## References

- **Migration Plan**: [Plan file](/.claude/plans/optimized-wishing-lagoon.md)
- **ADA-002 Breakthrough**: [docs/ADA002_BREAKTHROUGH.md](ADA002_BREAKTHROUGH.md)
- **Implementation Script**: [scripts/re_embed_with_ada002.py](../scripts/re_embed_with_ada002.py)
- **Verification Script**: [scripts/verify_ada002_migration.py](../scripts/verify_ada002_migration.py)
- **Status Checker**: [scripts/check_migration_status.py](../scripts/check_migration_status.py)
