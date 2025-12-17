# Multi-Collector News DAG

## Overview

The news collection DAG supports running **multiple collectors** in a single execution, combining the benefits of different news sources:

- **DPA**: Clean, original German wire content with rich metadata
- **EXA**: Broader international coverage, more web sources
- **Apify**: RSS-based headlines and summaries

This allows you to collect comprehensive news coverage while prioritizing high-quality sources.

---

## Configuration

### Environment Variables

```bash
# Multi-collector mode: comma-separated list of collectors to run
# Order matters - first collector's articles take priority for deduplication
NEWS_COLLECTORS=dpa,exa_direct

# Single collector fallback (used if NEWS_COLLECTORS is empty/unset)
NEWS_COLLECTOR=dpa
```

### Available Collectors

| Collector | Description | API Key |
|-----------|-------------|---------|
| `dpa` | German Press Agency (DPA) wire service | `DPA_API_KEY` |
| `exa_direct` | Exa.ai direct HTTP API | `EXA_API_KEY` |
| `exa` | Exa.ai Python client | `EXA_API_KEY` |
| `apify` | Apify RSS scraper | `APIFY_API_TOKEN` |

### Configuration Examples

**Run both DPA and EXA (recommended):**
```bash
NEWS_COLLECTORS=dpa,exa_direct
```

**Run only DPA:**
```bash
NEWS_COLLECTOR=dpa
# NEWS_COLLECTORS not set or empty
```

**Run EXA first, then DPA:**
```bash
NEWS_COLLECTORS=exa_direct,dpa
```

**Run all available collectors:**
```bash
NEWS_COLLECTORS=dpa,exa_direct,apify
```

---

## How It Works

### Sequential Execution

Collectors run **sequentially** in the order specified:

```
load_client_config
       ↓
┌─────────────────────────────────┐
│  collect_all_news               │
│  ├─ Collecting from dpa...      │
│  │  ✓ 20 articles               │
│  ├─ Collecting from exa_direct..│
│  │  ✓ 45 articles               │
│  └─ Total: 65 articles          │
└─────────────────────────────────┘
       ↓
transform_to_markdown (deduplication happens here)
       ↓
mark_initialization_complete
       ↓
check_auto_trigger
```

### Deduplication Strategy

Articles are deduplicated by URL:

1. **Within DAG run**: Track `seen_urls` across all collectors
2. **Across DAG runs**: Check existing files in storage before saving
3. **Priority order**: First collector wins
   - If `NEWS_COLLECTORS=dpa,exa_direct`, DPA articles take precedence
   - If same story exists from both sources, DPA version is saved (cleaner content)

### Error Resilience

If one collector fails, others continue:

```
Collecting from dpa...
  ✓ Collected 20 articles from dpa
Collecting from exa_direct...
  ✗ Failed to collect from exa_direct: API timeout

Total collected: 20 articles (from dpa only)
```

---

## DAG Task Flow

```
load_client_config
    ↓
    Determines enabled collectors from NEWS_COLLECTORS env var
    Calculates days_back for each collector (initialization vs daily)
    ↓
collect_news_data
    ↓
    Iterates through enabled collectors sequentially
    Tags each article with _collector_type
    Aggregates all articles into single list
    ↓
transform_to_markdown
    ↓
    Deduplicates by URL (first collector wins)
    Saves articles to storage
    ↓
mark_initialization_complete
    ↓
    Marks each collector as initialized (if first run)
    ↓
check_auto_trigger → trigger_flow_orchestration or generate_summary
```

---

## Factory Functions

### `get_enabled_collectors()`

Returns list of collectors to run based on configuration.

```python
from src.etl.collectors import get_enabled_collectors

collectors = get_enabled_collectors()
# Returns: ['dpa', 'exa_direct'] if NEWS_COLLECTORS=dpa,exa_direct
# Returns: ['dpa'] if NEWS_COLLECTOR=dpa and NEWS_COLLECTORS is empty
```

**Logic:**
1. If `NEWS_COLLECTORS` is set → parse comma-separated list
2. Else → use single `NEWS_COLLECTOR` value
3. Filter to only collectors with configured API keys
4. If none available → fall back to first available collector

### `get_available_collectors()`

Returns all collectors that have API keys configured.

```python
from src.etl.collectors import get_available_collectors

available = get_available_collectors()
# Returns: ['apify', 'exa', 'exa_direct', 'dpa'] (if all keys configured)
```

---

## Initialization Tracking

Each collector is tracked independently for initialization:

```json
// data/etl_initialization.json
{
  "collectors": {
    "dpa": {
      "initialized": true,
      "initialization_date": "2025-12-17T10:30:00",
      "initialization_days": 30,
      "articles_collected": 150
    },
    "exa_direct": {
      "initialized": true,
      "initialization_date": "2025-12-17T10:35:00",
      "initialization_days": 30,
      "articles_collected": 450
    }
  }
}
```

### First Run Behavior

On first run for a collector:
- Uses `ETL_INITIALIZATION_DAYS` (default: 30 days)
- Marks collector as initialized after successful collection

