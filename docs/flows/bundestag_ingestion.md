// Flow 5: German Bundestag Parliamentary Data Ingestion

## Overview

Flow 5 provides comprehensive German parliamentary data ingestion from the Bundestag Document and Information System (DIP) API. It collects, transforms, and loads 8 different types of parliamentary data into a knowledge graph structure for political analysis.

### Purpose

- Ingest German legislative procedures, documents, and parliamentary activities
- Build knowledge graph of Bundestag entities and relationships
- Enable temporal tracking of legislative processes
- Support political analysis and monitoring use cases

### Architecture

```
Bundestag DIP API → Collectors (8 types) → Transformers → Knowledge Graph
                         ↓
                   Entity Builder
                   Edge Builder
                         ↓
                   Kodosumi Interface → Neo4j
```

## Data Sources

### 1. Vorgang (Legislative Procedure)
- **Endpoint**: `/vorgang`
- **Entity Type**: `Vorgang`
- **Description**: Legislative procedures including bills, motions, and parliamentary initiatives
- **Key Fields**:
  - `vorgangstyp`: Procedure type (Gesetzgebung, Antrag, etc.)
  - `beratungsstand`: Current status (In Beratung, Abgeschlossen, etc.)
  - `wahlperiode`: Electoral period number
  - `initiative`: Initiating body (Bundesregierung, Bundesrat, Bundestag, etc.)
  - `sachgebiet`: Subject area (Gesundheit, Wirtschaft, Umwelt, etc.)

### 2. Drucksache (Parliamentary Document)
- **Endpoint**: `/drucksache`
- **Entity Type**: `Drucksache`
- **Description**: Official parliamentary documents including bills, reports, and motions
- **Key Fields**:
  - `dokumentart`: Document type (Gesetzentwurf, Antrag, Beschlussempfehlung, etc.)
  - `dokumentnummer`: Document number (format: wahlperiode/nummer)
  - `autoren`: Document authors
  - `pdf_url`: Link to PDF document

### 3. Person (Member of Parliament)
- **Endpoint**: `/person`
- **Entity Type**: `BundestagPerson`
- **Description**: Members of the Bundestag with biographical and political information
- **Key Fields**:
  - `fraktion`: Parliamentary group affiliation
  - `partei`: Political party
  - `wahlperioden`: List of electoral periods served
  - `wahlkreis`: Electoral constituency
  - `ausschuss_mitgliedschaften`: Committee memberships

### 4. Plenarprotokoll (Plenary Protocol)
- **Endpoint**: `/plenarprotokoll`
- **Entity Type**: `Plenarprotokoll`
- **Description**: Verbatim records of plenary sessions from Bundestag and Bundesrat
- **Composite Key**: `sitzungsnummer` + `wahlperiode`
- **Key Fields**:
  - `sitzungsnummer`: Session number (extracted from dokumentnummer)
  - `wahlperiode`: Electoral period number
  - `herausgeber`: Publishing body (BT=Bundestag, BR=Bundesrat)
  - `tagesordnungspunkte`: Agenda items (JSON)
  - `vorgangsbezug`: Linked procedures
  - `pdf_url`: Protocol document link
- **Detailed Documentation**: [Flow 5d: Plenarprotokoll](./bundestag_plenarprotokoll.md)

### 5. Vorgangsposition (Procedure Position/Step)
- **Endpoint**: `/vorgangsposition`
- **Entity Type**: `Vorgangsposition`
- **Description**: Individual steps in a legislative procedure
- **Key Fields**:
  - `vorgangsposition_name`: Step name (Erste Beratung, Zweite Beratung, etc.)
  - `sequenz`: Order in procedure
  - `datum`: Date of step
  - `fundstelle`: Reference to protocol

### 6. Aktivitaet (Activity)
- **Endpoint**: `/aktivitaet`
- **Entity Type**: `Aktivitaet`
- **Description**: Parliamentary activities including votes, debates, and decisions
- **Key Fields**:
  - `typ`: Activity type (Abstimmung, Beratung, etc.)
  - `ergebnis`: Result (Angenommen, Abgelehnt, etc.)
  - `ja_stimmen`, `nein_stimmen`, `enthaltungen`: Vote counts

### 7. Wahlperiode (Electoral Period)
- **Endpoint**: Built from metadata
- **Entity Type**: `Wahlperiode`
- **Description**: Electoral periods of the Bundestag
- **Key Fields**:
  - `wahlperiode_nummer`: Period number (19, 20, 21, etc.)
  - `von`, `bis`: Start and end dates
  - `bundeskanzler`: Chancellor during period
  - `sitze_gesamt`: Total seats in parliament

