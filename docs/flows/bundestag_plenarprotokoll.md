# Flow 5d: Bundestag Plenarprotokoll (Plenary Protocol) Ingestion

## Overview

Flow 5d collects plenary session protocols from both the German Bundestag (Federal Parliament) and Bundesrat (Federal Council) via the DIP API. These protocols contain verbatim records of parliamentary debates, speeches, votes, and procedural actions.

### Purpose

- Ingest complete plenary session transcripts from Bundestag and Bundesrat
- Link protocols to electoral periods (Wahlperioden)
- Connect protocols to legislative procedures (Vorgänge) discussed in sessions
- Enable temporal tracking of parliamentary debates and decisions
- Support legislative history and political discourse analysis

### Key Features

- ✅ Collects both Bundestag (BT) and Bundesrat (BR) protocols
- ✅ Handles composite key format (sitzungsnummer + wahlperiode)
- ✅ Extracts session numbers from dokumentnummer field
- ✅ Creates relationships to Wahlperiode and Vorgang entities
- ✅ Supports date range filtering and pagination
- ✅ Optional full-text transcript extraction

## Architecture

```
DIP API → PlenarprotokollCollector → Entity Transformation → Neo4j
   ↓              ↓                           ↓
   │      Base Collector                Composite Key
   │      (API + Save)                  Handling
   │              ↓                           ↓
   │      Edge Creation              Relationship
   │                                   Matching
   └──────────────────────────────────────────┘
                    Neo4j Knowledge Graph
```

## Data Model

### Entity: Plenarprotokoll

**Node Label**: `Plenarprotokoll`

**Composite Key**:
- `sitzungsnummer` (int) + `wahlperiode` (int)
- Example: Session 214 in Period 20 → `sitzungsnummer=214, wahlperiode=20`

**Properties**:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `plenarprotokoll_name` | string | Protocol title | "Protokoll der 214. Sitzung des 20. Deutschen Bundestages" |
| `sitzungsnummer` | int | Session number within period | 214 |
| `wahlperiode` | int | Electoral period number | 20 |
| `datum` | string | Session date (ISO format) | "2025-03-18" |
| `herausgeber` | string | Publishing body (BT or BR) | "BT" (Bundestag) or "BR" (Bundesrat) |
| `pdf_url` | string | Link to PDF protocol | "https://dserver.bundestag.de/btp/20/20214.pdf" |
| `full_text` | string | Complete transcript (optional) | "Deutscher Bundestag - 214. Sitzung..." |
| `tagesordnungspunkte` | string | Agenda items (JSON) | "[{\"top_nummer\": \"1\", \"titel\": \"...\"}]" |
| `reden_anzahl` | int | Number of speeches | 45 |
| `fundstelle` | string | Reference citation | "BT-PlPr 20/214" |
| `aktualisiert` | string | Last update timestamp | "2025-10-31T08:04:42+01:00" |
| `vorgangsbezug_anzahl` | int | Number of linked procedures | 12 |
| `related_vorgang_ids` | string | Linked Vorgang IDs (JSON) | "[{\"id\": \"320785\", \"titel\": \"...\"}]" |
| `url` | string | API document number | "20/214" |

### Relationships

#### 1. IN_WAHLPERIODE (Plenarprotokoll → Wahlperiode)

Links each protocol to its electoral period.

**Direction**: `Plenarprotokoll -[IN_WAHLPERIODE]-> Wahlperiode`

**Properties**:
- `entity_type`: "Plenarprotokoll"
- `active_from`: Session date
- `active_until`: null (protocols are point-in-time)

**Example**:
```cypher
(:Plenarprotokoll {sitzungsnummer: 214, wahlperiode: 20})
  -[:IN_WAHLPERIODE {entity_type: "Plenarprotokoll", active_from: "2025-03-18"}]->
(:Wahlperiode {wahlperiode_nummer: 20})
```

