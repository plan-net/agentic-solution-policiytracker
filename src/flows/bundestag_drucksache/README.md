# Flow 5c: Bundestag Drucksache Ingestion

## Overview

Flow 5c collects German parliamentary documents (Drucksachen) from the DIP API, including bills, motions, reports, and inquiries. Provides optional PDF download with full-text extraction and creates a comprehensive knowledge graph with relationships to Vorgänge and Wahlperioden.

### Purpose

- Ingest parliamentary documents from the German Bundestag
- Download and store PDF documents with structured directory organization
- Extract full text content page-by-page using PyPDF
- Build semantic relationships linking documents to legislative procedures
- Enable document-level search and analysis

### Key Features

- **Flexible Processing Modes**: Metadata-only (fast) vs. Full-text extraction (comprehensive)
- **Structured Storage**: Organized directory layout by Wahlperiode for PDFs and markdown
- **Page-Level Extraction**: Individual page text extraction with structured headers
- **Concurrent Downloads**: Controlled parallel PDF downloads with configurable limits
- **SSL Bypass**: Built-in certificate verification bypass for Bundestag API
- **Relationship Creation**: Automatic linking to Vorgang and Wahlperiode entities
- **Batch Processing**: Efficient processing with configurable batch sizes

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
   - Optional: PDF download
   - Optional: Page-by-page text extraction
         ↓
   Neo4j MERGE Operations
         ↓
   Relationship Creation:
   - BELONGS_TO (Wahlperiode)
   - DOCUMENT_FOR (Vorgang)
         ↓
   Knowledge Graph + File Storage
```

## Data Model

### Primary Entity: `Drucksache`

**Unique Identifier**: `drucksache_id` (from DIP API)

**Core Fields**:
- `drucksache_id`: Unique identifier from DIP
- `drucksache_nummer`: Document number (e.g., "20/1234")
- `titel`: Document title
- `dokumentart`: Document type (Gesetzentwurf, Antrag, etc.)
- `dokumentnummer`: Sequential document number
- `wahlperiode`: Electoral period number
- `datum`: Publication date
- `aktualisiert`: Last updated timestamp
- `herausgeber`: Publisher (typically "BT - Bundestag")
- `typ`: Entity type (always "Drucksache")

**Content Fields**:
- `abstract`: Document summary/abstract
- `fundstelle`: Citation information (JSON)
- `dokument_url`: URL to PDF document
- `urheber`: Originators/authors (JSON)
- `autoren_anzahl`: Number of authors
- `autoren_anzeige`: Author display string

**Classification Fields**:
- `ressort`: Responsible ministry/department (list)
- `initiative`: Initiating body (list) - Bundesregierung, Bundesrat, etc.
- `vorgang_ids_json`: Related Vorgang IDs (JSON) - for relationship creation

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
| `f.datum.start` | string | Start date (YYYY-MM-DD) | `"2024-01-01"` |
| `f.datum.end` | string | End date (YYYY-MM-DD) | `"2024-12-31"` |
| `format` | string | Response format | `"json"` |
| `cursor` | string | Pagination cursor | Auto-managed |

### Dokumentart Options

- **Gesetzentwurf**: Bill/draft law
- **Antrag**: Motion/proposal
- **Bericht**: Report
- **Kleine Anfrage**: Minor inquiry/question
- **Große Anfrage**: Major inquiry
- **Beschlussempfehlung**: Committee recommendation
- **Alle**: All document types

### SSL Configuration

```python
# Built-in SSL bypass for Bundestag API
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

## Storage Structure

### Directory Layout

```
data/input/bundestag/drucksache/
├── pdf/
│   ├── wahlperiode_19/
│   │   ├── 19_1.pdf
│   │   ├── 19_2.pdf
│   │   └── ...
│   ├── wahlperiode_20/
│   │   ├── 20_1.pdf
│   │   ├── 20_1234.pdf
│   │   └── ...
│   └── wahlperiode_21/
│       └── ...
└── markdown/
    ├── wahlperiode_19/
    │   ├── 19_1.md
    │   ├── 19_2.md
    │   └── ...
    ├── wahlperiode_20/
    │   ├── 20_1.md
    │   ├── 20_1234.md
    │   └── ...
    └── wahlperiode_21/
        └── ...
```

### File Naming Convention

- **Drucksache Number**: `20/1234` (API format)
- **PDF Filename**: `20_1234.pdf` (forward slash → underscore)
- **Markdown Filename**: `20_1234.md`

### Markdown Format

