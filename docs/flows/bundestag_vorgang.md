# Flow 5b: Bundestag Vorgang Ingestion

## Overview

Flow 5b collects German Bundestag legislative procedures (Vorgänge) from the DIP API, including bills, motions, and parliamentary initiatives. Creates a comprehensive knowledge graph with relationships to Wahlperiode, Fraktion, Deskriptor (keywords), and Sachgebiet (subject areas).

### Purpose

- Ingest legislative procedures from the German Bundestag
- Track legislation lifecycle from initiation to completion
- Build semantic relationships via keywords (Deskriptoren)
- Enable policy analysis and monitoring
- Support temporal tracking of legislative processes

### Key Features

- **Comprehensive Vorgang Data**: All procedure types (Gesetzgebung, Antrag, EU-Vorlage, etc.)
- **Keyword Extraction**: Automatic extraction of Deskriptor entities for semantic search
- **Subject Classification**: Links to Sachgebiet for topical organization
- **Relationship Creation**: Automatic linking to Wahlperiode, Fraktion, and other entities
- **Flexible Filtering**: Filter by Wahlperiode, Vorgangstyp, and batch processing
- **SSL Handling**: Built-in certificate verification bypass for Bundestag API

## Architecture

```
Bundestag DIP API /vorgang endpoint
         ↓
   Cursor-based Pagination
         ↓
   Data Collection & Mapping
         ↓
   Entity Extraction:
   - Vorgang entities
   - Deskriptor entities (keywords)
   - Sachgebiet entities (subjects)
         ↓
   Neo4j MERGE Operations
         ↓
   Relationship Creation:
   - BELONGS_TO (Wahlperiode)
   - TAGGED_WITH (Deskriptor)
   - SUBJECT_AREA (Sachgebiet)
         ↓
   Knowledge Graph
```

## Data Model

### Primary Entity: `Vorgang`

**Unique Identifier**: `vorgang_id` (from DIP API)

**Core Fields**:
- `vorgang_id`: Unique identifier
- `titel`: Full title of the procedure
- `abstract`: Summary description
- `vorgangstyp`: Type (Gesetzgebung, Antrag, Kleine Anfrage, etc.)
- `beratungsstand`: Current status (In Beratung, Angenommen, Abgelehnt, Verkündet, etc.)
- `datum`: Start date
- `aktualisiert`: Last updated timestamp
- `wahlperiode`: Electoral period number

**Classification Fields**:
- `sachgebiet`: Subject areas (list) - e.g., ["Gesundheit", "Wirtschaft"]
- `initiative`: Initiating body (list) - Bundesregierung, Bundesrat, Bundestag, etc.
- `typ`: Entity type (always "Vorgang")

**Optional Fields**:
- `gesta`: GESTA identifier (legislative tracking number)
- `archiv`: Archive status

**Gesetzgebung-Specific Fields** (stored as JSON):
- `zustimmungsbeduerftigkeit`: Whether Bundesrat consent required
- `verkuendung`: Publication details
- `inkrafttreten`: Entry into force details

**Metadata Fields**:
- `deskriptor_json`: Keywords/descriptors (JSON) - for relationship creation

### Related Entity: `Deskriptor`

**Purpose**: Keywords/tags for semantic search and categorization

**Fields**:
- `deskriptor_id`: Composite ID (name + type)
- `name`: Keyword name
- `typ`: Type (Sachbegriffe, Personen, Orte, etc.)
- `fundstelle`: Whether it's a primary reference point

### Related Entity: `Sachgebiet`

**Purpose**: Subject area classification

**Fields**:
- `sachgebiet_name`: Subject name (e.g., "Gesundheit", "Wirtschaft")
- `name`: Display name

## API Integration

### Endpoint
```
GET https://search.dip.bundestag.de/api/v1/vorgang
```

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `f.wahlperiode` | integer | Filter by electoral period | `20` |
| `f.vorgangstyp` | string | Filter by procedure type | `"Gesetzgebung"` |
| `format` | string | Response format | `"json"` |
| `cursor` | string | Pagination cursor | Auto-managed |

### Vorgangstyp Options

- **Gesetzgebung**: Legislation (bills)
- **Antrag**: Motion
- **Kleine Anfrage**: Minor inquiry
- **Große Anfrage**: Major inquiry
- **EU-Vorlage**: EU proposal
- **Bericht**: Report
- **Unterrichtung**: Information
- **Alle**: All types

### SSL Configuration

