# Flow 5a: Bundestag Person Ingestion

## Overview

Flow 5a collects comprehensive data about German Bundestag members (MdBs) from the DIP API and stores them in a Neo4j knowledge graph with deterministic field mapping and MERGE-based deduplication.

### Purpose

- Ingest biographical and political data for Bundestag members
- Build a knowledge graph of parliamentary representatives
- Track faction affiliations, committee memberships, and roles
- Support political network analysis and monitoring

### Key Features

- **Deterministic Field Mapping**: Consistent entity structure across all person records
- **MERGE-based Deduplication**: Automatic handling of duplicate entries using unique constraints
- **Relationship Creation**: Links to Wahlperiode, Fraktion, and other entities
- **Flexible Filtering**: Filter by Wahlperiode and date ranges
- **Batch Processing**: Efficient processing with configurable batch sizes

## Architecture

```
Bundestag DIP API /person endpoint
         ↓
   Data Collection
         ↓
   Field Extraction & Mapping
         ↓
   Neo4j MERGE Operations
         ↓
   Relationship Creation
         ↓
   Knowledge Graph (BundestagPerson nodes)
```

## Data Model

### Entity Type: `BundestagPerson`

**Unique Identifier**: `person_id` (from DIP API)

**Core Fields**:
- `person_id`: Unique identifier from DIP
- `person_name`: Full name
- `vorname`: First name
- `nachname`: Last name
- `namenszusatz`: Name suffix/title
- `geburtsdatum`: Date of birth
- `geburtsort`: Place of birth
- `geschlecht`: Gender

**Political Fields**:
- `fraktion`: Current parliamentary group (SPD, CDU/CSU, GRÜNE, FDP, AfD, DIE LINKE)
- `partei`: Political party
- `wahlperiode`: Current or most recent electoral period
- `wahlperioden`: List of all electoral periods served (JSON)
- `wahlkreis`: Electoral constituency
- `funktion`: Current role (e.g., MdB, Minister, etc.)

**Career Information**:
- `ausschuss_mitgliedschaften`: Committee memberships (JSON)
- `ressort`: Ministry assignments (for ministers)
- `akademische_titel`: Academic titles (Dr., Prof., etc.)
- `beruf`: Profession/occupation

**Metadata**:
- `typ`: Entity type (always "Person")
- `datum`: Snapshot date for temporal tracking
- `aktualisiert`: Last updated timestamp

## API Integration

### Endpoint
```
GET https://search.dip.bundestag.de/api/v1/person
```

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `f.wahlperiode` | string | Filter by electoral period | `"20"` or `"all"` |
| `f.datum.start` | string | Start date (ISO 8601) | `"2024-01-01"` |
| `f.datum.end` | string | End date (ISO 8601) | `"2024-12-31"` |
| `num` | integer | Results per page | `100` |
| `cursor` | string | Pagination cursor | Auto-managed |

### SSL Configuration

The flow includes SSL certificate verification bypass for the Bundestag API:
```python
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
   Navigate to: Bundestag Person Ingestion
   ```

2. **Configure Parameters**:
   - **Job Name**: Descriptive name for this ingestion run
   - **Wahlperiode**: Electoral period (19, 20, 21, or "all")
   - **Maximum Persons**: Limit number of persons to fetch (1-1000)
   - **Start Date**: Optional date filter (YYYY-MM-DD)
   - **End Date**: Optional date filter (YYYY-MM-DD)

3. **Submit**: Click "Start Collection"

4. **Monitor Progress**: Real-time updates via Kodosumi tracer

### Programmatic Usage

```python
from src.flows.bundestag_person.processor import process_bundestag_persons

inputs = {
    "job_name": "WP 20 Members",
    "wahlperiode": "20",
    "max_items": 100,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
}

# Mock tracer for testing
class MockTracer:
    async def markdown(self, text):
        print(text)

result = await process_bundestag_persons(inputs, MockTracer())
```

## Relationships

### Created Relationships

1. **Person → Wahlperiode** (`SERVED_IN`)
   - Links MPs to electoral periods they served
   - Created for each Wahlperiode in the person's `wahlperioden` list

2. **Person → Fraktion** (`MEMBER_OF`)
   - Links MPs to their parliamentary group
   - Based on current `fraktion` field

## Field Extraction Logic

The flow uses specialized field extractors from `bundestag_common/field_extractors.py`:

### Fraktion Extraction
```python
def extract_fraktion(api_data: Dict) -> str:
    """
    Extracts faction from various API field formats.

    Handles:
    - Direct string: "SPD"
    - Nested object: {"fraktion": "CDU/CSU"}
    - List: [{"fraktion": "GRÜNE"}]
    """
```

### Wahlperioden Extraction
```python
def extract_wahlperioden(api_data: Dict) -> List[str]:
    """
    Extracts list of electoral periods served.

    Returns: ["19", "20", "21"]
    """
```

