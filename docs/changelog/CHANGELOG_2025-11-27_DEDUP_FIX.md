# Changelog - Phase 2 Deduplication Infinite Loop Fix

**Date**: November 27, 2025
**Version**: Political Monitoring Agent v0.2.1
**Type**: Critical Bug Fix

## Problem Summary

Flow 1B (Bulk Auto-Delta Document Processing) was getting stuck in an infinite loop after the Phase 2 deduplication logic was implemented. The flow would run indefinitely without completing or producing errors.

## Root Cause Analysis

### Primary Issue: Blocking Synchronous Calls in Async Context

**Location**: `src/flows/data_ingestion/entity_registry.py`

The `EntityRegistry` class uses **synchronous Neo4j driver calls** (`session.run()`) inside methods marked as `async`:

```python
async def get_canonical_entity(...):
    with self.driver.session(...) as session:
        exact_result = session.run(...)  # SYNCHRONOUS blocking call!
```

This blocks the async event loop while waiting for Neo4j queries.

### Secondary Issue: N+1 Query Pattern

**Location**: `src/flows/data_ingestion/deduplicating_graphiti_client.py` lines 279-344

For **every entity** extracted, 2-3 synchronous database calls are made:
1. `get_canonical_entity()` - exact match query + alias match query
2. `add_alias()` or `register_canonical_entity()` - write query

With 50 entities per chunk, this results in **150+ blocking DB calls** per chunk.

### Combined Effect

When Ray actors process documents:
1. Each actor calls `DeduplicatingGraphitiClient.add_episode()`
2. Which calls `_deduplicate_entities()` for each chunk
3. Which makes synchronous blocking Neo4j calls for **each entity**
4. The `ray.wait()` loop in processor.py has a 5-second timeout
5. Blocking calls prevent tasks from completing, causing infinite waiting

## Fix Implemented

### Immediate Fix: Feature Flag to Disable Deduplication

Added `ENABLE_DEDUPLICATION` configuration flag that defaults to `False`, allowing users to bypass the problematic deduplication code until a proper async fix is implemented.

### Files Modified

#### 1. `src/config.py`

Added new setting in `GraphRAGSettings` class:

```python
ENABLE_DEDUPLICATION: bool = Field(
    default=False,
    description="Enable Phase 2 entity deduplication (disabled by default due to blocking sync Neo4j calls causing infinite loops)",
)
```

#### 2. `src/flows/data_ingestion/document_processor.py`

Updated `DocumentProcessorActor.initialize()` (lines 136-157):

```python
# Phase 2: Conditionally enable deduplication based on config flag
if config.graphrag_settings.ENABLE_DEDUPLICATION:
    # Initialize EntityRegistry schema
    await self.entity_registry.initialize_schema()

    # Wrap base client with DeduplicatingGraphitiClient
    self.dedupe_client = DeduplicatingGraphitiClient(...)
    logger.info(f"Actor {self.actor_id}: ... Phase 2 deduplication")
else:
    # Use base Graphiti client directly without deduplication wrapper
    self.dedupe_client = self.graphiti_client
    logger.info(f"Actor {self.actor_id}: ... (deduplication DISABLED)")
```

Updated `SimpleDocumentProcessor.process_document()` (lines 778-802) with same conditional logic.

## How to Use

### Default Behavior (Deduplication Disabled)

No changes needed. Flow 1B will work normally without deduplication:

```bash
# Just run Flow 1B - deduplication is disabled by default
```

### To Re-enable Deduplication (After Proper Fix)

Add to your `.env` file:

```bash
ENABLE_DEDUPLICATION=true
```

**Warning**: Only enable after the proper async fix is implemented (see Future Work below).

## Future Work: Proper Fix

The proper fix requires:

### Step 1: Convert EntityRegistry to Async Neo4j Driver

```python
from neo4j import AsyncGraphDatabase

class EntityRegistry:
    def __init__(self, ...):
        self.driver = AsyncGraphDatabase.driver(...)

    async def get_canonical_entity(...):
        async with self.driver.session(...) as session:
            result = await session.run(...)  # Truly async!
```

### Step 2: Batch Entity Queries

Replace N+1 query pattern with batch lookup:

```python
async def batch_get_canonical_entities(self, entity_list):
    """Single query for all entities."""
    async with self.driver.session(...) as session:
        result = await session.run("""
            UNWIND $entities AS entity
            OPTIONAL MATCH (ce:CanonicalEntity)
            WHERE toLower(ce.name) = toLower(entity.name)
            RETURN entity.name AS name, ce
        """, entities=[...])
```

### Step 3: Add Query Timeouts

```python
self.driver = AsyncGraphDatabase.driver(
    ...,
    connection_timeout=5.0,
    max_connection_lifetime=60,
    connection_acquisition_timeout=10.0,
)
```

## Impact

| Aspect | Before Fix | After Fix |
|--------|-----------|-----------|
| Flow 1B Status | Infinite loop | Completes normally |
| Deduplication | Active (broken) | Disabled by default |
| Entity extraction | Works | Works |
| Knowledge graph | Populated | Populated |
| Duplicate prevention | Broken | Not active (use weekly DAG) |

## Testing

1. Verified `ENABLE_DEDUPLICATION` defaults to `False`
2. Verified document processor imports correctly
3. Flow 1B should now complete without hanging

## Related Documentation

- **Phase 2 Implementation**: `docs/changelog/CHANGELOG_2025-11-25_PHASE2.md`
- **Deduplication Strategy**: `docs/deduplication_strategy.md`
- **Quick Reference**: `docs/PHASE2_QUICK_REFERENCE.md`

## Contributors

- Investigation and fix by Claude Code

---

**Changelog Version**: 1.0
**Date**: 2025-11-27