**Query Example**:
```cypher
// Find all protocols in electoral period 20
MATCH (p:Plenarprotokoll)-[:IN_WAHLPERIODE]->(w:Wahlperiode {wahlperiode_nummer: 20})
RETURN p.sitzungsnummer, p.datum, p.herausgeber
ORDER BY p.sitzungsnummer DESC
```

#### 2. REFERENCES_VORGANG (Plenarprotokoll → Vorgang)

Links protocols to legislative procedures discussed in the session.

**Direction**: `Plenarprotokoll -[REFERENCES_VORGANG]-> Vorgang`

**Properties**:
- `reference_type`: "debated_in_plenum"
- `context`: Session description

**Cardinality**: One protocol can reference many Vorgänge (procedures)

**Example**:
```cypher
(:Plenarprotokoll {sitzungsnummer: 214, wahlperiode: 20})
  -[:REFERENCES_VORGANG {reference_type: "debated_in_plenum", context: "Discussed in plenary session 214"}]->
(:Vorgang {vorgang_id: "320785"})
```

**Query Example**:
```cypher
// Find all procedures discussed in a specific session
MATCH (p:Plenarprotokoll {sitzungsnummer: 214, wahlperiode: 20})
      -[:REFERENCES_VORGANG]->(v:Vorgang)
RETURN v.vorgang_name, v.vorgangstyp, v.beratungsstand

// Find which sessions discussed a specific procedure
MATCH (p:Plenarprotokoll)-[:REFERENCES_VORGANG]->(v:Vorgang {vorgang_id: "320785"})
RETURN p.sitzungsnummer, p.datum, p.herausgeber
ORDER BY p.datum
```

## Data Collection

### API Endpoint

```
GET https://search.dip.bundestag.de/api/v1/plenarprotokoll
```

### Key API Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `f.wahlperiode` | Electoral period | "20" |
| `f.herausgeber` | Publishing body | "BT" (Bundestag) or "BR" (Bundesrat) |
| `f.datum_von` | Start date | "2024-01-01" |
| `f.datum_bis` | End date | "2024-12-31" |

**Note**: The `f.herausgeber='BT'` filter does NOT completely exclude Bundesrat protocols. The API may still return some BR protocols mixed in. The collector filters them appropriately during entity creation.

### API Response Structure

```json
{
  "id": "5695",
  "dokumentart": "Plenarprotokoll",
  "dokumentnummer": "20/214",  // Format: wahlperiode/session
  "wahlperiode": 20,
  "herausgeber": "BT",
  "datum": "2025-03-18",
  "titel": "Protokoll der 214. Sitzung des 20. Deutschen Bundestages",
  "vorgangsbezug_anzahl": 12,
  "vorgangsbezug": [
    {
      "id": "320785",
      "titel": "Gesetz zur...",
      "vorgangstyp": "Gesetzgebung"
    }
  ],
  "fundstelle": {
    "pdf_url": "https://dserver.bundestag.de/btp/20/20214.pdf",
    "dokumentnummer": "20/214"
  },
  "aktualisiert": "2025-10-31T08:04:42+01:00"
}
```

### Important Implementation Details

#### 1. Session Number Extraction

The API does **NOT** return a `sitzungsnummer` field directly. Instead, it returns `dokumentnummer` which contains the session number.

**Format**: `wahlperiode/sitzungsnummer` (e.g., "20/214")

**Extraction Logic**:
```python
dokumentnummer = item.get("dokumentnummer", "")  # "20/214"

# Extract session number from format "20/214"
if '/' in dokumentnummer:
    sitzungsnummer = int(dokumentnummer.split('/')[-1])  # 214
else:
    sitzungsnummer = int(dokumentnummer)  # Handle plain numbers like "1052"
```

#### 2. Composite Key Handling

Unlike other entities (Person, Vorgang, Drucksache) which use single ID fields, Plenarprotokoll uses a **composite key**.

