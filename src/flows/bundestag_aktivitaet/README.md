# Flow 5f: Bundestag Aktivitaet Ingestion

**Version**: 1.0.0
**Status**: Production Ready
**Route**: `/bundestag-aktivitaet`

## Overview

Flow 5f ingests parliamentary activities (questions, answers, speeches) from the Bundestag DIP API and creates `Aktivitaet` nodes in Neo4j with rich relationships to persons, procedures (Vorgänge), and documents.

### What is an Aktivitaet?

An **Aktivitaet** represents a parliamentary activity performed by a member of the Bundestag (MdB) or government official. This includes:

- **Kleine Anfrage** - Written questions to the government
- **Antwort** - Government responses to parliamentary questions
- **Frage** - Parliamentary questions
- **Rede** - Speeches given in plenary sessions
- **Rede (zu Protokoll gegeben)** - Speeches submitted for the parliamentary record

### Data Source

- **API Endpoint**: `https://search.dip.bundestag.de/api/v1/aktivitaet`
- **Total Activities**: 1,718,071+ across all Wahlperioden
- **Update Frequency**: Real-time updates from DIP API

## Features

✅ **Complete Activity Types**: All 5+ activity types supported
✅ **Rich Relationships**: Links to Persons, Vorgänge, Documents, and Wahlperioden
✅ **Batch Processing**: Configurable batch sizes (10-500)
✅ **Smart Filtering**: Filter by Wahlperiode, activity type, and date range
✅ **Duplicate Safe**: Uses MERGE operations with unique constraints
✅ **Document References**: Embeds Fundstelle (source document) metadata
✅ **Automatic Relationship Creation**: Creates 4 relationship types after entity upsert

## Configuration

### Kodosumi Form Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `job_name` | Text | "Bundestag Aktivitaet Ingestion" | Name for this ingestion run |
| `wahlperiode` | Text | "20" | Electoral period (19, 20, 21, or comma-separated) |
| `aktivitaetsart` | Select | "Alle" | Activity type filter |
| `max_aktivitaeten` | Number | 100 | Maximum activities to fetch (1-5000) |
| `batch_size` | Number | 100 | API batch size (10-500) |
| `create_relationships` | Checkbox | true | Create relationships to related entities |
| `start_date` | Text | "" | Optional: Start date filter (YYYY-MM-DD) |
| `end_date` | Text | "" | Optional: End date filter (YYYY-MM-DD) |

### Activity Types

- **Alle** - All activity types (default)
- **Kleine Anfrage** - Written Questions
- **Antwort** - Government Answers
- **Frage** - Parliamentary Questions
- **Rede** - Speeches
- **Rede (zu Protokoll gegeben)** - Speeches for Record

## Neo4j Schema

### Node: Aktivitaet

```cypher
CREATE (a:Aktivitaet {
  aktivitaet_id: "1712384",              // Unique ID (PRIMARY KEY)
  aktivitaetsart: "Kleine Anfrage",      // Activity type
  typ: "Aktivität",
  person_id: "1769",                      // FK to BundestagPerson
  wahlperiode: 20,
  datum: "2025-03-21",
  titel: "...",                           // Description
  dokumentart: "Drucksache",
  vorgangsbezug_anzahl: 1,               // Count of related procedures
  aktualisiert: "2025-03-25T07:11:03+01:00",

  // Fundstelle (source document)
  fundstelle_id: "279108",
  fundstelle_dokumentnummer: "20/15144",
  fundstelle_datum: "2025-03-24",
  fundstelle_pdf_url: "https://...",
  fundstelle_dokumentart: "Drucksache",
  fundstelle_drucksachetyp: "Kleine Anfrage",
  fundstelle_herausgeber: "BT",
  fundstelle_urheber: ["Gruppe BSW"],    // JSON array

  vorgangsbezug_json: "[{...}]"          // Related procedures as JSON
})
```

### Relationships

Flow 5f creates **4 types of relationships** automatically:

#### 1. PERFORMED_BY → BundestagPerson
Links activity to the person who performed it

```cypher
(Aktivitaet)-[:PERFORMED_BY]->(BundestagPerson)
```

**Data Source**: `person_id` field from API response
**Example**: Aktivitaet "1712384" → PERFORMED_BY → Julia Verlinden (person_id: "1769")

---

#### 2. RELATED_TO_VORGANG → Vorgang
Links activity to legislative procedures

```cypher
(Aktivitaet)-[:RELATED_TO_VORGANG {vorgangsposition: "..."}]->(Vorgang)
```

