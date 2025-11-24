"""
Report Generator for Bundestag Plenarprotokoll Ingestion (Flow 5d)

Formats collection results into comprehensive Markdown reports with statistics,
processing metrics, and actionable next steps for plenary protocol data.
"""

from datetime import datetime
from typing import Any


def generate_collection_report(results: dict[str, Any]) -> str:
    """
    Generate comprehensive collection report for Plenarprotokoll ingestion.

    Args:
        results: Dictionary containing collection results with:
            - total_protocols: Number of protocols collected
            - wahlperioden_processed: List of Wahlperiode processed
            - errors: Number of errors encountered
            - duration: Total execution time in seconds
            - fetch_full_text: Whether full text was extracted

    Returns:
        Markdown-formatted report string
    """

    total_protocols = results.get("total_protocols", 0)
    wahlperioden = results.get("wahlperioden_processed", [])
    errors = results.get("errors", 0)
    duration = results.get("duration", 0)
    fetch_full_text = results.get("fetch_full_text", False)

    # Calculate success rate
    success_rate = (
        ((total_protocols - errors) / max(total_protocols, 1)) * 100 if total_protocols > 0 else 100
    )

    # Determine status
    if success_rate >= 90:
        status = "✅ Success"
        status_class = "success"
    elif success_rate >= 70:
        status = "⚠️ Partial Success"
        status_class = "warning"
    else:
        status = "❌ Failed"
        status_class = "error"

    # Build report
    report = f"""# Bundestag Plenarprotokoll Collection Report

## Summary

**Status:** {status}
**Collection Time:** {duration:.1f} seconds ({duration/60:.1f} minutes)
**Wahlperioden:** {', '.join(map(str, wahlperioden))}
**Full Text Extraction:** {'✅ Yes' if fetch_full_text else '❌ No (Metadata only)'}

---

## Collection Statistics

| Metric | Value |
|--------|-------|
| Protocols Collected | {total_protocols:,} |
| Success Rate | {success_rate:.1f}% |
| Errors Encountered | {errors} |
| Processing Rate | {total_protocols / max(duration, 1):.2f} protocols/second |
| Collection Type | {'Full-Text Extraction' if fetch_full_text else 'Metadata Only'} |

---

## Plenarprotokoll Data Explained

### What are Plenarprotokolle?
Plenary protocols (Plenarprotokolle) are complete transcripts of German Bundestag parliamentary sessions. Each protocol contains:

- **Complete debates** - All speeches by members of parliament
- **Procedural actions** - Votes, motions, and parliamentary business
- **Agenda items** (Tagesordnungspunkte) - Structured topics discussed
- **Speaker records** - Who said what and when
- **Document references** - Links to related Drucksachen and Vorgänge

### Data Size Characteristics
- **Typical length:** 100-200 pages per protocol
- **File size:** 10-50 MB per protocol
- **Processing time:**
  - Metadata only: 5-10 seconds per protocol
  - Full text extraction: 5-10 minutes per protocol

### Current Database Status
"""

    # Add context about what's in the database
    if total_protocols > 0:
        report += f"""
The collection added **{total_protocols} protocols** to the knowledge graph. You can now:

1. **Query protocol metadata** - Date, session number, agenda items
2. **Search transcript text** - Full-text search across debates (if full text was extracted)
3. **Explore relationships** - Links to Vorgänge, Drucksachen, and speakers
4. **Analyze temporal patterns** - Track policy discussions over time
"""
    else:
        report += """
No protocols were collected. This may be due to:
- All protocols for the selected Wahlperiode already exist in the database
- Date filters excluded all available protocols
- API connection issues
"""

    report += """
---

## Next Steps

"""

    if success_rate >= 90:
        report += """
### Explore the Collected Data

1. **Neo4j Browser** - Visualize plenary protocols in the graph
   - URL: http://localhost:7474
   - Username: neo4j / Password: password123

   ```cypher
   // Find recent plenary sessions
   MATCH (p:Plenarprotokoll)
   RETURN p.sitzungsnummer, p.datum, p.wahlperiode
   ORDER BY p.datum DESC
   LIMIT 10
   ```

2. **Chat Interface** - Ask questions about parliamentary debates
   - URL: http://localhost:3000
   - Example: "What was discussed in the most recent plenary session?"

3. **Explore Agenda Items**
   ```cypher
   // Find protocols with specific agenda items
   MATCH (p:Plenarprotokoll)
   WHERE p.datum >= "2024-01-01"
   RETURN p.sitzungsnummer, p.datum,
          size(p.tagesordnungspunkte) as agenda_items
   ORDER BY p.datum DESC
   ```

4. **Link to Legislative Processes**
   ```cypher
   // Find connections to Vorgänge
   MATCH (p:Plenarprotokoll)-[:REFERENCES_VORGANG]->(v:Vorgang)
   RETURN p.sitzungsnummer, p.datum,
          v.titel as vorgang_title
   LIMIT 20
   ```

### Extract More Data
"""

        if not fetch_full_text:
            report += """
⚠️ **Full-text extraction was not enabled**. To extract complete transcript text:

1. Run Flow 5d again with **"Fetch Full Transcript Text"** checked
2. Use selective date ranges to limit processing time
3. Consider overnight processing for large batches (25-50 hours for all 305 protocols)

**Benefits of full-text extraction:**
- Semantic search across parliamentary speeches
- Speaker attribution and quote extraction
- Topic modeling and debate analysis
- Full-text search for specific keywords
"""

        report += """
### Expand Coverage

To collect more protocols:
- **Different Wahlperiode:** Try WP 19, 20, or 21
- **Different date ranges:** Focus on specific time periods
- **Incremental collection:** Add new protocols as they're published
"""

    else:
        report += f"""
### Troubleshooting

The collection encountered {errors} error(s). Common issues:

1. **API Rate Limiting**
   - The Bundestag DIP API may have rate limits
   - Solution: Wait 5-10 minutes and retry

2. **Network Timeout**
   - Large protocols may timeout during download
   - Solution: Reduce batch_size or disable full-text extraction

3. **Neo4j Connection Issues**
   - Check Neo4j is running: `docker ps | grep neo4j`
   - Test connection: http://localhost:7474

4. **Memory Issues**
   - Full-text extraction is memory-intensive
   - Solution: Process in smaller batches or disable full text

### Recommended Action

Review the error messages in the execution log and:
- Retry with smaller batch sizes
- Disable full-text extraction for initial metadata collection
- Check Neo4j and network connectivity
"""

    # Performance insights
    report += """
---

## Performance Insights

"""

    if fetch_full_text:
        report += f"""
**Full-text extraction was enabled** - This significantly increases processing time.

- **Actual rate:** {total_protocols / max(duration/60, 1):.1f} protocols/minute
- **Estimated time for all 305 protocols:** {305 * duration / max(total_protocols, 1) / 3600:.1f} hours

**Recommendation:** For initial data collection, disable full-text extraction to quickly populate metadata. Add full text later for specific protocols of interest.
"""
    else:
        report += f"""
**Metadata-only collection** - Fast and efficient for initial data loading.

- **Actual rate:** {total_protocols / max(duration, 1):.1f} protocols/second
- **Estimated time for all 305 protocols:** {305 * duration / max(total_protocols, 1):.1f} seconds ({305 * duration / max(total_protocols, 1) / 60:.1f} minutes)

**Next step:** Use selective full-text extraction for specific protocols relevant to your analysis.
"""

    # Data quality section
    report += """
---

## Data Quality

### Completeness Check

To verify data completeness, run these queries:

```cypher
// Count protocols by Wahlperiode
MATCH (p:Plenarprotokoll)
RETURN p.wahlperiode as WP, count(p) as protocols
ORDER BY WP DESC

// Check for protocols with full text
MATCH (p:Plenarprotokoll)
WHERE p.full_text IS NOT NULL
RETURN count(p) as protocols_with_fulltext

// Verify relationships to Vorgänge
MATCH (p:Plenarprotokoll)-[:REFERENCES_VORGANG]->(v:Vorgang)
RETURN count(DISTINCT p) as protocols_with_vorgang_links
```

### Expected Counts (as of 2024)
- **Wahlperiode 20:** ~258 protocols
- **Wahlperiode 21:** ~47 protocols
- **Total available:** ~305 protocols

"""

    # Footer
    report += f"""
---

*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Bundestag Plenarprotokoll Ingestion Flow (Flow 5d) v1.0.0*
"""

    return report


