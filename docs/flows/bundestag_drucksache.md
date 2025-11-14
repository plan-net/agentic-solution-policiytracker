# Flow 5c: Bundestag Drucksache Ingestion

## Overview

Flow 5c collects German Bundestag parliamentary documents (Drucksachen) from the DIP API, including bills, motions, reports, and inquiries. Supports metadata-only collection or full-text extraction with page-by-page PDF processing.

### Purpose

- Ingest parliamentary documents from the German Bundestag
- Track legislative documents (bills, motions, reports, inquiries)
- Optional full-text extraction from PDF documents
- Build document relationships to Vorgang and Wahlperiode entities
- Support two-phase workflow: metadata first, then selective full-text

### Key Features

- **Comprehensive Document Types**: Gesetzentwurf (Bill), Antrag (Motion), Bericht (Report), Kleine/Große Anfrage (Inquiry), Beschlussempfehlung (Recommendation)
- **Two-Phase Workflow**: Fast metadata collection first, selective full-text extraction later
- **Page-by-Page PDF Extraction**: Using PyPDF for accurate text capture
- **Markdown Export**: Each page exported with headers for readability
- **Local Storage**: Organized by Wahlperiode with separate PDF and markdown directories
- **Relationship Creation**: Automatic linking to Wahlperiode and Vorgang entities
- **Flexible Filtering**: Filter by Wahlperiode, Dokumentart, and date ranges

## Architecture

```
Bundestag DIP API /drucksache endpoint
         ↓
   Cursor-based Pagination
         ↓
   Data Collection & Mapping
         ↓
   Entity Extraction:
   - Drucksache entities (metadata)
   - DrucksachePage entities (optional full-text)
         ↓
   Optional PDF Processing:
   - Download PDFs (concurrency control)
   - Extract text page-by-page (PyPDF)
   - Save as markdown with page headers
         ↓
   Neo4j MERGE Operations
         ↓
   Relationship Creation:
   - BELONGS_TO (Wahlperiode)
   - DOCUMENT_FOR (Vorgang)
         ↓
   Knowledge Graph + Local Storage
```

## Data Model

### Primary Entity: `Drucksache`

**Unique Identifier**: `drucksache_id` (from DIP API)

**Core Fields**:
- `drucksache_id`: Unique identifier
- `drucksache_nummer`: Document number (e.g., "19/12345")
- `titel`: Full title of the document
- `dokumentart`: Document type (Gesetzentwurf, Antrag, Bericht, etc.)
- `dokumentnummer`: Document number component
- `wahlperiode`: Electoral period number
- `datum`: Publication date
- `aktualisiert`: Last updated timestamp
- `herausgeber`: Publisher (typically "BT" for Bundestag)
- `typ`: Entity type (always "Drucksache")

**Classification Fields**:
- `abstract`: Summary description (optional)
- `fundstelle`: Source reference (JSON)
- `ressort`: Ministry/department assignments (list)
- `initiative`: Initiating body (list)
- `urheber`: Originators (JSON)

**Document Access**:
- `dokument_url`: PDF download URL
- `autoren_anzahl`: Number of authors
- `autoren_anzeige`: Author display string

**Relationship Data**:
- `vorgang_ids_json`: Related Vorgang IDs (JSON) - for relationship creation

### Related Entity: `DrucksachePage` (Future Enhancement)

**Purpose**: Store page-by-page extracted text for advanced queries

**Fields**:
- `page_id`: Composite ID (drucksache_nummer + page number)
- `drucksache_nummer`: Parent document reference
- `page_number`: Page index (1-based)
- `page_text`: Extracted text content
- `wahlperiode`: Electoral period for organization

## API Integration

### Endpoint
```
GET https://search.dip.bundestag.de/api/v1/drucksache
```

### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `f.wahlperiode` | integer | Filter by electoral period | `20` |
| `f.dokumentart` | string | Filter by document type | `"Gesetzentwurf"` |
| `f.datum.start` | string | Start date (ISO 8601) | `"2024-01-01"` |
| `f.datum.end` | string | End date (ISO 8601) | `"2024-12-31"` |
| `format` | string | Response format | `"json"` |
| `cursor` | string | Pagination cursor | Auto-managed |

### Dokumentart Options