**Neo4j MERGE Query**:
```cypher
MERGE (n:Plenarprotokoll {sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode})
SET n += $properties
RETURN n
```

**Edge Matching**:
```python
# Edge from_id format: "sitzungsnummer_wahlperiode"
plenarprotokoll_id = f"{entity.sitzungsnummer}_{entity.wahlperiode}"  # "214_20"

# Special Cypher query for composite key matching
query = """
MATCH (a:Plenarprotokoll), (b)
WHERE a.sitzungsnummer = $sitzungsnummer AND a.wahlperiode = $wahlperiode
  AND (b.vorgang_id = $to_id OR b.id = $to_id OR b.name = $to_id)
MERGE (a)-[r:REFERENCES_VORGANG]->(b)
SET r += $properties
RETURN r
"""
```

#### 3. Type Conversion

**Critical**: Neo4j stores `sitzungsnummer` as **integer**, even though the schema defines it as string.

```python
# Convert to int for MERGE parameter
sitzungsnummer_int = int(sitzungsnummer)

# ALSO convert in entity_dict before SET operation
# Otherwise SET n += $properties will overwrite it back to string!
entity_dict['sitzungsnummer'] = sitzungsnummer_int
```

#### 4. Bundestag vs Bundesrat

**Bundestag (BT)**:
- Federal Parliament
- Document numbers: "20/214" (wahlperiode/session)
- Sessions numbered sequentially within Wahlperiode

**Bundesrat (BR)**:
- Federal Council (upper house)
- Document numbers: "1052" (continuous numbering)
- Sessions numbered continuously across all periods

**Filtering Strategy**:
```python
# API filter helps but doesn't guarantee exclusivity
filters = {
    "f.wahlperiode": wahlperiode,
    "f.herausgeber": "BT"  # Attempts to filter to Bundestag only
}

# Additional filtering during entity creation
herausgeber = item.get("herausgeber", "BT")
if herausgeber == "BR":
    continue  # Skip Bundesrat protocols if desired
```

## Usage Examples

### Example 1: Collect Recent Bundestag Protocols

```python
from src.flows.bundestag_plenarprotokoll.processor import process_plenarprotokoll_batch

inputs = {
    "wahlperioden": ["20"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "batch_size": 50,
    "max_protocols": 100,
    "fetch_full_text": False,
    "create_relationships": True
}

result = await process_plenarprotokoll_batch(inputs, tracer)
```

### Example 2: Collect Both Bundestag and Bundesrat

```python
# No herausgeber filter = collect both BT and BR
inputs = {
    "wahlperioden": ["20"],
    "max_protocols": 50,
    "fetch_full_text": False
}

result = await process_plenarprotokoll_batch(inputs, tracer)
# Will collect mixed Bundestag and Bundesrat protocols
```

### Example 3: Full-Text Extraction

```python
# Enable full-text transcript extraction (slower)
inputs = {
    "wahlperioden": ["20"],
    "max_protocols": 10,
    "fetch_full_text": True  # Extracts complete session transcripts
}

result = await process_plenarprotokoll_batch(inputs, tracer)
# Each protocol will have full_text property populated
```

### Example 4: Direct Collector Usage

```python
from src.flows.bundestag_ingestion.collectors.plenarprotokoll_collector import PlenarprotokollCollector
from src.flows.bundestag_common.api_client import BundestagAPIClient
from neo4j import GraphDatabase

api_client = BundestagAPIClient()
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))

collector = PlenarprotokollCollector(
    api_client=api_client,
    neo4j_driver=driver,
    neo4j_database="politicamonitoring.v2"
)

result = await collector.collect_and_transform({
    "filters": {
        "f.wahlperiode": "20",
        "f.datum_von": "2024-01-01"
    },
    "limit": 20,
    "fetch_full_text": False
})

print(f"Collected: {result['items_collected']} protocols")
print(f"Entities: {result['entities_created']}")
print(f"Edges: {result['edges_created']}")
```