**Data Source**: `vorgangsbezug` array from API response
**Property**: `vorgangsposition` (role in procedure, e.g., "Kleine Anfrage")
**Note**: Can create multiple relationships if activity relates to multiple procedures

---

#### 3. REFERENCES_DOCUMENT → Drucksache
Links to source document (Drucksache)

```cypher
(Aktivitaet)-[:REFERENCES_DOCUMENT]->(Drucksache)
```

**Data Source**: `fundstelle.dokumentnummer` from API response
**Benefit**: Access PDF documents through existing Drucksache nodes (no duplicate processing!)

---

#### 4. IN_WAHLPERIODE → Wahlperiode
Links to electoral period

```cypher
(Aktivitaet)-[:IN_WAHLPERIODE]->(Wahlperiode)
```

**Data Source**: `wahlperiode` field from API response
**Note**: Creates Wahlperiode node if it doesn't exist

## Usage Examples

### Run via Kodosumi

1. Navigate to: http://localhost:3370
2. Select "Flow 5f: Bundestag Aktivitaet Ingestion"
3. Configure:
   - Wahlperiode: 20
   - Aktivitaetsart: Kleine Anfrage
   - Maximum Activities: 50
   - Create Relationships: ✓
4. Click "Start Collection"

### Query Examples

#### Get all activities by a person
```cypher
MATCH (p:BundestagPerson {person_id: "1769"})<-[:PERFORMED_BY]-(a:Aktivitaet)
RETURN a.aktivitaetsart, a.datum, a.titel
ORDER BY a.datum DESC
LIMIT 10
```

#### Find activities related to a specific procedure
```cypher
MATCH (v:Vorgang {vorgang_id: "320988"})<-[:RELATED_TO_VORGANG]-(a:Aktivitaet)
RETURN a.aktivitaetsart, a.person_id, a.datum
ORDER BY a.datum
```

#### Count activities by type
```cypher
MATCH (a:Aktivitaet)
WHERE a.wahlperiode = 20
RETURN a.aktivitaetsart, count(*) as count
ORDER BY count DESC
```

#### Find speeches and their documents
```cypher
MATCH (a:Aktivitaet {aktivitaetsart: "Rede"})-[:REFERENCES_DOCUMENT]->(d:Drucksache)
RETURN a.person_id, a.titel, d.drucksache_nummer, a.datum
ORDER BY a.datum DESC
LIMIT 20
```

#### Activity timeline for a Wahlperiode
```cypher
MATCH (a:Aktivitaet)-[:IN_WAHLPERIODE]->(w:Wahlperiode {wahlperiode_nummer: 20})
WITH date(a.datum) as day, count(*) as count
RETURN day, count
ORDER BY day DESC
LIMIT 30
```

#### Most active MdBs by question count
```cypher
MATCH (p:BundestagPerson)<-[:PERFORMED_BY]-(a:Aktivitaet)
WHERE a.aktivitaetsart = "Kleine Anfrage"
  AND a.wahlperiode = 20
WITH p.person_name as name, count(*) as questions
RETURN name, questions
ORDER BY questions DESC
LIMIT 10
```

## Expected Data Volume

- **All Wahlperioden**: 1,718,071+ activities
- **Wahlperiode 20**: ~129,333 activities
- **Relationships**: ~4 per activity = 516,000+ relationships
- **Processing Time**: ~20-30 minutes for 100,000 activities (with relationships)
- **Batch Processing**: 100 activities every ~5 seconds

## Graph Impact

After ingestion, you can answer questions like:

- Who asked the most written questions this quarter?
- What activities are related to a specific legislative procedure?
- Show all speeches by a person on a given topic
- Timeline of government responses to parliamentary questions
- Which documents reference the same legislative procedure?

## Performance Tips

1. **Start Small**: Test with `max_aktivitaeten: 10`
2. **Filter by Type**: Use specific `aktivitaetsart` instead of "Alle"
3. **Date Ranges**: Use date filters for incremental updates
4. **Batch Size**: Adjust based on API performance (default: 100)
5. **Relationships**: Disable for faster ingestion, create later if needed

## Troubleshooting

### No activities ingested?

Check:
1. API key is valid (BUNDESTAG_API_KEY)
2. Wahlperiode format is correct ("20" not "WP20")
3. Date range doesn't exclude all results
4. Check Ray logs: `tail -f /tmp/ray/session_latest/logs/serve/*.log`

### Relationships not created?

Check:
1. `create_relationships` is checked in form
2. Related entities exist:
   - Run Flow 5a first (Persons)
   - Run Flow 5c first (Drucksachen)
   - Run Flow 5b if querying Vorgänge
