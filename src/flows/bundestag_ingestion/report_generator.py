"""
Report Generator for Bundestag Ingestion Flow

Formats execution results into comprehensive Markdown reports with statistics,
data quality metrics, and actionable next steps.
"""

from datetime import datetime
from typing import Any


def generate_execution_report(results: dict[str, Any]) -> str:
    """
    Generate comprehensive execution report from ingestion results.

    Args:
        results: Dictionary containing execution results with:
            - job_name: Name of the ingestion job
            - start_time: Job start timestamp
            - end_time: Job end timestamp
            - duration_seconds: Total execution time
            - collections: Dict of collected data by type
            - entities_created: Total entities created
            - edges_created: Total edges/relationships created
            - errors: List of error messages

    Returns:
        Markdown-formatted report string
    """

    job_name = results.get("job_name", "Bundestag Data Import")
    start_time = results.get("start_time", datetime.now())
    end_time = results.get("end_time", datetime.now())
    duration = results.get("duration_seconds", 0)
    collections = results.get("collections", {})
    entities_created = results.get("entities_created", 0)
    edges_created = results.get("edges_created", 0)
    errors = results.get("errors", [])

    # Calculate success rate
    total_collections = len(collections)
    successful_collections = sum(1 for c in collections.values() if c.get("status") == "success")
    success_rate = (
        (successful_collections / total_collections * 100) if total_collections > 0 else 0
    )

    # Calculate total items collected
    total_items_collected = sum(c.get("collected", 0) for c in collections.values())

    # Build report
    report = f"""# {job_name} - Execution Report

## Summary

**Status:** {"Success" if success_rate >= 80 else "Partial Success" if success_rate >= 50 else "Failed"}
**Execution Time:** {duration:.1f} seconds
**Start Time:** {start_time.strftime("%Y-%m-%d %H:%M:%S")}
**End Time:** {end_time.strftime("%Y-%m-%d %H:%M:%S")}

### Overall Statistics

| Metric | Value |
|--------|-------|
| Data Sources Collected | {successful_collections} / {total_collections} |
| Success Rate | {success_rate:.1f}% |
| Total Items Collected | {total_items_collected:,} |
| Entities Created | {entities_created:,} |
| Relationships Created | {edges_created:,} |
| Errors | {len(errors)} |

---

## Data Collection Breakdown

"""

    # Add detailed breakdown by data type
    for data_type, collection_result in collections.items():
        status = collection_result.get("status", "unknown")
        collected = collection_result.get("collected", 0)
        status_icon = "✅" if status == "success" else "❌"

        report += f"\n### {status_icon} {data_type.capitalize()}\n"
        report += f"- **Status:** {status}\n"
        report += f"- **Items Collected:** {collected:,}\n"

        if status != "success" and "error" in collection_result:
            report += f"- **Error:** {collection_result['error']}\n"

    # Data quality metrics
    report += "\n---\n\n## Data Quality Metrics\n\n"

    if entities_created > 0:
        avg_entities_per_source = entities_created / max(successful_collections, 1)
        report += f"- **Average Entities per Source:** {avg_entities_per_source:.1f}\n"

    if edges_created > 0 and entities_created > 0:
        connectivity_ratio = edges_created / entities_created
        report += f"- **Connectivity Ratio:** {connectivity_ratio:.2f} (edges per entity)\n"

    processing_rate = total_items_collected / max(duration, 1)
    report += f"- **Processing Rate:** {processing_rate:.1f} items/second\n"

    # Errors section
    if errors:
        report += "\n---\n\n## Errors and Warnings\n\n"
        for i, error in enumerate(errors, 1):
            report += f"{i}. {error}\n"

    # Data type explanations
    report += "\n---\n\n## Data Types Explained\n\n"
    report += """
| Data Type | Description | Typical Count |
|-----------|-------------|---------------|
| **Vorgang** | Legislative processes and procedures | 100-1000 |
| **Drucksache** | Printed parliamentary documents | 100-1000 |
| **Vorgangsposition** | Detailed positions within processes | 500-5000 |
| **Aktivitaet** | Parliamentary activities and actions | 100-1000 |
| **Plenarprotokoll** | Transcripts of parliamentary sessions | 50-500 |
| **Person** | Members of parliament and other persons | 500-1000 |
| **Wahlperiode** | Election periods (reference data) | 5-10 |
| **Fraktion** | Parliamentary groups (reference data) | 5-10 |
"""

    # Next steps
    report += "\n---\n\n## Next Steps\n\n"

    if success_rate >= 80:
        report += """
### Explore the Data

1. **Neo4j Browser** - Query and visualize the knowledge graph
   - URL: http://localhost:7474
   - Example: `MATCH (v:Vorgang) RETURN v LIMIT 25`

2. **Chat Interface** - Ask natural language questions
   - URL: http://localhost:3000
   - Example: "What legislative processes are active in Wahlperiode 20?"

3. **Build Communities** - Detect policy clusters
   - Command: `just build-communities`
   - Identifies related legislative topics and actors

### Sample Queries

```cypher
// Find recent legislative processes
MATCH (v:Vorgang)
WHERE v.wahlperiode = "20"
RETURN v.titel, v.vorgangTyp, v.datum
ORDER BY v.datum DESC
LIMIT 10

// Find active politicians
MATCH (p:Person)-[:AUTHORED]->(d:Drucksache)
RETURN p.vorname, p.nachname, COUNT(d) as documents
ORDER BY documents DESC
LIMIT 10

// Explore parliamentary groups
MATCH (f:Fraktion)<-[:BELONGS_TO]-(p:Person)
RETURN f.bezeichnung, COUNT(p) as members
ORDER BY members DESC
```
"""
    else:
        report += """
### Troubleshooting

Some data collections failed. Common issues:

1. **API Rate Limiting** - Wait a few minutes and retry
2. **Network Issues** - Check internet connectivity
3. **Invalid Parameters** - Verify Wahlperiode and date filters
4. **Timeout** - Reduce max_items_per_type or batch_size

**Recommended Action:** Review errors above and retry failed collections individually.
"""

    # Footer
    report += "\n---\n\n"
    report += f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    report += "*Bundestag Data Ingestion Flow v0.2.0*\n"

    return report


def generate_error_report(error: Exception, inputs: dict[str, Any]) -> str:
    """
    Generate error report when ingestion fails catastrophically.

    Args:
        error: Exception that caused the failure
        inputs: Original form inputs

    Returns:
        Markdown-formatted error report
    """

    return f"""# Ingestion Failed

## Error Details

**Error Type:** {type(error).__name__}
**Error Message:** {str(error)}

## Job Configuration

- **Job Name:** {inputs.get('job_name', 'N/A')}
- **Wahlperiode:** {inputs.get('wahlperiode', 'N/A')}
- **Max Items:** {inputs.get('max_items_per_type', 'N/A')}

## Troubleshooting Steps

1. **Check Neo4j Connection**
   - Ensure Neo4j is running: `docker ps | grep neo4j`
   - Test connection: `http://localhost:7474`

2. **Verify API Access**
   - Check internet connectivity
   - Verify Bundestag DIP API is accessible

3. **Review Configuration**
   - Check credentials in `.env` file
   - Verify resource limits (memory, CPU)

4. **Check Logs**
   - Ray logs: `just ray-logs`
   - Container logs: `docker logs policiytracker-neo4j`

## Next Steps

- Review error message above
- Address configuration issues
- Retry with smaller dataset (reduce max_items_per_type)
- Contact support if issue persists

---

*Error report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Bundestag Data Ingestion Flow v0.2.0*
"""