## Cypher Query Examples

### Find Recent Sessions

```cypher
// Find most recent 10 Bundestag sessions
MATCH (p:Plenarprotokoll)
WHERE p.herausgeber = 'BT'
RETURN p.sitzungsnummer, p.datum, p.plenarprotokoll_name
ORDER BY p.datum DESC
LIMIT 10
```

### Find Sessions by Date Range

```cypher
// Find sessions between two dates
MATCH (p:Plenarprotokoll)
WHERE p.datum >= '2024-01-01' AND p.datum <= '2024-12-31'
  AND p.herausgeber = 'BT'
RETURN p.sitzungsnummer, p.datum, p.vorgangsbezug_anzahl
ORDER BY p.datum
```

### Find All Vorgänge Discussed in a Session

```cypher
// Find all procedures discussed in session 214
MATCH (p:Plenarprotokoll {sitzungsnummer: 214, wahlperiode: 20})
      -[r:REFERENCES_VORGANG]->(v:Vorgang)
RETURN v.vorgang_name, v.vorgangstyp, r.reference_type, r.context
```

### Find Sessions Where a Procedure Was Discussed

```cypher
// Track debate history of a specific procedure
MATCH (v:Vorgang {vorgang_id: "320785"})<-[:REFERENCES_VORGANG]-(p:Plenarprotokoll)
RETURN p.sitzungsnummer, p.datum, p.herausgeber
ORDER BY p.datum
```

### Count Protocols by Electoral Period

```cypher
// Count protocols per Wahlperiode
MATCH (p:Plenarprotokoll)-[:IN_WAHLPERIODE]->(w:Wahlperiode)
RETURN w.wahlperiode_nummer, p.herausgeber, count(p) as protocol_count
ORDER BY w.wahlperiode_nummer DESC, p.herausgeber
```

### Find Busy Legislative Days

```cypher
// Find days with most Vorgang references
MATCH (p:Plenarprotokoll)-[:REFERENCES_VORGANG]->(v:Vorgang)
RETURN p.datum, p.sitzungsnummer, count(v) as vorgange_count
ORDER BY vorgange_count DESC
LIMIT 10
```

## Performance Considerations

### Collection Speed

| Operation | Typical Duration | Notes |
|-----------|------------------|-------|
| API fetch (10 items) | 1-2 seconds | Depends on API response time |
| Entity transformation | <0.1 seconds | Fast in-memory operation |
| Neo4j save (10 entities + edges) | 0.5-1 second | Includes MERGE queries |
| Full-text fetch (per protocol) | 2-3 seconds | Fetches complete transcript |

**Recommendation**: For large collections, use `fetch_full_text=False` unless transcripts are needed.

### Memory Usage

| Dataset Size | Memory Usage | Notes |
|--------------|--------------|-------|
| 10 protocols (no text) | <10 MB | Minimal metadata |
| 10 protocols (with text) | 50-100 MB | Full transcripts are large |
| 100 protocols (no text) | <50 MB | Recommended batch size |
| 100 protocols (with text) | 500 MB - 1 GB | Process in smaller batches |

### Optimization Tips

1. **Disable full-text for metadata-only collection**:
   ```python
   inputs = {"fetch_full_text": False}  # Much faster
   ```

2. **Use date ranges to limit scope**:
   ```python
   inputs = {
       "start_date": "2024-01-01",
       "end_date": "2024-03-31"  # Q1 only
   }
   ```

3. **Process in batches**:
   ```python
   inputs = {
       "batch_size": 50,  # Neo4j batch size
       "max_protocols": 100  # Limit total collection
   }
   ```

4. **Separate metadata and full-text collection**:
   ```python
   # First pass: Collect metadata
   result1 = await process_plenarprotokoll_batch({
       "max_protocols": 1000,
       "fetch_full_text": False
   })

   # Second pass: Fetch full text for specific protocols
   # (Implement selective full-text fetching as needed)
   ```