### 8. Fraktion (Parliamentary Group)
- **Endpoint**: Built from metadata and person data
- **Entity Type**: `BundestagFraktion`
- **Description**: Parliamentary groups/factions
- **Key Fields**:
  - `fraktion_name`: Full faction name
  - `kurz`: Abbreviation (SPD, CDU/CSU, etc.)
  - `sitze`: Number of seats
  - `koalition_opposition`: Coalition or opposition status

## Entity Relationships

### Primary Edges (15 types)

1. **Vorgang → Wahlperiode** (`IN_WAHLPERIODE`)
   - Links procedures to electoral periods

2. **Vorgang → Drucksache** (`HAS_DRUCKSACHE`)
   - Links procedures to their documents

3. **Drucksache → Wahlperiode** (`IN_WAHLPERIODE`)
   - Links documents to electoral periods

4. **Person → Fraktion** (`MEMBER_OF_FRAKTION`)
   - Links MPs to their parliamentary groups

5. **Person → Wahlperiode** (`ACTIVE_IN_WAHLPERIODE`)
   - Links MPs to periods they served

6. **Fraktion → Wahlperiode** (`EXISTS_IN_WAHLPERIODE`)
   - Links factions to electoral periods

7. **Vorgangsposition → Vorgang** (`POSITION_OF_VORGANG`)
   - Links procedure steps to procedures

8. **Aktivitaet → Vorgang** (`ACTIVITY_OF_VORGANG`)
   - Links activities to procedures

9. **Aktivitaet → Plenarprotokoll** (`DOCUMENTED_IN_PROTOKOLL`)
   - Links activities to plenary protocols

10. **Plenarprotokoll → Wahlperiode** (`IN_WAHLPERIODE`)
    - Links protocols to electoral periods
    - Properties: `entity_type`, `active_from` (session date)

11. **Plenarprotokoll → Vorgang** (`REFERENCES_VORGANG`)
    - Links protocols to procedures discussed in session
    - Properties: `reference_type="debated_in_plenum"`, `context`
    - Multiple: One protocol can reference many Vorgänge

12. **Person → Vorgang** (`INITIATES_VORGANG`)
    - Links MPs to procedures they initiated

13. **Person → Aktivitaet** (`PARTICIPATES_IN_ACTIVITY`)
    - Links MPs to activities they participated in

14. **Drucksache → Person** (`AUTHORED_BY`)
    - Links documents to their authors

15. **Vorgang → Vorgang** (`RELATED_TO_VORGANG`)
    - Links related procedures

16. **Fraktion → Vorgang** (`FRAKTION_POSITION_ON`)
    - Links factions to their positions on procedures

## Configuration

### Input Parameters

```yaml
# Bundestag ingestion configuration
wahlperiode: 20  # Electoral period to collect (20 = 2021-2025)
datum_von: "2024-01-01"  # Start date for collection
datum_bis: "2024-12-31"  # End date for collection
limit: 1000  # Maximum items per collector
data_sources:  # Which sources to collect from
  - vorgang
  - drucksache
  - person
  - plenarprotokoll
  - vorgangsposition
  - aktivitaet
```

### API Configuration

```python
# API client settings
BASE_URL = "https://search.dip.bundestag.de/api/v1/"
API_KEY = "YOUR_API_KEY"  # Default public key provided
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
TIMEOUT = 30  # seconds
```

### Rate Limiting

The Bundestag DIP API has rate limits:
- **Default**: 100 requests per minute
- **Burst**: 20 requests per second
- **Headers**: `Retry-After` provided on 429 responses

The API client implements:
- Exponential backoff retry logic
- Automatic rate limit handling
- Configurable timeout and retry settings

## Usage Examples

### Example 1: Collect Legislative Procedures

```python
from src.flows.bundestag_ingestion.collectors.vorgang_collector import VorgangCollector
from src.flows.bundestag_ingestion.utils.api_client import BundestagAPIClient
from src.flows.bundestag_ingestion.transformers.entity_builder import BundestagEntityBuilder
from src.flows.bundestag_ingestion.transformers.edge_builder import BundestagEdgeBuilder

# Initialize components
api_client = BundestagAPIClient()
entity_builder = BundestagEntityBuilder()
edge_builder = BundestagEdgeBuilder()

# Create collector
collector = VorgangCollector(api_client, entity_builder, edge_builder)

# Collect data
result = await collector.collect_with_filters(
    wahlperiode="20",
    datum_von="2024-01-01",
    datum_bis="2024-12-31",
    limit=100
)

print(f"Collected {result['items_collected']} procedures")
print(f"Created {result['entities_created']} entities")
print(f"Created {result['edges_created']} edges")
```

