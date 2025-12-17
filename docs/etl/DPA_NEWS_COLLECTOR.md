# DPA News Collector

## Overview

The DPA News Collector integrates with the **dpa-IQ-Retriever API** to collect high-quality German news articles from Deutsche Presse-Agentur (DPA), Germany's leading news agency.

### Why DPA?

| Aspect | DPA | Web Scrapers (Exa, etc.) |
|--------|-----|--------------------------|
| **Content Quality** | Original wire service content, clean markdown | Contains web noise (nav links, share buttons) |
| **Metadata** | Rich professional tags (urgency, categories) | Basic metadata |
| **Language Detection** | Accurate (`de`) | Often incorrect |
| **Source** | Original source | Republished/scraped content |
| **Formatting** | Professional structure | Variable quality |

DPA is the **original source** that many German news outlets (Zeit, Spiegel, etc.) republish.

---

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# DPA News API (German press agency - dpa-IQ-Retriever)
# Get your API key from: https://article-retriever.iq.dpa-ai-hub.de/docs
DPA_API_KEY=your_dpa_api_key_here

# Set DPA as the default collector
NEWS_COLLECTOR=dpa
```

### Docker Compose

The following environment variables are passed to Airflow containers in `docker-compose.yml`:

```yaml
environment:
  - DPA_API_KEY=${DPA_API_KEY}
  - NEWS_COLLECTOR=${NEWS_COLLECTOR:-exa_direct}
```

---

## API Details

### Base URL
```
https://article-retriever.iq.dpa-ai-hub.de
```

### Authentication
- **Header**: `X-API-Key`
- **Value**: Your DPA API key

### Endpoint
```
POST /articles/relevant
```

This endpoint has "reasonable defaults for news context" and is optimized for retrieving relevant news articles.

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search term (e.g., company name) |
| `limit` | int | No | Max results per request (default: 20, max: 20 for stability) |
| `from_datetime` | datetime | No | Start of date range (ISO format) |
| `to_datetime` | datetime | No | End of date range (ISO format) |
| `response_format` | string | No | Set to `"article_objects_markdown"` for structured data |

### Response Structure

```json
{
  "context": [
    {
      "urn": "urn:newsml:dpa.com:20090101:251216-930-433311",
      "headline": "Article Title",
      "article_complete_markdown": "Full content in Markdown...",
      "article_html": "<article>...</article>",
      "version_created_at_utc": "2025-12-16T21:48:51",
      "tags": ["dnllang:de", "dpacat:wi", "medtop:09000000", ...],
      "score": 1.2336844,
      "rerank_score": null
    }
  ]
}
```

### URL Construction

DPA doesn't return direct URLs. URLs are constructed from the URN:

```
https://www.dpa-news-hub.de/archiv/detail/{urn}
```

Example:
```
https://www.dpa-news-hub.de/archiv/detail/urn:newsml:dpa.com:20090101:251201-930-363691
```

---

## Collector Implementation

### Class: `DPANewsCollector`

Location: `src/etl/collectors/dpa_news.py`

```python
class DPANewsCollector:
    """Collects news articles from dpa-IQ-Retriever API."""

    API_BASE_URL = "https://article-retriever.iq.dpa-ai-hub.de"
    DPA_NEWS_HUB_URL = "https://www.dpa-news-hub.de/archiv/detail"
    DEFAULT_MAX_ITEMS = 50  # Default with batching support
    MAX_ITEMS_PER_REQUEST = 20  # API tends to timeout with larger requests
```

### Key Methods

#### `collect_news(query, max_items, days_back, **kwargs)`

Collects news articles with automatic batching support.

**Parameters:**
- `query` (str): Search query (e.g., company name from client context)
- `max_items` (int): Maximum articles to collect (default: 50)
- `days_back` (int): How many days back to search (default: 1)

**Returns:** `list[dict]` - Normalized article dictionaries

**Batching:**
- Requests are automatically batched in groups of 20 to avoid API timeouts
- Date-based pagination fetches older articles in subsequent batches
- 2-second delay between batches to avoid rate limiting
- Deduplication by URN across batches

#### `_normalize_article(dpa_article)`

Converts DPA response format to standard article format.

**Field Mapping:**

| DPA Field | Standard Field | Notes |
|-----------|----------------|-------|
| `urn` | `dpa_id` | Unique identifier |
| `headline` | `title` | Article title |
| `article_complete_markdown` | `content` | Full markdown content |
| `version_created_at_utc` | `published_date` | ISO format timestamp |
| `tags` | `topics` | DPA category tags |
| `score` | `dpa_score` | Relevance score |
| Constructed from URN | `url` | DPA News Hub URL |
| Extract from tags | `language` | From `dnllang:xx` tag |

### Output Format

Each article is normalized to:

```python
{
    # Core fields
    "title": "Warnstreik bei Zalando in Erfurt",
    "url": "https://www.dpa-news-hub.de/archiv/detail/urn:newsml:...",
    "content": "Full markdown content...",

    # Temporal fields
    "published_date": "2025-12-01T09:40:19",
    "collected_date": "2025-12-17T06:17:46.086366",

    # Source information
    "source": "DPA",
    "source_url": "https://www.dpa.com",
    "author": "",

    # Additional metadata
    "description": "Die Gewerkschaft Verdi hat erneut...",
    "image_url": "",
    "language": "de",
    "topics": ["dnllang:de", "dpacat:wi", ...],

    # DPA specific
    "dpa_id": "urn:newsml:dpa.com:20090101:251201-930-363691",
    "dpa_score": 1.2336844,
    "dpa_rerank_score": null,

    # Raw data
    "_raw": { ... }
}
```

---

## Usage

### Via Factory

```python
from src.etl.collectors import create_news_collector

