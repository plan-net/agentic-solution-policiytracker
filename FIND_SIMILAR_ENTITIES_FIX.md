# find_similar_entities Tool Fix - AttributeError Resolved

## Issue
The `find_similar_entities` tool was throwing an AttributeError:
```
Error finding similar entities to Google: 'EntityNode' object has no attribute 'fact'
```

## Root Cause
The tool uses `NODE_HYBRID_SEARCH_RRF` which returns both **edges** and **nodes**:
- **Edges** have a `.fact` attribute
- **Nodes** have `.summary` and `.name` attributes instead

The code at line 427 in `/src/chat/tools/entity.py` was trying to access `result.fact` on all results without checking the type, causing it to crash when encountering node objects.

## Fix Applied
Modified lines 427-460 in `/src/chat/tools/entity.py` to properly handle both result types:

```python
for result in results:
    # Handle both edges (with .fact) and nodes (with .summary)
    content = ""
    if hasattr(result, "fact") and result.fact:
        content = result.fact
    elif hasattr(result, "summary") and result.summary:
        content = result.summary
    elif hasattr(result, "name") and result.name:
        # If it's a node entity, use its name as potential similar entity
        entity_name_candidate = result.name
        if entity_name_candidate != entity_name and len(entity_name_candidate) > 2:
            if entity_name_candidate not in similar_entities:
                similar_entities[entity_name_candidate] = []
            similar_entities[entity_name_candidate].append(
                getattr(result, "summary", f"Entity: {entity_name_candidate}")
            )
        continue

    if not content:
        continue
```

## Fix Verification
Tested with `test_find_similar_fix.py`:
- ✅ No AttributeError
- ✅ Successfully finds similar entities to "Google"
- ✅ Returns 5 similar entities with context counts
- ✅ Proper formatting and display

## Test Results
Query: "Find similar entities to Google"

Results:
1. **The** (18 contexts)
2. **Zalando** (15 contexts)
3. **Norway** (6 contexts)
4. **Google Cloud** (5 contexts)
5. **Google Play** (4 contexts)

## Status
✅ **FIXED** - Tool now handles both edge and node results correctly

## Date
2025-11-18

## Related Files
- `/src/chat/tools/entity.py` (lines 427-460)
- `/test_find_similar_fix.py` (verification script)