- **Gesetzentwurf**: Legislative bill
- **Antrag**: Motion or proposal
- **Bericht**: Report
- **Kleine Anfrage**: Minor parliamentary inquiry
- **Große Anfrage**: Major parliamentary inquiry
- **Beschlussempfehlung**: Recommendation for decision
- **Unterrichtung**: Information or notification
- **Alle**: All document types

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
   Navigate to: Bundestag Drucksache Ingestion
   ```

2. **Configure Parameters**:
   - **Job Name**: Descriptive name (e.g., "WP 20 Bills")
   - **Wahlperiode**: Comma-separated periods (e.g., "19,20,21")
   - **Dokumentart**: Filter by type or "Alle" for all
   - **Date Filters**: Optional start/end dates (YYYY-MM-DD)
   - **Batch Size**: Processing batch size (10-500)
   - **Maximum Documents**: Limit total processing (1-10000)
   - **Extract Full Text**: Enable/disable PDF processing
   - **Max Concurrent Downloads**: Limit concurrent PDFs (1-10)
   - **Create Relationships**: Enable/disable relationship creation

3. **Submit**: Click "Start Collection"

4. **Monitor Progress**: Real-time updates via Kodosumi tracer

### Programmatic Usage

```python
from src.flows.bundestag_drucksache.processor import process_drucksache_batch

inputs = {
    "wahlperioden": ["20"],
    "dokumentart": "Gesetzentwurf",
    "batch_size": 100,
    "max_drucksachen": 1000,
    "extract_full_text": False,  # Metadata only
    "max_concurrent_downloads": 5,
    "create_relationships": True,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
}

# Mock tracer for testing
class MockTracer:
    async def markdown(self, text):
        print(text)

result = await process_drucksache_batch(inputs, MockTracer())
```

### Example API Stats (WP 20)

Based on actual API data:
- **Total Drucksachen**: 281,000+ documents (all types)
- **Gesetzentwurf**: ~700 bills
- **Antrag**: ~3,000 motions
- **Kleine Anfrage**: ~15,000 minor inquiries
- **Bericht**: ~1,500 reports
- **Average PDF Size**: 1-5 MB per document

## Two-Phase Workflow Strategy

### Phase 1: Fast Metadata Collection (Recommended First Step)

```yaml
Configuration:
  - extract_full_text: False
  - max_drucksachen: 10000
  - batch_size: 200

Performance:
  - Speed: 200-300 documents/minute
  - Memory: ~500MB
  - Duration: 30-60 minutes for 10,000 documents

Benefits:
  - Build complete graph structure quickly
  - Identify relevant documents
  - Create all relationships
  - Enable graph queries immediately
```

### Phase 2: Selective Full-Text Extraction

```yaml
Configuration:
  - extract_full_text: True
  - max_drucksachen: 100  # Smaller batches
  - batch_size: 50
  - Filter: By dokumentart or date range

Performance:
  - Speed: 10-20 documents/minute
  - Memory: ~2GB (5-25MB PDFs buffered)
  - Duration: 5-10 minutes per 100 documents

Benefits:
  - Focus on high-priority documents
  - Manage storage costs
  - Balance processing time
```

## PDF Storage and Processing

### Storage Structure

```
data/drucksachen/
├── wp19/
│   ├── pdfs/
│   │   ├── 19-1234.pdf
│   │   └── 19-5678.pdf
│   ├── 19-1234.md
│   └── 19-5678.md
├── wp20/
│   ├── pdfs/
│   │   ├── 20-9101.pdf
│   │   └── 20-1121.pdf
│   ├── 20-9101.md
│   └── 20-1121.md
└── wp21/
    └── ...
```

### Markdown Export Format

```markdown
# Drucksache 20/1234

Wahlperiode: 20

---

## Seite 1

[Page 1 text content...]

---

## Seite 2

[Page 2 text content...]

---

## Seite 3

[Page 3 text content...]

---
```

### PDF Processing Pipeline

```python
# Step 1: Download PDF
async def download_pdf(session, url, save_path, semaphore):
    # Concurrency control with semaphore
    # Timeout: 60 seconds
    # Error handling for network issues

# Step 2: Extract text page-by-page
async def extract_pdf_text(pdf_path):
    # PyPDF PdfReader
    # Extract each page separately
    # Handle extraction errors gracefully

# Step 3: Save as markdown
def save_pages_as_markdown(drucksache_nummer, pages, wahlperiode):
    # Format with page headers
    # Organize by Wahlperiode
    # UTF-8 encoding for German characters