# Uses NEWS_COLLECTOR env var (or defaults to exa_direct)
collector = create_news_collector()

# Or explicitly create DPA collector
collector = create_news_collector("dpa")
```

### Direct Instantiation

```python
from src.etl.collectors.dpa_news import DPANewsCollector

collector = DPANewsCollector()
# or with explicit API key
collector = DPANewsCollector(api_key="sk-...")
```

### Collecting News

```python
import asyncio

async def collect():
    collector = DPANewsCollector()
    articles = await collector.collect_news(
        query="Zalando",
        max_items=50,
        days_back=7
    )
    return articles

articles = asyncio.run(collect())
```

### With Airflow DAG

The collector integrates with the existing `news_collection_dag.py`:

1. Set `NEWS_COLLECTOR=dpa` in `.env`
2. Restart Airflow: `docker compose up -d airflow-webserver airflow-scheduler`
3. Trigger the DAG: `just airflow-trigger-news` or via Airflow UI

---

## Batching Behavior

The DPA API tends to timeout with large requests. The collector implements smart batching:

### Example: Requesting 50 articles

```
Batch 1/3: requesting 20 items
Batch 1: collected 20 articles (total: 20)
[2 second delay]
Batch 2/3: requesting 20 items
Batch 2: collected 18 articles (total: 38)
[2 second delay]
Batch 3/3: requesting 12 items
Batch 3: collected 10 articles (total: 48)
Collected 48 total articles for query: 'Zalando'
```

### Batching Logic

1. **Batch Size**: Maximum 20 items per request
2. **Pagination**: Uses date-based pagination (searches for articles older than the oldest from previous batch)
3. **Deduplication**: Tracks seen URNs to avoid duplicates
4. **Rate Limiting**: 2-second delay between batches
5. **Early Termination**: Stops if API returns fewer items than requested

---

## DPA Tag Categories

DPA articles include rich metadata tags:

| Tag Prefix | Meaning | Example |
|------------|---------|---------|
| `dnllang:` | Language | `dnllang:de` (German) |
| `dpacat:` | Category | `dpacat:wi` (Business) |
| `dpaarea:` | Region | `dpaarea:16` (Thuringia) |
| `medtop:` | Media Topic | `medtop:09000000` (Labor) |
| `urgency:` | Priority | `urgency:4` |
| `dpauserneed:` | User Need | `dpauserneed:updateme` |

---

## Error Handling

### API Errors
- HTTP status codes are checked
- Error messages are logged with details

### Timeouts
- 120-second timeout per request
- Batching prevents server-side timeouts

### Empty Results
- Handles empty `context` array gracefully
- Stops batching when no more articles available

### Date Parsing
- Multiple date format support
- Falls back gracefully if parsing fails
- Validates dates aren't in future or too old (< 1990)

---

## Testing

### Manual API Test

```bash
curl -X POST "https://article-retriever.iq.dpa-ai-hub.de/articles/relevant" \
  -H "X-API-Key: $DPA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Zalando",
    "limit": 5,
    "response_format": "article_objects_markdown"
  }'
```

### Check Available Collectors

```python
from src.etl.collectors import get_available_collectors
print(get_available_collectors())
# ['apify', 'exa', 'exa_direct', 'dpa']
```

---

## Comparison: DPA vs Exa Output

### Same Story: "Warnstreik bei Zalando in Erfurt"

**DPA Output:**
- Clean markdown with proper `##` headers
- Accurate metadata (`language: de`)
- Rich topic tags
- No web scraping noise

**Exa Output (from Zeit.de):**
- Contains navigation noise (`[Zum Inhalt springen]`)
- Social share button links
- Wrong language detection (`language: en`)
- Actually republished DPA content (`© dpa-infocom`)

---

## Files Modified

| File | Change |
|------|--------|
| `src/etl/collectors/dpa_news.py` | New collector implementation |
| `src/etl/collectors/__init__.py` | Added try-except import |
| `src/etl/collectors/factory.py` | Added "dpa" type routing |
| `.env.template` | Added `DPA_API_KEY` documentation |
| `.env` | Added `DPA_API_KEY` with actual key |
| `docker-compose.yml` | Added DPA_API_KEY to Airflow containers |

---

## Troubleshooting

### "DPA_API_KEY not provided or found in environment"
- Ensure `DPA_API_KEY` is set in `.env`
- Ensure `docker-compose.yml` passes the key to Airflow containers
- Restart Airflow: `docker compose up -d airflow-webserver airflow-scheduler`

### "Available collectors: ['apify', 'exa', 'exa_direct']" (missing 'dpa')
- Check that `DPA_API_KEY` is passed to Docker containers
- Verify in `docker-compose.yml` under airflow-webserver and airflow-scheduler

### API Timeout (504 Gateway Timeout)
- Reduce `max_items` or rely on default batching (20 items per request)
- Batching is automatic and should prevent this

### "DPA API returned markdown string instead of article objects"
- Ensure `response_format: "article_objects_markdown"` is set in request
- This is handled automatically by the collector

---

## References

- **DPA API Documentation**: https://article-retriever.iq.dpa-ai-hub.de/docs
- **DPA News Hub**: https://www.dpa-news-hub.de/
- **DPA Website**: https://www.dpa.com/

---

**Last Updated**: 2025-12-17
**Author**: Political Monitoring Agent Team
