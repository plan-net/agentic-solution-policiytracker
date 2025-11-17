# Plenarprotokoll Flow: Critical Fixes Documentation

## Summary

This document details the critical fixes applied to Flow 5d (Bundestag Plenarprotokoll Ingestion) to enable proper data collection, entity creation, and relationship building in the Neo4j knowledge graph.

## Problem Statement

**Initial Issue**: Flow 5d was collecting Plenarprotokoll data from the DIP API successfully (showing 10 items collected with 100% success rate), but **no nodes or relationships were being created in Neo4j**.

## Root Causes Identified

Through systematic debugging, we identified **7 layers of issues** that needed to be resolved:

### 1. Missing save_to_neo4j() Call
**Problem**: The collector was transforming entities but never saving them to Neo4j.

**Location**: `src/flows/bundestag_ingestion/collectors/plenarprotokoll_collector.py:117`

**Fix**:
```python
# Added call to save entities and edges
save_result = await self.save_to_neo4j(entities, edges)
```

### 2. Missing Composite Key Handling
**Problem**: Base collector only handled single ID fields (person_id, vorgang_id, etc.) but Plenarprotokoll uses composite key (sitzungsnummer + wahlperiode).

**Location**: `src/flows/bundestag_ingestion/collectors/base_collector.py:168-247`

**Fix**:
```python
# Special handling for Plenarprotokoll (uses composite key)
if entity_type == 'Plenarprotokoll':
    sitzungsnummer = entity_dict.get('sitzungsnummer')
    wahlperiode = entity_dict.get('wahlperiode')

    query = f"""
    MERGE (n:{entity_type} {{sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode}})
    SET n += $properties
    RETURN n
    """
```

### 3. Type Mismatch (String vs Integer)
**Problem**: Schema defines `sitzungsnummer` as string, but existing Neo4j nodes used integer. MERGE queries failed because "214" (string) didn't match 214 (integer).

**Location**: `src/flows/bundestag_ingestion/collectors/base_collector.py:200-221`

**Fix**:
```python
# Convert sitzungsnummer to int for MERGE parameter
sitzungsnummer_int = int(sitzungsnummer)

# CRITICAL: Also convert in entity_dict before SET
# Otherwise SET n += $properties will overwrite it back to string!
entity_dict['sitzungsnummer'] = sitzungsnummer_int
```

### 4. Wrong Field Name
**Problem**: The API **doesn't return a `sitzungsnummer` field** at all. It returns `dokumentnummer` which contains the session number.

**API Response Format**:
```json
{
  "dokumentnummer": "20/214",  // Format: wahlperiode/session
  // NO sitzungsnummer field!
}
```

**Location**: `src/flows/bundestag_ingestion/collectors/plenarprotokoll_collector.py:302`

**Fix**:
```python
# Use dokumentnummer as sitzungsnummer (API doesn't return sitzungsnummer field)
sitzungsnummer = item.get("dokumentnummer", "")
```

### 5. Session Number Format Handling
**Problem**: The `dokumentnummer` field contains values like "20/214" (wahlperiode/session), not just "214". Direct int conversion failed.

**Location**: `src/flows/bundestag_ingestion/collectors/base_collector.py:204-206`

**Fix**:
```python
# Handle format "20/214" by extracting the session number after the slash
if '/' in str(sitzungsnummer):
    # Extract session number from "20/214" format
    sitzungsnummer_int = int(sitzungsnummer.split('/')[-1])  # Gets "214"
else:
    sitzungsnummer_int = int(sitzungsnummer)  # Handle plain numbers like "1052"
```

### 6. Bundesrat vs Bundestag Filtering
**Problem**: API filter `f.herausgeber='BT'` doesn't completely exclude Bundesrat protocols. Mixed results returned.

**Example**:
```
Requested: 10 protocols with f.herausgeber='BT'
Returned: 7 BT + 3 BR protocols
Result: Only 7 nodes created (3 filtered out)
```

**Initial Solution**: Filter out BR protocols in entity creation

**Final Solution**: Support **both** Bundestag and Bundesrat protocols

**Location**:
- `src/flows/bundestag_ingestion/collectors/plenarprotokoll_collector.py:309-329`
- `src/flows/bundestag_plenarprotokoll/processor.py:108-111`

**Fix**:
```python
# Removed BR filtering to collect both types
filters = {
    "f.wahlperiode": wahlperiode
    # Note: No herausgeber filter - collect both Bundestag (BT) and Bundesrat (BR)
}
```