```

## Relationships

### Created Relationships

1. **Drucksache → Wahlperiode** (`BELONGS_TO`)
   ```cypher
   MATCH (d:Drucksache {wahlperiode: 20})
   MATCH (w:Wahlperiode {wahlperiode_nummer: 20})
   MERGE (d)-[:BELONGS_TO]->(w)
   ```

2. **Drucksache → Vorgang** (`DOCUMENT_FOR`)
   ```cypher
   MATCH (d:Drucksache)
   WHERE d.vorgang_ids_json IS NOT NULL
   WITH d, d.vorgang_ids_json as vorgang_json
   UNWIND apoc.convert.fromJsonList(vorgang_json) as vorgang_id
   MATCH (v:Vorgang {vorgang_id: vorgang_id})
   MERGE (d)-[:DOCUMENT_FOR]->(v)
   ```
   **Note**: Requires APOC for JSON parsing

3. **Future: DrucksachePage → Drucksache** (`PAGE_OF`)
   ```cypher
   MATCH (p:DrucksachePage)
   MATCH (d:Drucksache {drucksache_nummer: p.drucksache_nummer})
   MERGE (p)-[:PAGE_OF]->(d)
   ```

## Field Mapping Logic

### Drucksache Entity Mapping

```python
def map_drucksache_to_entity(api_data: Dict) -> Dict:
    """
    Maps DIP API response to Neo4j entity structure.

    Handles:
    - String fields with safe_str()
    - List fields with safe_list()
    - Date fields with safe_date()
    - JSON serialization for complex nested objects (urheber, fundstelle)
    - Related Vorgang IDs extraction for relationships
    """
```

### PDF URL Extraction

```python
# Extract PDF URL from API response
if api_data.get("dokumentUrl"):
    entity["dokument_url"] = safe_str(api_data["dokumentUrl"])

# PDF URLs typically look like:
# https://dserver.bundestag.de/btd/20/012/2001234.pdf
```

### Related Vorgang Extraction

```python
def extract_related_vorgang_ids(api_data: Dict) -> Optional[str]:
    """
    Extracts related Vorgang IDs from drucksache data.

    Looks in multiple API fields:
    - vorgangsbezug
    - vorgaenge
    - related_vorgaenge

    Returns: JSON string of Vorgang IDs or None
    """
```

## Configuration

### In config.yaml

```yaml
- name: flow5c-bundestag-drucksache
  route_prefix: /bundestag-drucksache
  import_path: src.flows.bundestag_drucksache.app:fast_app
  runtime_env:
    env_vars:
      NEO4J_URI: bolt://localhost:7687
      NEO4J_USERNAME: neo4j
      NEO4J_PASSWORD: password123
      NEO4J_DATABASE: politicamonitoring.v2
      BUNDESTAG_API_KEY: YOUR_API_KEY
      BUNDESTAG_API_URL: https://search.dip.bundestag.de/api/v1/
      DRUCKSACHE_STORAGE_PATH: ./data/drucksachen
  ray_actor_options:
    num_cpus: 2
    memory: 4000000000  # 4GB
  autoscaling_config:
    min_replicas: 1
    max_replicas: 2
```

### Storage Configuration

```python
# Environment variable for storage path
DRUCKSACHE_STORAGE_PATH = Path(os.getenv(
    "DRUCKSACHE_STORAGE_PATH",
    "./data/drucksachen"
))

# Automatic directory creation
DRUCKSACHE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
```

## Neo4j Schema

### Constraints

```cypher
CREATE CONSTRAINT drucksache_drucksache_id_unique IF NOT EXISTS
FOR (n:Drucksache)
REQUIRE n.drucksache_id IS UNIQUE

CREATE CONSTRAINT drucksache_drucksache_nummer_unique IF NOT EXISTS
FOR (n:Drucksache)
REQUIRE n.drucksache_nummer IS UNIQUE
```

### Indexes

```cypher
-- Drucksache indexes
CREATE INDEX drucksache_drucksache_id_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.drucksache_id)

CREATE INDEX drucksache_drucksache_nummer_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.drucksache_nummer)

CREATE INDEX drucksache_wahlperiode_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.wahlperiode)

CREATE INDEX drucksache_dokumentart_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.dokumentart)

CREATE INDEX drucksache_datum_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.datum)

CREATE INDEX drucksache_dokumentnummer_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.dokumentnummer)
```

## Query Examples

### Find all bills in current period
```cypher
MATCH (d:Drucksache {dokumentart: "Gesetzentwurf"})
WHERE d.wahlperiode = 20
RETURN d.drucksache_nummer, d.titel, d.datum
ORDER BY d.datum DESC
LIMIT 20
```

### Find documents for a specific Vorgang
```cypher
MATCH (d:Drucksache)-[:DOCUMENT_FOR]->(v:Vorgang {vorgang_id: "123456"})
RETURN d.drucksache_nummer, d.dokumentart, d.titel, d.datum
ORDER BY d.datum
```

### Find documents by date range
```cypher
MATCH (d:Drucksache)
WHERE d.wahlperiode = 20
  AND d.datum >= date("2024-01-01")
  AND d.datum <= date("2024-12-31")