def generate_error_report(error: str) -> str:
    """
    Generate error report when collection fails.

    Args:
        error: Error message

    Returns:
        Markdown-formatted error report
    """

    return f"""# ❌ Plenarprotokoll Collection Failed

## Error Details

{error}

## Troubleshooting Steps

1. **Check Neo4j Connection**
   ```bash
   docker ps | grep neo4j
   # Should show container running on port 7687
   ```

2. **Verify Bundestag API Access**
   - Test API endpoint: https://search.dip.bundestag.de/api/v1/plenarprotokoll
   - Check internet connectivity
   - Verify API key in environment variables

3. **Review Configuration**
   - Check `.env` file for correct credentials
   - Verify Neo4j URI: `bolt://localhost:7687`
   - Ensure database name: `politicamonitoring.v2`

4. **Check Resource Availability**
   - Free disk space: Protocols are large (10-50 MB each)
   - Available memory: Full-text extraction needs 3+ GB
   - CPU availability: Check Ray dashboard at http://localhost:8265

5. **Review Logs**
   ```bash
   # Ray application logs
   just ray-logs

   # Neo4j logs
   docker logs policiytracker-neo4j

   # Flow 5d specific logs
   docker logs policiytracker-kodosumi | grep plenarprotokoll
   ```

## Common Issues and Solutions

### Issue 1: API Rate Limiting
**Symptom:** Errors mentioning 429 or "too many requests"
**Solution:** Wait 5-10 minutes and retry with smaller batch_size

### Issue 2: Memory Exhaustion
**Symptom:** Out of memory errors or container crashes
**Solution:** Disable full-text extraction or reduce batch_size to 10-20

### Issue 3: Network Timeout
**Symptom:** Timeout errors when downloading protocols
**Solution:**
- Increase timeout in configuration
- Use more reliable network connection
- Reduce concurrent requests

### Issue 4: Neo4j Connection Refused
**Symptom:** "Connection refused" to bolt://localhost:7687
**Solution:**
```bash
# Restart Neo4j
docker restart policiytracker-neo4j

# Verify it's accessible
curl http://localhost:7474
```

## Recovery Steps

1. **Check current database state**
   ```cypher
   // How many protocols do we have?
   MATCH (p:Plenarprotokoll)
   RETURN p.wahlperiode, count(p)
   ORDER BY p.wahlperiode
   ```

2. **Retry with conservative settings**
   - Set Max Protocols to 10 (quick test)
   - Disable "Fetch Full Transcript Text"
   - Use recent date range (last 30 days)

3. **Incremental approach**
   - Collect metadata first (fast)
   - Add full text later for specific protocols
   - Process one Wahlperiode at a time

## Need Help?

If the issue persists:
1. Capture the full error message from logs
2. Note your configuration (Wahlperiode, batch size, full-text setting)
3. Check system resources (memory, disk space, CPU)
4. Review similar issues in project documentation

---

*Error report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Bundestag Plenarprotokoll Ingestion Flow (Flow 5d) v1.0.0*
"""