## Troubleshooting

### Issue 1: No Nodes Created

**Symptoms**:
- Flow completes successfully
- Reports "X protocols collected"
- But `MATCH (p:Plenarprotokoll) RETURN count(p)` shows 0 nodes

**Common Causes**:
1. All collected protocols have empty `sitzungsnummer`
2. Type mismatch (string vs int) in MERGE query
3. Composite key not properly constructed

**Debug Steps**:
```bash
# Check debug log
cat /tmp/plenarprotokoll_save_debug.log

# Look for:
# - "SKIPPED: No sitzungsnummer"
# - "Cannot convert sitzungsnummer to int"
# - "Converted sitzungsnummer 'X' to int Y"
# - "✅ SAVED Plenarprotokoll sitzung=X, wp=Y"
```

**Solution**:
- Ensure `dokumentnummer` extraction is working
- Verify type conversion to int
- Check that both MERGE parameter AND entity_dict use int

### Issue 2: Fewer Nodes Than Expected

**Symptoms**:
- Requested 10 protocols
- Only 7 nodes created

**Cause**:
API returns mixed Bundestag (BT) and Bundesrat (BR) protocols even with `f.herausgeber='BT'` filter.

**Example**:
```
Requested: 10 protocols
Returned: 10 items (3 BR + 7 BT)
Filtered: 7 BT protocols → 7 nodes created
```

**Solution**:
Request higher limit to account for filtering:
```python
inputs = {
    "max_protocols": 15  # Request more to get 10 BT after filtering
}
```

Or disable filtering to collect both:
```python
# Collect both BT and BR protocols
# (Default behavior - no herausgeber filtering)
```

### Issue 3: No Relationships Created

**Symptoms**:
- Nodes created successfully
- But `MATCH (p:Plenarprotokoll)-[r]->() RETURN count(r)` shows 0 relationships

**Common Causes**:
1. Composite key format incorrect in edges
2. Wahlperiode or Vorgang nodes don't exist
3. Edge matching query failing

**Debug Steps**:
```cypher
// Check if Wahlperiode exists
MATCH (w:Wahlperiode {wahlperiode_nummer: 20})
RETURN w

// Check if Vorgang nodes exist
MATCH (v:Vorgang)
WHERE v.vorgang_id IN ["320785", "320784"]
RETURN v.vorgang_id, v.vorgang_name

// Check edge format in debug log
// Should see: from_id="214_20", to_id="20", type="IN_WAHLPERIODE"
```

**Solution**:
1. Ensure Wahlperiode nodes exist (run Flow 5g first)
2. Ensure Vorgang nodes exist (run Flow 5b first)
3. Verify edge `from_id` format: "sitzungsnummer_wahlperiode"

### Issue 4: Duplicate Nodes

**Symptoms**:
- Running flow multiple times creates duplicate protocols

**Cause**:
MERGE query not finding existing nodes due to key mismatch.

**Solution**:
```cypher
// Check for duplicates
MATCH (p:Plenarprotokoll)
WHERE p.sitzungsnummer = 214 AND p.wahlperiode = 20
RETURN p, count(*) as dup_count

// Remove duplicates (keep first)
MATCH (p:Plenarprotokoll)
WHERE p.sitzungsnummer = 214 AND p.wahlperiode = 20
WITH p.sitzungsnummer as sitz, p.wahlperiode as wp, collect(p) as nodes
WHERE size(nodes) > 1
FOREACH (n in tail(nodes) | DETACH DELETE n)
```

## Testing

### Unit Tests

```bash
# Test collector
pytest tests/unit/flows/bundestag_ingestion/test_plenarprotokoll_collector.py -v

# Test entity creation
pytest tests/unit/flows/bundestag_ingestion/test_plenarprotokoll_collector.py::test_create_entities_directly -v

# Test edge creation
pytest tests/unit/flows/bundestag_ingestion/test_plenarprotokoll_collector.py::test_transform_to_edges -v
```

