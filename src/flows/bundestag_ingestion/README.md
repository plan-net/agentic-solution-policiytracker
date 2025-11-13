# Bundestag Ingestion Flow v0.2.0

Kodosumi flow interface for collecting and ingesting German parliamentary data from the Bundestag DIP API into Neo4j knowledge graph.

## Overview

This is **Flow 5** in the Political Monitoring Agent system. It provides a comprehensive interface for collecting data from 8 different Bundestag DIP API endpoints and transforming it into the political schema v4 format in Neo4j.

## Architecture

### Files Structure

```
bundestag_ingestion/
├── app.py                 # Kodosumi endpoint (172 lines)
├── forms.py              # Form definitions (155 lines)
├── processor.py          # Main business logic (275 lines)
├── report_generator.py   # Output formatting (245 lines)
├── collectors/           # 8 collectors (already implemented)
│   ├── vorgang_collector.py
│   ├── drucksache_collector.py
│   ├── vorgangsposition_collector.py
│   ├── aktivitaet_collector.py
│   ├── plenarprotokoll_collector.py
│   ├── person_collector.py
│   ├── wahlperiode_builder.py
│   └── fraktion_builder.py
├── transformers/         # Entity and edge builders
│   ├── entity_builder.py
│   └── edge_builder.py
└── utils/               # Utility functions
```

### Data Sources (8 endpoints)

1. **Vorgänge** - Legislative processes and procedures
2. **Drucksachen** - Printed parliamentary documents
3. **Vorgangspositionen** - Detailed positions within processes
4. **Aktivitäten** - Parliamentary activities and actions
5. **Plenarprotokolle** - Transcripts of parliamentary sessions
6. **Personen** - Members of parliament and other persons
7. **Wahlperioden** - Election periods (reference data)
8. **Fraktionen** - Parliamentary groups (reference data)

## Features

### User Interface (forms.py)

- Checkbox selection for all 8 data types
- Wahlperiode dropdown (19, 20, 21, all)
- Max items per type (1-10000)
- Batch size configuration (10-500)
- Date range filters (optional)
- Full text content option
- Clear existing data option

### Processing Pipeline (processor.py)

1. **Initialization** - Neo4j connection and validation
2. **Reference Data Collection** - Wahlperioden and Fraktionen
3. **Parallel Collection** - Use Ray actors for concurrent API calls
4. **Entity Transformation** - Map to political schema v4
5. **Relationship Building** - Create edges between entities
6. **Reporting** - Comprehensive execution summary

### Progress Tracking

Uses `tracer.markdown()` for real-time updates:
- Connection status
- Collection progress per data type
- Entity creation counts
- Edge creation counts
- Error messages
- Timing information

### Report Generation (report_generator.py)

Produces markdown reports with:
- Summary statistics (items, entities, edges, duration)
- Breakdown by data type
- Data quality metrics (connectivity ratio, processing rate)
- Error details
- Sample Cypher queries
- Next steps and troubleshooting

## Usage

### Via Kodosumi Admin UI

1. Access: http://localhost:3370 (admin/admin)
2. Navigate to Bundestag Ingestion flow
3. Configure parameters:
   - Select data types to collect
   - Choose Wahlperiode
   - Set max items and batch size
   - Optional: date filters
4. Click "Start Collection"
5. Monitor real-time progress
6. Review execution report

### Via API

```python
import requests

response = requests.post(
    "http://localhost:8001/bundestag-ingestion",
    json={
        "job_name": "Test Import",
        "collect_vorgang": True,
        "collect_person": True,
        "wahlperiode": "20",
        "max_items_per_type": 100,
        "batch_size": 50
    }
)
```

## Configuration

### Required Environment Variables (.env)

```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=neo4j
```

### Ray Deployment (config.yaml)

```yaml
flows:
  flow5-bundestag-ingestion:
    import_path: src.flows.bundestag_ingestion.app:fast_app
    route_prefix: /bundestag-ingestion
    num_replicas: 1
    ray_actor_options:
      num_cpus: 4
      memory: 8589934592  # 8GB
```

## Performance Considerations

### Memory Usage

- **Vorgangsposition** is the largest dataset (can be 10k+ items)
- Recommended batch size: 50-100 items
- Ray actor uses 8GB memory for large imports

### Processing Time

Typical execution times:
- 100 items per type: 2-5 minutes
- 1000 items per type: 15-30 minutes
- Full import (10k+ items): 1-2 hours

### Optimization

- Use parallel collection with Ray actors
- Batch processing for Neo4j ingestion
- Skip full text if not needed (faster)
- Filter by date range to reduce dataset

## Error Handling

### Common Issues

1. **Neo4j Connection Failed**
   - Check Neo4j is running: `docker ps | grep neo4j`
   - Verify credentials in `.env`

2. **API Rate Limiting**
   - Reduce max_items_per_type
   - Increase delays between requests

3. **Memory Issues**
   - Reduce batch_size
   - Process data types separately

4. **Timeout**
   - Increase RAY_TASK_TIMEOUT
   - Reduce dataset size

### Graceful Degradation

- Failed collections don't stop other collections
- Partial results are saved
- Detailed error messages in report
- Can retry failed collections individually

## Testing

### Unit Tests

```bash
pytest tests/unit/test_bundestag_ingestion_flow.py -v
```

### Integration Tests

```bash
pytest tests/integration/test_bundestag_collection.py -v
```

### Manual Testing

```bash
# Test with minimal dataset
curl -X POST http://localhost:8001/bundestag-ingestion \
  -H "Content-Type: application/json" \
  -d '{
    "job_name": "Test",
    "collect_person": true,
    "wahlperiode": "20",
    "max_items_per_type": 10
  }'
```

## Deployment

### Local Development

```bash
# Start services
just start

# Deploy flow
just deploy-bundestag-ingestion

# Check status
just status
```

### Production

```bash
# Deploy all flows
just deploy-all

# Monitor Ray dashboard
open http://localhost:8265

# Check flow health
curl http://localhost:8001/bundestag-ingestion/health
```

## Next Steps After Ingestion

1. **Explore Data in Neo4j Browser**
   - http://localhost:7474
   - Example: `MATCH (v:Vorgang) RETURN v LIMIT 25`

2. **Query via Chat Interface**
   - http://localhost:3000
   - Ask natural language questions about German parliament

3. **Build Communities**
   - Run: `just build-communities`
   - Detect policy clusters and relationships

4. **Run Analytics**
   - Use provided Cypher queries
   - Explore network analysis tools

## Version History

- **v0.2.0** (2024-11-12) - Initial Kodosumi flow implementation
  - 8 collectors integrated
  - Ray parallel processing
  - Comprehensive reporting
  - Political schema v4 support

## References

- Bundestag DIP API: https://dip.bundestag.de/
- Political Schema v4: See `docs/schemas/political_schema_v4.md`
- Kodosumi Patterns: See `.claude/kodosumi-patterns.md`
- Flow Architecture: See `.claude/project-architecture.md`