```markdown
---
drucksache_nummer: 20/1234
wahlperiode: 20
page_count: 25
pages_with_content: 24
total_characters: 45678
extraction_date: 2025-01-15T10:30:00.000000
---

# Drucksache 20/1234

## Page 1

[Page 1 text content...]

---

## Page 2

[Page 2 text content...]

---

...
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
   - **Job Name**: Descriptive name (e.g., "WP 20 Gesetzentwürfe")
   - **Wahlperiode**: Comma-separated periods (e.g., "20" or "19,20,21")
   - **Dokumentart**: Filter by type or "Alle" for all
   - **Start/End Date**: Optional date range filters (YYYY-MM-DD)
   - **Batch Size**: Processing batch size (10-500)
   - **Maximum Documents**: Total documents to collect (1-10000)
   - **Extract Full Text**: Enable/disable PDF download and text extraction
   - **Max Concurrent Downloads**: Limit parallel downloads (1-10)
   - **Create Relationships**: Enable/disable relationship creation

3. **Submit**: Click "Start Collection"

4. **Monitor Progress**: Real-time updates via Kodosumi tracer

### Programmatic Usage

```python
from src.flows.bundestag_drucksache.processor import process_drucksache_batch

inputs = {
    "job_name": "WP 20 Bills",
    "wahlperioden": "20",
    "dokumentart": "Gesetzentwurf",
    "batch_size": 100,
    "max_drucksachen": 500,
    "extract_full_text": True,
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
   UNWIND apoc.convert.fromJsonList(d.vorgang_ids_json) as vorgang_id
   MATCH (v:Vorgang {vorgang_id: vorgang_id})
   MERGE (d)-[:DOCUMENT_FOR]->(v)
   ```
   **Note**: Requires APOC for JSON parsing

### Relationship Dependencies

- **Wahlperiode nodes**: Must exist before creating BELONGS_TO relationships (run Flow 5g)
- **Vorgang nodes**: Must exist before creating DOCUMENT_FOR relationships (run Flow 5b)

## Field Mapping Logic

### Drucksache Entity Mapping

```python
def map_drucksache_to_entity(api_data: Dict) -> Dict:
    """
    Maps DIP API response to Neo4j entity structure.

    Key transformations:
    - String fields with safe_str() for null handling
    - Date fields with safe_date() for ISO format
    - Lists with safe_list() for array normalization
    - JSON serialization for complex nested objects
    """
    entity = {
        "drucksache_id": safe_str(api_data.get("id")),
        "drucksache_nummer": safe_str(api_data.get("drucksachetyp")),
        "titel": safe_str(api_data.get("titel", "")),
        "dokumentart": safe_str(api_data.get("dokumentart", "")),
        "wahlperiode": safe_int(api_data.get("wahlperiode")),
        "datum": safe_date(api_data.get("datum")),
        # ... additional fields
    }
    return entity
```

### PDF Processing Pipeline

```python
# Step 1: Download PDF with retry and exponential backoff
pdf_bytes = await pdf_handler.download_pdf(pdf_url, max_retries=3)

# Step 2: Extract pages with PyPDF
pages = pdf_handler.extract_pages_from_pdf(pdf_bytes)
# Returns: [{"page_number": 1, "page_text": "...", "char_count": 1234}, ...]

# Step 3: Generate markdown with frontmatter
markdown_content = pdf_handler.generate_markdown(
    drucksache_nummer="20/1234",
    wahlperiode=20,
    pages=pages
)

# Step 4: Save to file system
storage_manager.save_pdf(drucksache_nummer, wahlperiode, pdf_bytes)
storage_manager.save_markdown(drucksache_nummer, wahlperiode, markdown_content)
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
      DRUCKSACHE_STORAGE_PATH: ./data/input/bundestag/drucksache
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

CREATE INDEX drucksache_titel_idx IF NOT EXISTS
FOR (n:Drucksache) ON (n.titel)
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
MATCH (v:Vorgang {vorgang_id: "12345"})
MATCH (d:Drucksache)-[:DOCUMENT_FOR]->(v)
RETURN d.drucksache_nummer, d.titel, d.dokumentart, d.datum
ORDER BY d.datum
```

### Find all inquiries by date range
```cypher
MATCH (d:Drucksache)
WHERE d.dokumentart IN ["Kleine Anfrage", "Große Anfrage"]
  AND d.datum >= date("2024-01-01")
  AND d.datum <= date("2024-12-31")
RETURN d.drucksache_nummer, d.titel, d.datum, d.dokumentart
ORDER BY d.datum DESC
```

### Find documents by initiator
```cypher
MATCH (d:Drucksache)
WHERE ANY(init IN d.initiative WHERE init CONTAINS "Bundesregierung")
RETURN d.drucksache_nummer, d.titel, d.initiative
ORDER BY d.datum DESC
LIMIT 20
```

### Find documents by ministry
```cypher
MATCH (d:Drucksache)
WHERE ANY(res IN d.ressort WHERE res CONTAINS "Gesundheit")
RETURN d.drucksache_nummer, d.titel, d.ressort, d.datum
ORDER BY d.datum DESC
```

### Full-text search in extracted documents
```cypher
// Note: Requires full-text index on extracted content
// This is a placeholder for search integration
CALL db.index.fulltext.queryNodes("drucksache_fulltext", "Digitalisierung")
YIELD node, score
RETURN node.drucksache_nummer, node.titel, score
ORDER BY score DESC
LIMIT 10
```

## Performance

### Typical Metrics

**Metadata-Only Mode (Fast)**:
- **Collection Speed**: 100-200 documents/minute
- **Entity Creation**: ~2-3 seconds per batch of 100
- **Memory Usage**: ~500MB for 1000 documents
- **Network**: ~1-2 API requests/second

**Full-Text Extraction Mode (Comprehensive)**:
- **Collection Speed**: 10-20 documents/minute
- **PDF Download**: 5-30 seconds per document (size dependent)
- **Text Extraction**: 2-5 seconds per document
- **Memory Usage**: ~2-4GB for concurrent processing
- **Storage**: ~2-5MB per PDF document
- **Concurrency**: 5-10 simultaneous downloads recommended

### Processing Time Estimates

| Configuration | Documents | Metadata Only | With Full-Text |
|---------------|-----------|---------------|----------------|
| 100 docs | Single WP | ~1 minute | ~8-12 minutes |
| 500 docs | Single WP | ~3-5 minutes | ~35-50 minutes |
| 1000 docs | Single WP | ~7-10 minutes | ~70-100 minutes |
| 10000 docs | Multiple WP | ~60-90 minutes | ~10-15 hours |

### Optimization Tips

1. **Start with Metadata**: Collect metadata first, then run selective full-text extraction
2. **Batch Size**: Use 100-200 for optimal throughput
3. **Concurrent Downloads**: 5-10 simultaneous downloads balances speed and memory
4. **Filter by Type**: Collect specific Dokumentart types first (e.g., "Gesetzentwurf")
5. **Date Ranges**: Use date filters to limit collection scope
6. **Wahlperiode Focus**: Process one period at a time for better organization
7. **Skip Existing**: Check `storage_manager.pdf_exists()` to avoid re-downloads

## Troubleshooting

### Common Issues

#### 1. SSL Certificate Error
**Symptom**: `ClientConnectorCertificateError`

**Solution**: Already handled with SSL verification bypass:
```python
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

#### 2. PDF Download Timeout
**Symptom**: `asyncio.TimeoutError` during PDF download

**Solution**:
- Reduce `max_concurrent_downloads` to 2-3
- Increase timeout in `pdf_handler.py` (default: 300 seconds)
- Check network connectivity to Bundestag servers

#### 3. Empty PDF Content
**Symptom**: PDFs download but text extraction returns empty pages

**Solution**:
- Some PDFs are scanned images without text layer
- Consider OCR integration for image-based PDFs
- Check PDF validity with `pypdf.PdfReader`

#### 4. Memory Issues with Large Batches
**Symptom**: Ray actor OOM errors or system slowdown

**Solution**:
- Reduce `batch_size` to 50
- Reduce `max_concurrent_downloads` to 3
- Disable full-text extraction initially
- Increase memory allocation in config.yaml

#### 5. Missing Relationships
**Symptom**: DOCUMENT_FOR relationships not created

**Solution**:
- Ensure Vorgang nodes exist (run Flow 5b first)
- Ensure Wahlperiode nodes exist (run Flow 5g first)
- Verify APOC plugin is installed for JSON parsing
- Check relationship creation logs for errors

#### 6. File System Permission Errors
**Symptom**: `OSError` when saving PDFs or markdown

**Solution**:
- Verify write permissions for `DRUCKSACHE_STORAGE_PATH`
- Check available disk space
- Ensure directory paths are valid

## Processing Modes

### Mode 1: Metadata-Only Collection (Fast)

**Use Case**: Quick inventory of all documents, build graph structure

**Configuration**:
```python
inputs = {
    "extract_full_text": False,
    "create_relationships": True,
    "max_drucksachen": 10000
}
```

**Benefits**:
- 100+ documents/minute
- Minimal storage usage (~50KB per document in Neo4j)
- Quick graph construction
- Low memory requirements

### Mode 2: Selective Full-Text Extraction

**Use Case**: Extract specific document types or date ranges

**Configuration**:
```python
inputs = {
    "dokumentart": "Gesetzentwurf",  # Only bills
    "extract_full_text": True,
    "max_drucksachen": 500,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
}
```

**Benefits**:
- Focused document collection
- Manageable storage requirements
- Full searchable text for important documents

### Mode 3: Comprehensive Archive

**Use Case**: Complete historical archive with full text

**Configuration**:
```python
inputs = {
    "wahlperioden": "19,20,21",
    "dokumentart": "Alle",
    "extract_full_text": True,
    "max_drucksachen": 50000,
    "max_concurrent_downloads": 10
}
```

**Considerations**:
- Very slow (days for complete collection)
- Large storage requirements (hundreds of GB)
- Requires robust error handling and resumption logic

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
```

### Test PDF Processing
```python
from src.flows.bundestag_drucksache.pdf_handler import DrucksachePDFHandler
from src.flows.bundestag_drucksache.storage_manager import DrucksacheStorageManager

# Initialize components
storage = DrucksacheStorageManager()
pdf_handler = DrucksachePDFHandler(storage)

# Test PDF download and extraction
result = await pdf_handler.process_pdf(
    pdf_url="https://dserver.bundestag.de/btd/20/012/2001234.pdf",
    drucksache_nummer="20/1234",
    wahlperiode=20
)

print(f"Pages extracted: {result['page_count']}")
print(f"Total characters: {result['total_characters']}")
```

## Related Flows

- **Flow 5**: Bundestag Ingestion (main comprehensive flow)
- **Flow 5a**: Bundestag Person (MPs - for author relationships)
- **Flow 5b**: Bundestag Vorgang (legislative procedures - prerequisite for DOCUMENT_FOR relationships)
- **Flow 5g**: Bundestag Wahlperiode (electoral periods - prerequisite for BELONGS_TO relationships)
- **Flow 5h**: Bundestag Fraktion (parliamentary groups)

## Prerequisites

Before running this flow:

1. **Neo4j Constraints**: Create via Flow 5 or manually
2. **Wahlperiode Nodes**: Run Flow 5g to create electoral period nodes
3. **Vorgang Nodes** (Optional): Run Flow 5b for DOCUMENT_FOR relationships
4. **APOC Plugin**: Required for Vorgang relationship creation
5. **Storage Directory**: Ensure `DRUCKSACHE_STORAGE_PATH` exists and is writable
6. **Dependencies**: Install `pypdf` for PDF text extraction

## Example Workflows

### Workflow 1: Quick Inventory
```python
# Step 1: Collect metadata for all documents in current period
inputs = {
    "wahlperioden": "20",
    "dokumentart": "Alle",
    "extract_full_text": False,
    "max_drucksachen": 10000,
    "create_relationships": True
}
result = await process_drucksache_batch(inputs, tracer)

# Step 2: Query Neo4j to identify important documents
# Step 3: Run selective full-text extraction
```

### Workflow 2: Legislative Bill Analysis
```python
# Step 1: Collect all bills with full text
inputs = {
    "wahlperioden": "20",
    "dokumentart": "Gesetzentwurf",
    "extract_full_text": True,
    "max_drucksachen": 1000,
    "create_relationships": True
}

# Step 2: Extract text and build graph
result = await process_drucksache_batch(inputs, tracer)

# Step 3: Analyze bill progression via Vorgang relationships
# Step 4: Search full text for policy topics
```

### Workflow 3: Historical Archive
```python
# Step 1: Metadata collection for multiple periods
for wp in ["19", "20", "21"]:
    inputs = {
        "wahlperioden": wp,
        "dokumentart": "Alle",
        "extract_full_text": False,
        "max_drucksachen": 50000
    }
    await process_drucksache_batch(inputs, tracer)

# Step 2: Selective full-text for important document types
for dokumentart in ["Gesetzentwurf", "Große Anfrage"]:
    inputs = {
        "wahlperioden": "19,20,21",
        "dokumentart": dokumentart,
        "extract_full_text": True,
        "max_drucksachen": 5000
    }
    await process_drucksache_batch(inputs, tracer)
```

## References

- [Bundestag DIP API Documentation](https://dip.bundestag.de/documents/informationen-zur-dip-api.pdf)
- [PyPDF Documentation](https://pypdf.readthedocs.io/)
- [Neo4j MERGE Documentation](https://neo4j.com/docs/cypher-manual/current/clauses/merge/)
- [Kodosumi Flow Patterns](../../.claude/kodosumi-patterns.md)

## Changelog

### Version 1.0.0 (2025-11-13)
- Initial implementation
- Metadata collection from DIP API
- Optional PDF download with concurrent control
- Page-by-page text extraction using PyPDF
- Markdown export with YAML frontmatter
- Structured file storage by Wahlperiode
- MERGE-based deduplication
- Relationship creation (BELONGS_TO, DOCUMENT_FOR)
- SSL certificate handling
- Comprehensive documentation