RETURN d.drucksache_nummer, d.dokumentart, d.titel, d.datum
ORDER BY d.datum DESC
```

### Count documents by type
```cypher
MATCH (d:Drucksache {wahlperiode: 20})
RETURN d.dokumentart as type, count(*) as count
ORDER BY count DESC
```

### Find documents with PDF URLs
```cypher
MATCH (d:Drucksache)
WHERE d.dokument_url IS NOT NULL
  AND d.wahlperiode = 20
RETURN d.drucksache_nummer, d.dokumentart, d.dokument_url
LIMIT 10
```

### Find documents by author
```cypher
MATCH (d:Drucksache)
WHERE d.autoren_anzeige CONTAINS "Schmidt"
  AND d.wahlperiode = 20
RETURN d.drucksache_nummer, d.titel, d.autoren_anzeige
ORDER BY d.datum DESC
```

## Performance

### Typical Metrics

**Metadata-Only Collection**:
- **Collection Speed**: 200-300 documents/minute
- **Entity Creation**: 2-3 seconds per batch of 100
- **Relationship Creation**: 1-2 seconds per batch
- **Memory Usage**: ~500MB for 1000 documents
- **API Response Time**: 500ms-2s per request

**Full-Text Extraction**:
- **Collection Speed**: 10-20 documents/minute
- **PDF Download**: 2-5 seconds per document (depending on size)
- **Text Extraction**: 1-3 seconds per document
- **Memory Usage**: 2-3GB for concurrent downloads
- **Disk Usage**: 1-5MB per PDF, 50-200KB per markdown file

### Optimization Tips

1. **Two-Phase Approach**: Collect metadata first (fast), extract full-text selectively (slow)
2. **Batch Size**: Use 100-200 for metadata, 50-100 for full-text
3. **Concurrent Downloads**: Limit to 5-10 to manage memory and network
4. **Date Range Filtering**: Focus on recent documents first
5. **Dokumentart Filtering**: Process bills (Gesetzentwurf) separately from inquiries
6. **Storage Management**: Regularly archive old PDF files

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
**Symptom**: No drucksachen collected

**Solution**:
- Verify Wahlperiode is valid (19, 20, 21)
- Try `dokumentart="Alle"` first
- Check API key is valid
- Test with small `max_drucksachen` value (e.g., 10)
- Verify date range is not too restrictive

#### 3. PDF Download Failures
**Symptom**: PDFs not downloaded or empty files

**Solution**:
```bash
# Check network connectivity
curl -I https://dserver.bundestag.de/

# Verify storage path is writable
ls -la ./data/drucksachen/

# Check disk space
df -h

# Reduce concurrent downloads
max_concurrent_downloads: 3  # Lower value
```

#### 4. Memory Issues with Full-Text
**Symptom**: Ray actor OOM errors during PDF processing

**Solution**:
- Reduce `max_concurrent_downloads` to 3 or lower
- Reduce `batch_size` to 25-50
- Disable `extract_full_text` temporarily
- Increase memory allocation in config.yaml to 6GB
- Process smaller batches (e.g., 100 documents at a time)

#### 5. APOC Not Available for Relationships
**Symptom**: Vorgang relationships not created

**Solution**:
```cypher
-- Install APOC plugin in Neo4j
-- Or manually parse JSON in Cypher (alternative method)
MATCH (d:Drucksache)
WHERE d.vorgang_ids_json IS NOT NULL
WITH d, apoc.convert.fromJsonList(d.vorgang_ids_json) as vorgang_ids
UNWIND vorgang_ids as vorgang_id
MATCH (v:Vorgang {vorgang_id: vorgang_id})
MERGE (d)-[:DOCUMENT_FOR]->(v)
```

#### 6. PyPDF Extraction Errors
**Symptom**: Empty markdown files or missing pages

**Solution**:
- Check PDF file integrity (not corrupted)
- Verify PyPDF is installed: `pip install pypdf`
- Some PDFs may be scanned images (OCR required)
- Check logs for specific page extraction errors

## Processing Pipeline Details

### Stage 1: Data Collection
```python
# Cursor-based pagination
while cursor and wp_count < max_drucksachen:
    documents, next_cursor = await fetch_drucksachen_from_api(
        client, wahlperiode, dokumentart, start_date, end_date, cursor
    )
    cursor = next_cursor