```python
# Built-in SSL bypass for Bundestag API
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

## Usage

### Via Kodosumi Interface

1. **Access the Flow**:
   ```
   http://localhost:3370
   Login: admin/admin
   Navigate to: Bundestag Vorgang Ingestion
   ```

2. **Configure Parameters**:
   - **Job Name**: Descriptive name (e.g., "WP 20 Gesetzgebung")
   - **Wahlperiode**: Comma-separated periods (e.g., "19,20,21")
   - **Vorgangstyp**: Filter by type or "Alle" for all
   - **Batch Size**: Processing batch size (10-500)
   - **Maximum Vorgänge**: Limit total processing (100-10000)
   - **Create Relationships**: Enable/disable relationship creation

3. **Submit**: Click "Start Collection"

4. **Monitor Progress**: Real-time updates via Kodosumi tracer

### Programmatic Usage

```python
from src.flows.bundestag_vorgang.processor import process_vorgang_batch

inputs = {
    "wahlperioden": ["20"],
    "vorgangstyp": "Gesetzgebung",
    "batch_size": 100,
    "max_vorgaenge": 1000,
    "create_relationships": True
}

# Mock tracer for testing
class MockTracer:
    async def markdown(self, text):
        print(text)

result = await process_vorgang_batch(inputs, MockTracer())
```

### Example API Stats (WP 20)

Based on actual API data:
- **Total Vorgänge**: 37,666+ (all types)
- **Gesetzgebung**: 696 bills
- **Antrag**: ~5,000 motions
- **Kleine Anfrage**: ~10,000 minor inquiries
- **Related Vorgangsposition**: 676,000+ procedure steps
- **Related Drucksache**: 281,000+ documents

## Relationships

### Created Relationships

1. **Vorgang → Wahlperiode** (`BELONGS_TO`)
   ```cypher
   MATCH (v:Vorgang {wahlperiode: 20})
   MATCH (w:Wahlperiode {wahlperiode_nummer: 20})
   MERGE (v)-[:BELONGS_TO]->(w)
   ```

2. **Vorgang → Deskriptor** (`TAGGED_WITH`)
   ```cypher
   MATCH (v:Vorgang)
   UNWIND v.deskriptor_json as desk
   MATCH (d:Deskriptor {name: desk.name, typ: desk.typ})
   MERGE (v)-[r:TAGGED_WITH]->(d)
   SET r.fundstelle = desk.fundstelle
   ```
   **Note**: Requires APOC for JSON parsing

3. **Vorgang → Sachgebiet** (`SUBJECT_AREA`)
   ```cypher
   MATCH (v:Vorgang)
   UNWIND v.sachgebiet AS sg_name
   MATCH (s:Sachgebiet {sachgebiet_name: sg_name})
   MERGE (v)-[:SUBJECT_AREA]->(s)
   ```

## Field Mapping Logic

### Vorgang Entity Mapping

```python
def map_vorgang_to_entity(api_data: Dict) -> Dict:
    """
    Maps DIP API response to Neo4j entity structure.

    Handles:
    - String fields with safe_str()
    - List fields with safe_list()
    - Date fields with safe_date()
    - JSON serialization for complex nested objects
    """
```

### Deskriptor Extraction

```python
def extract_deskriptoren(api_data: Dict) -> List[Dict]:
    """
    Extracts keyword entities from vorgang data.

    Creates composite ID: "{name}_{type}"
    Example: "Digitalisierung_Sachbegriffe"
    """
```

### Sachgebiet Extraction

```python
def extract_sachgebiete(api_data: Dict) -> List[Dict]:
    """
    Extracts subject area entities from vorgang data.

    Deduplicates and normalizes subject names.
    """
```

## Configuration

### In config.yaml

```yaml
- name: flow5b-bundestag-vorgang
  route_prefix: /bundestag-vorgang
  import_path: src.flows.bundestag_vorgang.app:fast_app
  runtime_env:
    env_vars:
      NEO4J_URI: bolt://localhost:7687
      NEO4J_USERNAME: neo4j
      NEO4J_PASSWORD: password123
      NEO4J_DATABASE: politicamonitoring.v2
      BUNDESTAG_API_KEY: YOUR_API_KEY
      BUNDESTAG_API_URL: https://search.dip.bundestag.de/api/v1/
  ray_actor_options:
    num_cpus: 2
    memory: 4000000000  # 4GB
  autoscaling_config:
    min_replicas: 1
    max_replicas: 2