### Integration Tests

```bash
# Test end-to-end flow
pytest tests/integration/flows/test_plenarprotokoll_flow.py -v

# Test with Neo4j
pytest tests/integration/flows/test_plenarprotokoll_flow.py::test_full_collection_with_neo4j -v
```

### Manual Testing

```python
# Test API connectivity
from src.flows.bundestag_common.api_client import BundestagAPIClient

api_client = BundestagAPIClient()
response = await api_client.get("plenarprotokoll", params={
    "f.wahlperiode": "20",
    "num": 1
})
print(f"API working: {response.get('numFound', 0)} protocols found")

# Test collector
from src.flows.bundestag_ingestion.collectors.plenarprotokoll_collector import PlenarprotokollCollector

collector = PlenarprotokollCollector(api_client=api_client)
result = await collector.collect_and_transform({
    "filters": {"f.wahlperiode": "20"},
    "limit": 5
})
print(f"Collector working: {result['items_collected']} collected, {result['entities_created']} created")
```

## Code References

### Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `src/flows/bundestag_plenarprotokoll/processor.py` | Flow orchestration | 23-217 (process_plenarprotokoll_batch) |
| `src/flows/bundestag_ingestion/collectors/plenarprotokoll_collector.py` | Data collection | 276-365 (_create_entities_directly)<br>367-424 (_transform_to_edges) |
| `src/flows/bundestag_ingestion/collectors/base_collector.py` | Neo4j save logic | 168-247 (Plenarprotokoll special handling)<br>303-366 (Edge creation) |
| `src/graphrag/political_schema_v4.py` | Entity schema | Plenarprotokoll class definition |

### Critical Code Sections

**Session Number Extraction** (plenarprotokoll_collector.py:302):
```python
# Use dokumentnummer as sitzungsnummer (API doesn't return sitzungsnummer field)
sitzungsnummer = item.get("dokumentnummer", "")
```

**Composite Key Handling** (base_collector.py:216-220):
```python
query = f"""
MERGE (n:Plenarprotokoll {{sitzungsnummer: $sitzungsnummer, wahlperiode: $wahlperiode}})
SET n += $properties
RETURN n
"""
```

**Type Conversion** (base_collector.py:203-213):
```python
if '/' in str(sitzungsnummer):
    sitzungsnummer_int = int(sitzungsnummer.split('/')[-1])
else:
    sitzungsnummer_int = int(sitzungsnummer)

# CRITICAL: Also convert in entity_dict
entity_dict['sitzungsnummer'] = sitzungsnummer_int
```

**Edge Creation** (plenarprotokoll_collector.py:383-410):
```python
plenarprotokoll_id = f"{entity.sitzungsnummer}_{entity.wahlperiode}"

wahlperiode_edge = {
    "type": "IN_WAHLPERIODE",
    "from_id": plenarprotokoll_id,
    "to_id": str(entity.wahlperiode),
    # ... properties
}
```

## Related Documentation

- [Bundestag Ingestion Overview](./bundestag_ingestion.md)
- [Political Schema v4](../schema/political_schema_v4.md)
- [Flow 5b: Vorgang Ingestion](./bundestag_vorgang.md)
- [Kodosumi Flow Patterns](../../.claude/kodosumi-patterns.md)

## Changelog

### Version 1.1.0 (2025-11-17)
- ✅ Fixed session number extraction from `dokumentnummer` field
- ✅ Added support for both Bundestag and Bundesrat protocols
- ✅ Implemented composite key handling for edges
- ✅ Fixed type conversion (string to int) for Neo4j compatibility
- ✅ Added relationship creation (IN_WAHLPERIODE, REFERENCES_VORGANG)

### Version 1.0.0 (2025-11-12)
- Initial implementation of Plenarprotokoll collector
- Basic entity creation and API integration
- Neo4j save functionality