```

### Stage 2: Entity Mapping
```python
# Map each document to entity structure
drucksache_entities = []
for doc in documents:
    drucksache_entity = map_drucksache_to_entity(doc)
    drucksache_entities.append(drucksache_entity)
```

### Stage 3: Neo4j Upsert
```python
# MERGE-based upsert with deduplication
upsert_manager.upsert_entities_batch(
    entity_type="Drucksache",
    entities=drucksache_entities,
    batch_size=100
)
```

### Stage 4: PDF Processing (Optional)
```python
# Concurrent PDF downloads with semaphore
semaphore = asyncio.Semaphore(max_concurrent_downloads)

for task in pdf_download_tasks:
    # Download PDF
    success = await download_pdf(session, url, save_path, semaphore)

    if success:
        # Extract text page-by-page
        pages = await extract_pdf_text(save_path)

        # Save as markdown
        md_path = save_pages_as_markdown(nummer, pages, wahlperiode)
```

### Stage 5: Relationship Creation
```python
# Create relationships via Cypher queries
rel_count = await create_drucksache_relationships(
    driver, database, [d["drucksache_nummer"] for d in entities]
)
```

## Testing

### Unit Tests
```bash
pytest tests/unit/flows/bundestag_drucksache/ -v
```

### Integration Tests
```bash
pytest tests/integration/flows/test_bundestag_drucksache_flow.py -v
```

### Manual API Testing
```bash
# Test API connectivity
curl -H "Authorization: ApiKey YOUR_KEY" \
  "https://search.dip.bundestag.de/api/v1/drucksache?f.wahlperiode=20&num=1"

# Test with filters
curl -H "Authorization: ApiKey YOUR_KEY" \
  "https://search.dip.bundestag.de/api/v1/drucksache?f.wahlperiode=20&f.dokumentart=Gesetzentwurf&num=10"

# Test PDF download
curl -I https://dserver.bundestag.de/btd/20/012/2001234.pdf
```

### Testing Full-Text Extraction
```python
# Test PDF download and extraction
from src.flows.bundestag_drucksache.processor import download_pdf, extract_pdf_text

# Download test PDF
async with aiohttp.ClientSession() as session:
    semaphore = asyncio.Semaphore(1)
    success = await download_pdf(
        session,
        "https://dserver.bundestag.de/btd/20/012/2001234.pdf",
        Path("./test.pdf"),
        semaphore
    )

# Extract text
if success:
    pages = await extract_pdf_text(Path("./test.pdf"))
    print(f"Extracted {len(pages)} pages")
```

## Related Flows

- **Flow 5**: Bundestag Ingestion (main flow - comprehensive)
- **Flow 5a**: Bundestag Person (MPs - for author relationships)
- **Flow 5b**: Bundestag Vorgang (legislative procedures - parent documents)
- **Flow 5g**: Bundestag Wahlperiode (electoral periods - prerequisite)
- **Flow 5h**: Bundestag Fraktion (parliamentary groups - for party documents)

## Prerequisites

Before running this flow:

1. **Neo4j Constraints**: Create via Flow 5 or manually
2. **Wahlperiode Nodes**: Run Flow 5g or script
3. **Vorgang Nodes**: Run Flow 5b for DOCUMENT_FOR relationships
4. **Storage Directory**: Ensure write permissions for PDF/markdown storage
5. **APOC Plugin**: Required for Vorgang relationships (optional)
6. **PyPDF Library**: Required for full-text extraction (`pip install pypdf`)

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [Neo4j MERGE Documentation](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [PyPDF Documentation](https://pypdf.readthedocs.io/)
- [APOC JSON Functions](https://neo4j.com/labs/apoc/4.4/overview/apoc.convert/)
- [Kodosumi Flow Patterns](../../.claude/kodosumi-patterns.md)

## Changelog

### Version 1.0.0 (2025-11-13)
- Initial implementation
- Cursor-based pagination for large datasets
- Two-phase workflow support (metadata + selective full-text)
- Page-by-page PDF extraction with PyPDF
- Markdown export with page headers
- Concurrent PDF download with semaphore control
- MERGE-based deduplication
- SSL certificate handling
- Comprehensive relationship creation
- Kodosumi form with validation
- Performance optimization for large-scale processing
- Comprehensive documentation