3. Check relationship stats in final report
4. Verify in Neo4j: `MATCH ()-[r:PERFORMED_BY]->() RETURN count(r)`

### Slow performance?

Optimize:
- Reduce `max_aktivitaeten`
- Increase `batch_size` to 200-500
- Disable relationship creation initially
- Create indexes on Aktivitaet fields (done automatically)

### API 404 errors?

Fixed in v1.0.0:
- URL construction now handles trailing slashes correctly
- Aktivitaetsart filter properly passed to API
- Parameter mapping from `max_aktivitaeten` to `max_items` corrected

## Integration with Other Flows

### Prerequisites

For full relationship creation, the target nodes must already exist:

1. **Flow 5a** (Person): Required for PERFORMED_BY relationships
2. **Flow 5c** (Drucksache): Required for REFERENCES_DOCUMENT relationships
3. **Flow 5b** (Vorgang): Optional for RELATED_TO_VORGANG relationships
4. **Wahlperiode**: Created automatically if missing

### Recommended Ingestion Order

1. Flow 5a - Bundestag Person (creates BundestagPerson nodes)
2. Flow 5c - Bundestag Drucksache (creates Drucksache nodes)
3. **Flow 5f - Bundestag Aktivitaet** (links everything together)
4. Flow 5b - Bundestag Vorgang (optional, completes the graph)

### Why This Order?

- **Persons first**: Most activities reference persons (PERFORMED_BY)
- **Drucksachen second**: Most activities reference documents (REFERENCES_DOCUMENT)
- **Aktivitäten third**: Creates the linking layer between persons and documents
- **Vorgänge last**: Vorgänge reference Aktivitäten, so create them after

## API Reference

### Health Check

```bash
curl http://localhost:8001/bundestag-aktivitaet/health
```

Response:
```json
{
  "status": "healthy",
  "service": "political-monitoring-agent-flow5f",
  "version": "1.0.0",
  "flow": "bundestag_aktivitaet"
}
```

### Flow Endpoint

**URL**: `http://localhost:8001/bundestag-aktivitaet`
**Method**: POST (via Kodosumi form)
**Authentication**: None (API key in config)

## Version History

### 1.0.0 (2025-11-14)

**Initial Release**
- Support for all activity types (Kleine Anfrage, Antwort, Frage, Rede, etc.)
- 4 relationship types (PERFORMED_BY, RELATED_TO_VORGANG, REFERENCES_DOCUMENT, IN_WAHLPERIODE)
- Smart filtering and batch processing
- Complete documentation

**Bug Fixes Applied**:
- Fixed URL construction for proper slash handling
- Fixed parameter mapping from `max_aktivitaeten` to `max_items`
- Fixed `aktivitaetsart` filter support in base_flow
- Fixed relationship creation not being called (added to process override)
- Fixed `self.driver` → `self.neo4j_driver` attribute name
- Fixed stats counting bug (double `result.single()` calls)

## Architecture Notes

### Code Structure

```
src/flows/bundestag_aktivitaet/
├── __init__.py           # Package initialization
├── app.py                # Kodosumi endpoint (FastAPI)
├── processor.py          # Business logic + relationship creation
├── forms.py             # Kodosumi form definition
└── README.md            # This file
```

### Key Components

1. **app.py**:
   - Validates form inputs
   - Launches processor with correct parameters
   - Maps `max_aktivitaeten` → `max_items` for base_flow compatibility

2. **processor.py**:
   - Extends `BaseBundestagFlow`
   - Overrides `process()` to add Stage 4: Relationship Creation
   - Implements `map_api_to_entity()` for data transformation
   - Implements `create_relationships()` for graph linking

3. **forms.py**:
   - Defines Kodosumi UI form
   - Uses `F.Select` for activity type dropdown
   - Uses `F.Checkbox` for relationship creation toggle

### Relationship Creation Logic

Relationships are created **after** all entities are upserted to Neo4j. This ensures:
1. All Aktivitaet nodes exist before linking
2. Batch processing is efficient
3. Errors in one relationship don't affect others
4. Statistics are accurate

The `create_relationships()` method:
- Iterates through all upserted entities
- Uses `MERGE` for idempotent relationship creation
- Counts successful creations for reporting
- Handles errors gracefully (logs but continues)

## Support

For issues or questions:
- Check Ray logs: `tail -f /tmp/ray/session_latest/logs/serve/*.log`
- Check Neo4j browser: http://localhost:7474
- Monitor Kodosumi: http://localhost:3370
- Check Ray dashboard: http://localhost:8265

## License

Part of the Political Monitoring Agent v0.2.0