```

## Neo4j Schema

### Constraints

```cypher
CREATE CONSTRAINT vorgang_vorgang_id_unique IF NOT EXISTS
FOR (n:Vorgang)
REQUIRE n.vorgang_id IS UNIQUE

CREATE CONSTRAINT deskriptor_deskriptor_id_unique IF NOT EXISTS
FOR (n:Deskriptor)
REQUIRE n.deskriptor_id IS UNIQUE

CREATE CONSTRAINT sachgebiet_sachgebiet_name_unique IF NOT EXISTS
FOR (n:Sachgebiet)
REQUIRE n.sachgebiet_name IS UNIQUE
```

### Indexes

```cypher
-- Vorgang indexes
CREATE INDEX vorgang_vorgang_id_idx IF NOT EXISTS
FOR (n:Vorgang) ON (n.vorgang_id)

CREATE INDEX vorgang_wahlperiode_idx IF NOT EXISTS
FOR (n:Vorgang) ON (n.wahlperiode)

CREATE INDEX vorgang_vorgangstyp_idx IF NOT EXISTS
FOR (n:Vorgang) ON (n.vorgangstyp)

CREATE INDEX vorgang_beratungsstand_idx IF NOT EXISTS
FOR (n:Vorgang) ON (n.beratungsstand)

CREATE INDEX vorgang_datum_idx IF NOT EXISTS
FOR (n:Vorgang) ON (n.datum)

-- Deskriptor indexes
CREATE INDEX deskriptor_name_idx IF NOT EXISTS
FOR (n:Deskriptor) ON (n.name)

CREATE INDEX deskriptor_typ_idx IF NOT EXISTS
FOR (n:Deskriptor) ON (n.typ)

-- Sachgebiet indexes
CREATE INDEX sachgebiet_sachgebiet_name_idx IF NOT EXISTS
FOR (n:Sachgebiet) ON (n.sachgebiet_name)
```

## Query Examples

### Find all legislation in current period
```cypher
MATCH (v:Vorgang {vorgangstyp: "Gesetzgebung"})
WHERE v.wahlperiode = 20
RETURN v.titel, v.beratungsstand, v.datum
ORDER BY v.datum DESC
LIMIT 20
```

### Find legislation by keyword
```cypher
MATCH (v:Vorgang)-[:TAGGED_WITH]->(d:Deskriptor {name: "Digitalisierung"})
WHERE v.vorgangstyp = "Gesetzgebung"
RETURN v.titel, v.beratungsstand
```

### Find legislation by subject area
```cypher
MATCH (v:Vorgang)-[:SUBJECT_AREA]->(s:Sachgebiet {sachgebiet_name: "Gesundheit"})
WHERE v.wahlperiode = 20
RETURN v.titel, v.vorgangstyp, v.beratungsstand
ORDER BY v.datum DESC
```

### Find completed legislation
```cypher
MATCH (v:Vorgang {vorgangstyp: "Gesetzgebung"})
WHERE v.beratungsstand = "Verkündet"
  AND v.wahlperiode = 20
RETURN v.titel, v.datum
ORDER BY v.datum DESC
```

### Analyze legislation by initiator
```cypher
MATCH (v:Vorgang {vorgangstyp: "Gesetzgebung", wahlperiode: 20})
UNWIND v.initiative as init
RETURN init, count(*) as count
ORDER BY count DESC
```

### Find most common keywords
```cypher
MATCH (v:Vorgang)-[:TAGGED_WITH]->(d:Deskriptor)
WHERE v.wahlperiode = 20
RETURN d.name, d.typ, count(*) as usage_count
ORDER BY usage_count DESC
LIMIT 20
```

## Performance

### Typical Metrics

- **Collection Speed**: ~100-200 vorgänge/minute
- **Entity Creation**: ~2-3 seconds per batch of 100
- **Relationship Creation**: ~1-2 seconds per batch
- **Memory Usage**: ~1GB for 1000 vorgänge with relationships
- **API Response Time**: ~500ms-2s per request

### Optimization Tips

1. **Batch Size**: Use 100-200 for optimal throughput
2. **Disable Relationships**: Set `create_relationships: False` for faster collection
3. **Filter by Type**: Collect "Gesetzgebung" first (smaller dataset)
4. **Wahlperiode Focus**: Process one period at a time
5. **Pagination**: Uses cursor-based pagination automatically

## Troubleshooting

### Common Issues

#### 1. SSL Certificate Error
**Symptom**: `ClientConnectorCertificateError`

**Solution**: Already handled with SSL verification bypass:
```python
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