### Daily Run Behavior

After initialization:
- Uses `ETL_DAILY_COLLECTION_DAYS` (default: 1-3 days)
- No initialization marking needed

### Mixed Mode

If one collector is initialized and another isn't:
- Uses maximum `days_back` across all collectors
- Only uninitialzed collectors get marked after run

---

## Log Output

### Collection Summary

```
==================================================
Collection Summary (DAILY: 3 days)
==================================================
Company: Zalando
Collectors used: ['dpa', 'exa_direct']
  - dpa: 20 articles
  - exa_direct: 45 articles
Total collected: 65 articles
==================================================
```

### Final Summary

```
============================================================
News Collection Summary
============================================================
Company: Zalando
Collection Mode: DAILY (3 days back)
Run Date: 2025-12-17

Collectors Used: dpa, exa_direct
Available Collectors: apify, exa, exa_direct, dpa

Collector Stats:
  - dpa: 20 articles
  - exa_direct: 45 articles

Results:
  - Total Collected: 65
  - Articles Saved: 58
  - Articles Failed: 0
  - Duplicates Skipped: 7
============================================================
```

---

## Docker Configuration

Ensure both env vars are passed to Airflow containers in `docker-compose.yml`:

```yaml
airflow-webserver:
  environment:
    - NEWS_COLLECTOR=${NEWS_COLLECTOR:-exa_direct}
    - NEWS_COLLECTORS=${NEWS_COLLECTORS:-}
    - DPA_API_KEY=${DPA_API_KEY}
    - EXA_API_KEY=${EXA_API_KEY}
    - APIFY_API_TOKEN=${APIFY_API_TOKEN}

airflow-scheduler:
  environment:
    - NEWS_COLLECTOR=${NEWS_COLLECTOR:-exa_direct}
    - NEWS_COLLECTORS=${NEWS_COLLECTORS:-}
    - DPA_API_KEY=${DPA_API_KEY}
    - EXA_API_KEY=${EXA_API_KEY}
    - APIFY_API_TOKEN=${APIFY_API_TOKEN}
```

---

## Testing

### 1. Restart Airflow

After changing `NEWS_COLLECTORS` in `.env`:

```bash
docker compose up -d airflow-webserver airflow-scheduler
```

### 2. Trigger DAG

Via Airflow UI or CLI:

```bash
# Via just command (if available)
just airflow-trigger-news

# Or via docker
docker exec policiytracker-airflow-scheduler airflow dags trigger news_collection
```

### 3. Check Logs

Look for multi-collector output:

```
Enabled collectors: ['dpa', 'exa_direct']
Collecting from dpa...
  ✓ Collected 20 articles from dpa
Collecting from exa_direct...
  ✓ Collected 45 articles from exa_direct
```

### 4. Verify Files

Check that articles from both collectors are saved:

```bash
ls -la data/input/news/2025-12/

# Should see files like:
# 20251217_dpa_headline-here_abc123.md
# 20251217_sourcename_headline-here_def456.md
```

---

## Backwards Compatibility

The multi-collector feature is fully backwards compatible:

| Configuration | Behavior |
|--------------|----------|
| `NEWS_COLLECTORS=dpa,exa_direct` | Runs both collectors |
| `NEWS_COLLECTORS=dpa` | Runs only DPA |
| `NEWS_COLLECTORS=` (empty) | Falls back to `NEWS_COLLECTOR` |
| `NEWS_COLLECTOR=dpa` (no NEWS_COLLECTORS) | Runs only DPA |

---

## Troubleshooting

### "No collectors available"

Check that API keys are configured:

```bash
# In .env
DPA_API_KEY=sk-...
EXA_API_KEY=...
```

And passed to Docker containers (restart Airflow after changes).

### Collector not appearing in logs

1. Verify the collector name is correct (case-insensitive)
2. Check that the API key environment variable is set
3. Ensure docker-compose.yml passes the env var

### Deduplication not working

- Deduplication is by URL
- DPA URLs are constructed from URN, so same story from DPA vs Exa will have different URLs
- Cross-collector deduplication happens within a single DAG run

### One collector failing

The DAG continues with remaining collectors. Check logs for specific error:

```
✗ Failed to collect from exa_direct: API timeout
```

---

## Files Modified

| File | Change |
|------|--------|
| `src/etl/collectors/factory.py` | Added `get_enabled_collectors()` |
| `src/etl/collectors/__init__.py` | Exported new function |
| `src/etl/dags/news_collection_dag.py` | Multi-collector support |
| `.env` | Added `NEWS_COLLECTORS` |
| `.env.template` | Added `NEWS_COLLECTORS` documentation |
| `docker-compose.yml` | Added `NEWS_COLLECTORS` env var |

---

## Related Documentation

- [DPA News Collector](DPA_NEWS_COLLECTOR.md) - DPA-specific configuration and API details
- [ETL Initialization Settings](../../.env.template) - `ETL_INITIALIZATION_DAYS` and `ETL_DAILY_COLLECTION_DAYS`

---

**Last Updated**: 2025-12-17
**Author**: Political Monitoring Agent Team