### Example 2: Collect All Data Sources

```python
collectors = {
    'vorgang': VorgangCollector(api_client, entity_builder, edge_builder),
    'drucksache': DrucksacheCollector(api_client, entity_builder, edge_builder),
    'person': PersonCollector(api_client, entity_builder, edge_builder),
    # ... other collectors
}

results = {}
for name, collector in collectors.items():
    print(f"Collecting {name}...")
    result = await collector.collect_with_filters(
        wahlperiode="20",
        limit=500
    )
    results[name] = result

# Generate summary report
total_entities = sum(r['entities_created'] for r in results.values())
total_edges = sum(r['edges_created'] for r in results.values())
print(f"Total: {total_entities} entities, {total_edges} edges")
```

### Example 3: Filtered Collection

```python
# Collect only health-related legislation
result = await collector.collect_with_filters(
    wahlperiode="20",
    sachgebiet="Gesundheit",
    vorgangstyp="Gesetzgebung",
    beratungsstand="Abgeschlossen",
    datum_von="2023-01-01",
    limit=50
)
```

### Example 4: Pagination Handling

```python
# Collect large dataset with automatic pagination
from src.flows.bundestag_ingestion.utils.pagination import PaginationHelper

pagination = PaginationHelper(api_client, max_items=10000)

all_items = []
async for item in pagination.paginate("vorgang", {"f.wahlperiode": "20"}):
    all_items.append(item)
    print(f"Collected {len(all_items)} items...")

print(f"Total items collected: {len(all_items)}")
```

## API Endpoint Reference

### Base URL
```
https://search.dip.bundestag.de/api/v1/
```

### Common Query Parameters

- `apikey`: API authentication key (required)
- `f.wahlperiode`: Filter by electoral period (e.g., "20")
- `f.datum`: Filter by date (ISO 8601 format)
- `f.vorgangstyp`: Filter by procedure type
- `f.beratungsstand`: Filter by status
- `num`: Number of results per page (default: 100, max: 100)
- `cursor`: Pagination cursor for next page
- `sort`: Sort order (e.g., "datum desc")

### Response Format

```json
{
  "documents": [
    {
      "id": "287654",
      "titel": "Gesetz zur...",
      "vorgangstyp": "Gesetzgebung",
      "wahlperiode": 20,
      // ... more fields
    }
  ],
  "numFound": 1234,
  "cursor": "AoE/cursor_string"
}
```

### Error Responses

- **400 Bad Request**: Invalid parameters
- **401 Unauthorized**: Invalid API key
- **404 Not Found**: Resource not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: API error

## Troubleshooting

### Common Issues

#### 1. Rate Limiting

**Symptoms**: 429 HTTP errors, `Rate limit exceeded` messages

**Solution**:
```python
# Increase retry delay and max retries
api_client = BundestagAPIClient(
    max_retries=5,
    retry_delay=2.0  # Start with 2 seconds
)
```

#### 2. Timeout Errors

**Symptoms**: `Request timeout` errors, slow responses

**Solution**:
```python
# Increase timeout
api_client = BundestagAPIClient(timeout=60)
```

#### 3. Empty Results

**Symptoms**: `numFound: 0` in responses

**Solution**:
- Verify filter parameters are correct
- Check date ranges (use ISO 8601 format: YYYY-MM-DD)
- Verify Wahlperiode number exists (19, 20, 21)
- Test with minimal filters first

#### 4. Authentication Errors

**Symptoms**: 401 Unauthorized responses

**Solution**:
```python
# Use valid API key
api_client = BundestagAPIClient(api_key="YOUR_VALID_KEY")

# Or use default public key (expires 05/2026)
api_client = BundestagAPIClient()  # Uses default key
```

#### 5. Pagination Issues

**Symptoms**: Incomplete data collection, missing items

**Solution**:
```python
# Ensure cursor is being passed correctly
# PaginationHelper handles this automatically
pagination = PaginationHelper(api_client, max_items=None)  # No limit
```

### Debug Logging

Enable detailed logging:

```python
import structlog
import logging

logging.basicConfig(level=logging.DEBUG)
logger = structlog.get_logger()

# API client will now log all requests and responses
```