#### 2. Empty Results
**Symptom**: No vorgänge collected

**Solution**:
- Verify Wahlperiode is valid (19, 20, 21)
- Try `vorgangstyp="Alle"` first
- Check API key is valid
- Test with small `max_vorgaenge` value

#### 3. APOC Not Available for Relationships
**Symptom**: Deskriptor relationships not created

**Solution**:
```cypher
-- Install APOC plugin in Neo4j
-- Or manually parse JSON in Cypher
MATCH (v:Vorgang)
WHERE v.deskriptor_json IS NOT NULL
WITH v, apoc.convert.fromJsonList(v.deskriptor_json) as desks
UNWIND desks as desk
MATCH (d:Deskriptor {name: desk.name, typ: desk.typ})
MERGE (v)-[:TAGGED_WITH]->(d)
```

#### 4. Memory Issues
**Symptom**: Ray actor OOM errors

**Solution**:
- Reduce `batch_size` to 50
- Reduce `max_vorgaenge` per run
- Disable relationship creation initially
- Increase memory allocation in config.yaml

#### 5. Missing Prerequisites
**Symptom**: Relationship creation fails

**Solution**: Ensure these flows run first:
```bash
# 1. Create Wahlperiode nodes
python scripts/bundestag_wahlperiode_setup.py

# 2. Create Fraktion nodes (if needed)
python scripts/bundestag_fraktion_setup.py

# 3. Then run vorgang ingestion
```

## Processing Pipeline Details

### Stage 1: Data Collection
```python
# Cursor-based pagination
while cursor:
    documents, next_cursor = await fetch_vorgaenge_from_api(
        wahlperiode, vorgangstyp, cursor, batch_size
    )
    cursor = next_cursor
```

### Stage 2: Entity Mapping
```python
# Map each document to entity structure
for doc in documents:
    vorgang_entity = map_vorgang_to_entity(doc)
    deskriptoren = extract_deskriptoren(doc)
    sachgebiete = extract_sachgebiete(doc)
```

### Stage 3: Neo4j Upsert
```python
# MERGE-based upsert with deduplication
upsert_manager.upsert_entities_batch(
    entity_type="Vorgang",
    entities=vorgang_entities,
    batch_size=100
)
```

### Stage 4: Relationship Creation
```python
# Create relationships via Cypher queries
rel_count = await create_vorgang_relationships(
    driver, database, [v["vorgang_id"] for v in entities]
)
```

## Testing

### Unit Tests
```bash
pytest tests/unit/flows/bundestag_vorgang/ -v
```

### Integration Tests
```bash
pytest tests/integration/flows/test_bundestag_vorgang_flow.py -v
```

### Manual API Testing
```bash
# Test API connectivity
curl -H "Authorization: ApiKey YOUR_KEY" \
  "https://search.dip.bundestag.de/api/v1/vorgang?f.wahlperiode=20&num=1"

# Test with specific filters
curl -H "Authorization: ApiKey YOUR_KEY" \
  "https://search.dip.bundestag.de/api/v1/vorgang?f.wahlperiode=20&f.vorgangstyp=Gesetzgebung&num=10"
```

## Related Flows

- **Flow 5**: Bundestag Ingestion (main flow - comprehensive)
- **Flow 5a**: Bundestag Person (MPs - for INITIATES_VORGANG relationships)
- **Flow 5g**: Bundestag Wahlperiode (electoral periods - prerequisite)
- **Flow 5h**: Bundestag Fraktion (parliamentary groups - prerequisite)

## Prerequisites

Before running this flow:

1. **Neo4j Constraints**: Create via Flow 5 or manually
2. **Wahlperiode Nodes**: Run Flow 5g or script
3. **Optional - Fraktion Nodes**: Run Flow 5h for faction relationships
4. **APOC Plugin**: Required for Deskriptor relationships (optional)

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [Neo4j MERGE Documentation](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [APOC JSON Functions](https://neo4j.com/labs/apoc/4.4/overview/apoc.convert/)
- [Kodosumi Flow Patterns](../../.claude/kodosumi-patterns.md)

## Changelog

### Version 1.0.0 (2025-11-13)
- Initial implementation
- Cursor-based pagination for large datasets
- Deskriptor and Sachgebiet entity extraction
- MERGE-based deduplication
- SSL certificate handling
- Comprehensive relationship creation
- Kodosumi form with validation
- Comprehensive documentation