### 7. Missing Relationship Creation
**Problem**: Edges were being created as Pydantic objects without `from_id` and `to_id` fields. The base_collector's edge saving logic couldn't match nodes.

**Location**: `src/flows/bundestag_ingestion/collectors/plenarprotokoll_collector.py:378-424`

**Fix**:
```python
# Create edges with explicit from_id and to_id
plenarprotokoll_id = f"{entity.sitzungsnummer}_{entity.wahlperiode}"  # Composite key format

# IN_WAHLPERIODE edge
wahlperiode_edge = {
    "type": "IN_WAHLPERIODE",
    "from_id": plenarprotokoll_id,  # "214_20"
    "to_id": str(entity.wahlperiode),  # "20"
    "entity_type": "Plenarprotokoll",
    "active_from": item.get("datum"),
    "active_until": None
}

# REFERENCES_VORGANG edges
for vorgang_ref in item.get("vorgangsbezug", []):
    vorgang_id = vorgang_ref.get("id")
    if vorgang_id:
        vorgang_edge = {
            "type": "REFERENCES_VORGANG",
            "from_id": plenarprotokoll_id,
            "to_id": vorgang_id,
            "reference_type": "debated_in_plenum",
            "context": f"Discussed in plenary session {entity.sitzungsnummer}"
        }
        edges.append(vorgang_edge)
```

**Edge Matching Logic**:

**Location**: `src/flows/bundestag_ingestion/collectors/base_collector.py:323-349`

**Fix**:
```python
# Special handling for Plenarprotokoll edges (composite key: sitzungsnummer_wahlperiode)
if '_' in str(from_id) and from_id.replace('_', '').replace('/', '').isdigit():
    # Parse composite key format: "214_20" or "20/214_20"
    parts = str(from_id).rsplit('_', 1)
    if len(parts) == 2:
        sitzung_raw = parts[0]
        wahlperiode = parts[1]

        # Extract session number from "20/214" format if needed
        if '/' in sitzung_raw:
            sitzungsnummer = int(sitzung_raw.split('/')[-1])
        else:
            sitzungsnummer = int(sitzung_raw)

        query = f"""
        MATCH (a:Plenarprotokoll), (b)
        WHERE a.sitzungsnummer = $sitzungsnummer AND a.wahlperiode = $wahlperiode
          AND (b.vorgang_id = $to_id OR b.id = $to_id OR b.name = $to_id)
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $properties
        RETURN r
        """
```

## Testing the Fixes

### Before Fixes
```cypher
// No nodes
MATCH (p:Plenarprotokoll) RETURN count(p)
// Result: 0

// No relationships
MATCH (p:Plenarprotokoll)-[r]->() RETURN count(r)
// Result: 0
```

### After Fixes
```cypher
// Nodes created successfully
MATCH (p:Plenarprotokoll) WHERE p.herausgeber = 'BT'
RETURN p.sitzungsnummer, p.wahlperiode, p.datum
ORDER BY p.sitzungsnummer DESC
// Result: 7 Bundestag protocols (sessions 208-214)

// Relationships created
MATCH (p:Plenarprotokoll)-[r]->()
RETURN type(r), count(r)
// Result:
// IN_WAHLPERIODE: 7 edges
// REFERENCES_VORGANG: 38 edges (multiple Vorgänge per protocol)
```

## Key Learnings

### 1. API Field Mapping
**Lesson**: Never assume API field names match your schema field names.

**Solution**: Always inspect actual API responses and map fields explicitly.

```python
# Debug: Log actual API response structure
with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
    f.write(f"Sample item keys: {list(items[0].keys())}\n")
    f.write(f"Sample item: {items[0]}\n")
```

### 2. Type Consistency
**Lesson**: Neo4j MERGE is type-sensitive. String "214" ≠ Integer 214.

**Solution**: Establish and enforce a consistent type convention. Convert early and maintain throughout.

```python
# Convert once at extraction
sitzungsnummer_int = int(dokumentnummer.split('/')[-1])

# Use everywhere (MERGE parameter AND entity properties)
entity_dict['sitzungsnummer'] = sitzungsnummer_int
```

### 3. Composite Keys
**Lesson**: Entities with composite keys need special handling in both entity creation and edge matching.