### Safe Type Conversions
- `safe_str()`: Handles null values, lists, nested objects
- `safe_int()`: Converts to int with None fallback
- `safe_date()`: Extracts date from ISO strings or complex objects
- `safe_list()`: Ensures list output from various input types

## Configuration

### In config.yaml

```yaml
- name: flow5a-bundestag-person
  route_prefix: /bundestag-person
  import_path: src.flows.bundestag_person.app:fast_app
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
CREATE CONSTRAINT bundestagperson_person_id_unique IF NOT EXISTS
FOR (n:BundestagPerson)
REQUIRE n.person_id IS UNIQUE
```

### Indexes

```cypher
CREATE INDEX bundestagperson_person_name_idx IF NOT EXISTS
FOR (n:BundestagPerson)
ON (n.person_name)

CREATE INDEX bundestagperson_fraktion_idx IF NOT EXISTS
FOR (n:BundestagPerson)
ON (n.fraktion)

CREATE INDEX bundestagperson_funktion_idx IF NOT EXISTS
FOR (n:BundestagPerson)
ON (n.funktion)
```

## Query Examples

### Find all SPD members in Wahlperiode 20
```cypher
MATCH (p:BundestagPerson {fraktion: "SPD"})
WHERE "20" IN p.wahlperioden
RETURN p.person_name, p.funktion, p.wahlkreis
ORDER BY p.person_name
```

### Find ministers in current government
```cypher
MATCH (p:BundestagPerson)
WHERE p.ressort IS NOT NULL
RETURN p.person_name, p.ressort, p.partei
ORDER BY p.ressort
```

### Find members who served multiple periods
```cypher
MATCH (p:BundestagPerson)
WHERE size(p.wahlperioden) > 1
RETURN p.person_name, p.wahlperioden, size(p.wahlperioden) as periods_served
ORDER BY periods_served DESC
LIMIT 20
```

### Find committee chairs (if data available)
```cypher
MATCH (p:BundestagPerson)
WHERE p.ausschuss_mitgliedschaften CONTAINS 'Vorsitz'
RETURN p.person_name, p.ausschuss_mitgliedschaften
```

## Performance

### Typical Metrics

- **Collection Speed**: ~50-100 persons/minute
- **Entity Creation**: ~1-2 seconds per batch of 100
- **Relationship Creation**: ~0.5 seconds per batch
- **Memory Usage**: ~500MB for 1000 persons

### Optimization Tips

1. **Batch Size**: Use larger batches (100-200) for better throughput
2. **Wahlperiode Filter**: Filter to specific periods to reduce data volume
3. **Parallel Processing**: Multiple flows can run concurrently
4. **Neo4j Indexes**: Ensure indexes are created before large ingestion

## Troubleshooting

### Common Issues

#### 1. SSL Certificate Error
**Symptom**: `SSLCertVerificationError`

**Solution**: Already handled in the flow with SSL verification disabled for the Bundestag API.

#### 2. Empty Results
**Symptom**: No persons collected

**Solution**:
- Verify Wahlperiode number is valid (19, 20, 21)
- Check date range parameters
- Test with `wahlperiode="all"` first

#### 3. Duplicate Entities
**Symptom**: Same person created multiple times

**Solution**: Ensure Neo4j constraint exists:
```bash
# Check constraints
docker exec -it neo4j cypher-shell -u neo4j -p password123 \
  "SHOW CONSTRAINTS"
```

#### 4. Missing Relationships
**Symptom**: Persons not linked to Wahlperiode/Fraktion

**Solution**:
- Ensure Wahlperiode nodes exist first (run Flow 5g)
- Ensure Fraktion nodes exist (run Flow 5h)
- Check relationship creation logs

## Testing

### Unit Tests
```bash
pytest tests/unit/flows/bundestag_person/ -v
```

### Integration Tests
```bash
pytest tests/integration/flows/test_bundestag_person_flow.py -v
```

### Manual Testing
```bash
# Test API connectivity
curl -H "Authorization: ApiKey YOUR_KEY" \
  "https://search.dip.bundestag.de/api/v1/person?f.wahlperiode=20&num=1"

# Test field extractors
python -c "
from src.flows.bundestag_common.field_extractors import extract_fraktion
test_data = {'fraktion': 'SPD'}
print(extract_fraktion(test_data))
"
```

## Related Flows

- **Flow 5**: Bundestag Ingestion (main flow)
- **Flow 5b**: Bundestag Vorgang (legislative procedures)
- **Flow 5g**: Bundestag Wahlperiode (electoral periods - prerequisite)
- **Flow 5h**: Bundestag Fraktion (parliamentary groups - prerequisite)

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [Neo4j MERGE Documentation](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [Kodosumi Flow Patterns](../../.claude/kodosumi-patterns.md)

## Changelog

### Version 1.0.0 (2025-11-13)
- Initial implementation
- Deterministic field mapping
- MERGE-based deduplication
- SSL certificate handling
- Comprehensive documentation