### Health Check

Test API connectivity:

```python
api_client = BundestagAPIClient()
is_healthy = await api_client.health_check()

if is_healthy:
    print("API is accessible")
else:
    print("API connection failed")
```

### Collector Health Check

Test individual collector:

```python
collector = VorgangCollector(api_client, entity_builder, edge_builder)
is_healthy = await collector.health_check()

if is_healthy:
    print(f"{collector.entity_type} collector is working")
```

## Performance Optimization

### Batch Collection

Collect multiple sources in parallel:

```python
import asyncio

collectors = [vorgang_collector, drucksache_collector, person_collector]

# Collect in parallel
results = await asyncio.gather(*[
    collector.collect_with_filters(wahlperiode="20", limit=100)
    for collector in collectors
])
```

### Memory Management

For large collections:

```python
# Process in smaller batches
batch_size = 100
total_items = 1000

for offset in range(0, total_items, batch_size):
    result = await collector.collect_with_filters(
        wahlperiode="20",
        limit=batch_size
    )
    # Process result before next batch
```

### Caching Strategy

Cache frequently accessed data:

```python
# Cache Wahlperiode data (rarely changes)
wahlperiode_cache = {}

# Cache Fraktion data per Wahlperiode
fraktion_cache = {}
```

## Integration with Knowledge Graph

### Entity Storage

Entities are stored in Neo4j via Kodosumi interface:

```cypher
// Example: Vorgang entity
CREATE (v:Vorgang {
    id: "287654",
    vorgang_name: "Gesetz zur...",
    vorgangstyp: "Gesetzgebung",
    wahlperiode: 20,
    beratungsstand: "Abgeschlossen"
})
```

### Edge Storage

Relationships connect entities:

```cypher
// Example: Vorgang → Drucksache relationship
MATCH (v:Vorgang {id: "287654"})
MATCH (d:Drucksache {dokumentnummer: "20/1234"})
CREATE (v)-[:HAS_DRUCKSACHE]->(d)
```

### Query Examples

```cypher
// Find all legislation in current period
MATCH (v:Vorgang)-[:IN_WAHLPERIODE]->(w:Wahlperiode {wahlperiode_nummer: 20})
WHERE v.vorgangstyp = "Gesetzgebung"
RETURN v

// Find all documents authored by a person
MATCH (p:BundestagPerson {person_name: "Anna Müller"})-[:AUTHORED]->(d:Drucksache)
RETURN d

// Find coalition parties in current period
MATCH (f:BundestagFraktion)-[:EXISTS_IN_WAHLPERIODE]->(w:Wahlperiode {wahlperiode_nummer: 20})
WHERE f.koalition_opposition = "Koalition"
RETURN f
```

## Testing

### Running Tests

```bash
# All Bundestag tests
pytest tests/unit/flows/bundestag_ingestion/ -v

# Specific test file
pytest tests/unit/flows/bundestag_ingestion/test_collectors.py -v

# Integration tests
pytest tests/integration/flows/test_bundestag_ingestion_flow.py -v

# With coverage
pytest tests/unit/flows/bundestag_ingestion/ --cov=src.flows.bundestag_ingestion --cov-report=html
```

### Test Coverage

Expected coverage: >90%

- Collectors: 95%
- Transformers: 92%
- Utils (API client, pagination, filters): 93%
- Integration flow: 88%

### Sample Data

Test fixtures available in `tests/fixtures/bundestag_sample_data.py`:

- `SAMPLE_VORGANG_RESPONSE`
- `SAMPLE_DRUCKSACHE_RESPONSE`
- `SAMPLE_PERSON_RESPONSE`
- `SAMPLE_PLENARPROTOKOLL_RESPONSE`
- `SAMPLE_VORGANGSPOSITION_RESPONSE`
- `SAMPLE_AKTIVITAET_RESPONSE`
- `SAMPLE_WAHLPERIODE_DATA`
- `SAMPLE_FRAKTION_DATA`

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [Political Schema v4 Documentation](../schema/political_schema_v4.md)
- [Kodosumi Flow Patterns](../../.claude/kodosumi-patterns.md)
- [Testing Standards](../../.claude/testing-standards.md)

## Changelog

### Version 0.2.0 (2025-11-12)
- Initial implementation of Bundestag ingestion flow
- 8 data collectors implemented
- Entity and edge builders for political_schema_v4
- Comprehensive test coverage
- Full documentation