**Solution**:
- Use composite key in MERGE query
- Use formatted composite key for edge references
- Implement special matching logic in base_collector

```python
# Entity MERGE
MERGE (n:Plenarprotokoll {sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode})

# Edge reference
from_id = f"{sitzungsnummer}_{wahlperiode}"  # "214_20"

# Edge matching
WHERE a.sitzungsnummer = $sitzungsnummer AND a.wahlperiode = $wahlperiode
```

### 4. Edge Creation
**Lesson**: Pydantic edge models without node references are useless. Edges need explicit source and target node identifiers.

**Solution**: Always include `from_id` and `to_id` fields in edge dictionaries.

```python
edge = {
    "type": "REFERENCES_VORGANG",
    "from_id": plenarprotokoll_id,  # REQUIRED
    "to_id": vorgang_id,             # REQUIRED
    # ... properties
}
```

### 5. Debug Logging
**Lesson**: Silent failures are the worst. Add debug logging at critical points.

**Solution**: Implement debug file logging to track execution flow.

```python
with open("/tmp/plenarprotokoll_save_debug.log", "a") as f:
    f.write(f"✅ SAVED Plenarprotokoll sitzung={sitzungsnummer}, wp={wahlperiode}\n")
```

## Files Modified

### Primary Changes

1. **`src/flows/bundestag_ingestion/collectors/plenarprotokoll_collector.py`**
   - Added save_to_neo4j() call
   - Changed field extraction from `sitzungsnummer` to `dokumentnummer`
   - Removed Bundesrat filtering
   - Updated edge creation with from_id/to_id

2. **`src/flows/bundestag_ingestion/collectors/base_collector.py`**
   - Added Plenarprotokoll composite key handling in save logic
   - Added session number format parsing ("20/214" → 214)
   - Added type conversion (string → int)
   - Added special edge matching for composite keys

3. **`src/flows/bundestag_plenarprotokoll/processor.py`**
   - Removed `f.herausgeber='BT'` filter to support both BT and BR

### Documentation Created

1. **`docs/flows/bundestag_plenarprotokoll.md`**
   - Comprehensive flow documentation
   - API field mapping details
   - Entity and relationship schema
   - Cypher query examples
   - Troubleshooting guide

2. **`docs/flows/bundestag_ingestion.md`** (Updated)
   - Added Plenarprotokoll relationship details
   - Added link to detailed documentation

3. **`docs/flows/PLENARPROTOKOLL_FIXES.md`** (This document)
   - Complete fix history and rationale

## Verification Checklist

After deploying fixes, verify:

- [ ] Nodes are created: `MATCH (p:Plenarprotokoll) RETURN count(p)`
- [ ] Composite keys work: `MATCH (p:Plenarprotokoll {sitzungsnummer: 214, wahlperiode: 20}) RETURN p`
- [ ] Types are correct: `MATCH (p:Plenarprotokoll) RETURN p.sitzungsnummer LIMIT 1` (should be integer)
- [ ] Both BT and BR: `MATCH (p:Plenarprotokoll) RETURN p.herausgeber, count(*)`
- [ ] IN_WAHLPERIODE edges: `MATCH (p:Plenarprotokoll)-[r:IN_WAHLPERIODE]->() RETURN count(r)`
- [ ] REFERENCES_VORGANG edges: `MATCH (p:Plenarprotokoll)-[r:REFERENCES_VORGANG]->() RETURN count(r)`
- [ ] Edge properties: `MATCH (p:Plenarprotokoll)-[r:REFERENCES_VORGANG]->() RETURN r LIMIT 1`

## Related Issues

- [Flow 5d Initial Implementation](../FLOW_5D_IMPLEMENTATION.md) (if exists)
- [Neo4j Schema Design](../schema-er-diagram.md)
- [Composite Key Handling Best Practices](../../.claude/etl-patterns.md)

## Future Improvements

1. **Full-text extraction optimization**: Currently slow, could be parallelized
2. **Agenda item parsing**: `tagesordnungspunkte` could be expanded into separate entities
3. **Speech extraction**: Individual speeches could be extracted as separate nodes
4. **Vote tracking**: Link protocols to voting results
5. **Speaker tracking**: Link protocols to Person entities for speakers

## Contact

For questions about these fixes, refer to:
- Git commit history around 2025-11-17
- Debug logs at `/tmp/plenarprotokoll_save_debug.log`
- This documentation and related docs in `docs/flows/`
