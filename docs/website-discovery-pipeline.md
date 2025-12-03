# Website Content Discovery & Collection Pipeline

## Overview

The Website Content Discovery Pipeline is an Airflow DAG that automatically discovers and collects relevant content (blogs, articles, news, press releases) from German government and political websites. It filters content for relevance based on `client.yaml` configuration and saves articles as markdown files for downstream Graphiti ingestion.

## Target Websites

| Site Key | Domain | Description |
|----------|--------|-------------|
| `bundesregierung` | bundesregierung.de | Federal Government |
| `bmjv` | bmj.de | Ministry of Justice |
| `cdu` | cdu.de | CDU Party |
| `bsw` | bsw-vg.de | BSW Party |
| `bmwk` | bmwk.de | Ministry of Economic Affairs |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Airflow DAG (Daily at 6 AM)                  │
├─────────────────────────────────────────────────────────────────┤
│  1. Load Config     → websites.yaml + client.yaml              │
│  2. Discovery       → RSS → Section → Sitemap (per site)       │
│  3. Deduplicate     → URL hash against state file              │
│  4. Filter          → Keyword (fast) + LLM (optional)          │
│  5. Extract         → Full content via URLToMarkdownConverter  │
│  6. Transform       → MarkdownTransformer with frontmatter     │
│  7. Save            → data/input/website/YYYY-MM/*.md          │
│  8. Update State    → Mark URLs as processed                   │
│  9. Auto-trigger    → Optional: Trigger Flow 1 ingestion       │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
src/etl/
├── dags/
│   └── website_discovery_dag.py        # Main Airflow DAG
│
├── collectors/
│   └── website_discovery/              # Discovery module
│       ├── __init__.py
│       ├── base.py                     # BaseDiscoveryStrategy ABC
│       ├── models.py                   # Data models
│       ├── rss_strategy.py             # RSS feed discovery (priority 1)
│       ├── section_strategy.py         # Section crawling (priority 2)
│       ├── sitemap_strategy.py         # Sitemap parsing (priority 3)
│       ├── orchestrator.py             # Strategy orchestration
│       └── rate_limiter.py             # Polite crawling utilities
│
├── filtering/                          # Relevance filtering
│   ├── __init__.py
│   ├── keyword_scorer.py               # Fast keyword-based scoring
│   ├── llm_analyzer.py                 # Optional LLM analysis
│   └── relevance_filter.py             # Hybrid filter logic
│
├── config/
│   └── websites.yaml                   # Site-specific configuration
│
└── utils/
    └── url_deduplication.py            # URL dedup with persistence

data/
├── state/
│   └── website_discovery_state.json    # Persistent discovery state
└── input/
    └── website/
        └── YYYY-MM/                    # Monthly subdirectories
            └── *.md                    # Collected articles
```

## Discovery Strategies

The pipeline uses three discovery strategies in priority order with automatic fallback:

### 1. RSS Discovery (Priority 1)

**Best for:** Sites with well-maintained RSS/Atom feeds

```yaml
- type: rss
  priority: 1
  config:
    feeds:
      - url: https://www.bundesregierung.de/breg-de/service/rss
        category: general
    max_items_per_feed: 50
```

**Features:**
- Parses RSS 2.0 and Atom feeds
- Extracts title, description, published date, author
- Cleanest data source with reliable metadata

### 2. Section Discovery (Priority 2)

**Best for:** Sites without RSS but with structured news sections

```yaml
- type: section
  priority: 2
  config:
    sections:
      - path: /breg-de/aktuelles
        name: Aktuelles
        depth: 2
    follow_pagination: true
    max_pages: 10
```

**Features:**
- Crawls specified website sections
- Follows pagination links
- Extracts article links from listing pages
- Handles German date formats

### 3. Sitemap Discovery (Priority 3)

**Best for:** Fallback when RSS and sections unavailable

```yaml
- type: sitemap
  priority: 3
  config:
    sitemap_url: https://www.bundesregierung.de/sitemap.xml
    include_patterns:
      - "/breg-de/aktuelles/*"
    exclude_patterns:
      - "*.pdf"
    max_urls: 500
```

**Features:**
- Parses XML sitemaps and sitemap indexes
- Supports Google News sitemap extension
- Pattern-based URL filtering

## Relevance Filtering

### Scoring Dimensions

Content is scored across 5 dimensions using keywords from `client.yaml`:

| Dimension | Weight | Source Fields |
|-----------|--------|---------------|
| Direct Impact | 40% | `direct_impact_keywords` |
| Industry Relevance | 25% | `core_industries`, `topic_patterns` |
| Geographic Relevance | 15% | `primary_markets`, `secondary_markets` |
| Temporal Urgency | 10% | Date indicators, deadlines |
| Strategic Alignment | 10% | `strategic_themes` |

### Decision Thresholds

```
Score >= 70  →  RELEVANT (high confidence)
Score <= 30  →  NOT_RELEVANT (low confidence)
30 < Score < 70  →  UNCERTAIN (use LLM if enabled)
```

### Hybrid Filtering Flow

```
                    ┌──────────────┐
                    │   Article    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Keyword    │
                    │   Scoring    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        Score >= 70   30-70 Score   Score <= 30
              │            │            │
              ▼            ▼            ▼
          RELEVANT    ┌────────┐   NOT_RELEVANT
                      │  LLM?  │
                      └────┬───┘
                           │
                    ┌──────┴──────┐
                    │             │
                 Enabled      Disabled
                    │             │
                    ▼             ▼
               LLM Analysis   UNCERTAIN
                    │        (include if
                    ▼         configured)
              RELEVANT/
            NOT_RELEVANT
```

## Configuration

### websites.yaml

```yaml
websites:
  bundesregierung:
    domain: bundesregierung.de
    name: Bundesregierung
    language: de
    enabled: true
    discovery_strategies:
      - type: rss
        priority: 1
        config:
          feeds:
            - url: https://www.bundesregierung.de/breg-de/service/rss
              category: general
          max_items_per_feed: 50
      - type: section
        priority: 2
        config:
          sections:
            - path: /breg-de/aktuelles
              name: Aktuelles
              depth: 2

discovery_settings:
  request_delay_seconds: 1.5
  max_concurrent_requests: 3
  request_timeout_seconds: 30
  user_agent: "PolicyTracker/1.0 (Political Monitoring Research)"
  respect_robots_txt: true

filtering:
  strategy: hybrid  # keyword_only | llm_only | hybrid
  keyword_filter:
    min_keyword_matches: 1
    additional_keywords:
      - politik
      - gesetz
      - regulierung
  llm_filter:
    enabled: false
    model: gpt-4o-mini
    relevance_threshold: 50.0

deduplication:
  strategy: url_hash
  state_file: data/state/website_discovery_state.json
  lookback_days: 90
```

### client.yaml (Relevance Keywords)

```yaml
company_terms:
  - zalando

core_industries:
  - e-commerce
  - online retail
  - fashion

primary_markets:
  - european union
  - germany
  - france

strategic_themes:
  - digital transformation
  - sustainability
  - data privacy

direct_impact_keywords:
  - must comply
  - required to
  - obligation
  - penalty

topic_patterns:
  data-protection:
    - gdpr
    - data privacy
  ecommerce-regulation:
    - digital services act
    - dsa
```

## Output Format

Articles are saved to `data/input/website/YYYY-MM/` with YAML frontmatter:

```markdown
---
title: Kabinett beschließt neue Digitalstrategie
url: https://bundesregierung.de/breg-de/aktuelles/...
published_date: 2024-11-15
collected_date: 2024-11-15T06:35:00
source: bundesregierung.de
description: Das Bundeskabinett hat heute...
language: de
collection_type: website_discovery
discovery_method: rss
---

# Kabinett beschließt neue Digitalstrategie

[Full German content preserved as-is]
```

## Usage

### Running the DAG

The DAG runs automatically daily at 6 AM. To trigger manually:

```bash
# Via Airflow CLI
airflow dags trigger website_discovery_collection

# Via Airflow UI
# Navigate to DAGs → website_discovery_collection → Trigger
```

### Programmatic Usage

```python
import asyncio
from src.etl.collectors.website_discovery import (
    SiteConfig,
    StrategyOrchestrator,
    RateLimiter,
)

# Create site configuration
site_config = SiteConfig(
    site_key="bundesregierung",
    domain="bundesregierung.de",
    name="Bundesregierung",
    discovery_strategies=[
        {
            "type": "rss",
            "priority": 1,
            "config": {
                "feeds": [{"url": "https://bundesregierung.de/rss"}]
            }
        }
    ]
)

# Create orchestrator
orchestrator = StrategyOrchestrator(site_config=site_config)

# Discover content
async def discover():
    result = await orchestrator.discover_content(limit=50)
    print(f"Discovered {len(result.articles)} articles")
    for article in result.articles:
        print(f"  - {article.title}")
    await orchestrator.close()

asyncio.run(discover())
```

### Using the Keyword Scorer

```python
from src.etl.filtering import KeywordScorer
import yaml

# Load client config
with open("data/context/client.yaml") as f:
    client_config = yaml.safe_load(f)

# Create scorer
scorer = KeywordScorer(client_config=client_config)

# Score content
breakdown = scorer.score_content(
    title="New GDPR Enforcement in EU E-Commerce",
    content="Companies must comply with new regulations..."
)

print(f"Total Score: {breakdown.weighted_total}")
print(f"Direct Impact: {breakdown.direct_impact}")
print(f"Matched Keywords: {breakdown.all_matched_keywords}")
```

### Using the Relevance Filter

```python
from src.etl.filtering import RelevanceFilter, FilterConfig

# Create filter
filter_config = FilterConfig(
    strategy="hybrid",
    llm_enabled=False,
    high_confidence_threshold=70.0,
    low_confidence_threshold=30.0,
)

relevance_filter = RelevanceFilter(
    client_config=client_config,
    config=filter_config,
)

# Filter content
async def filter_article():
    result = await relevance_filter.filter_content(
        title="EU Digital Services Act Update",
        content="New compliance requirements for platforms..."
    )
    print(f"Decision: {result.decision.value}")
    print(f"Score: {result.final_score}")

asyncio.run(filter_article())
```

## Rate Limiting & Politeness

The pipeline implements polite crawling:

- **Request Delay**: 1.5 seconds between requests (configurable)
- **Concurrent Requests**: Max 3 simultaneous requests
- **Robots.txt**: Respected by default
- **Exponential Backoff**: On errors, delay increases
- **Per-Domain Tracking**: Separate rate limits per site

```python
from src.etl.collectors.website_discovery import RateLimiter, RateLimiterConfig

rate_limiter = RateLimiter(RateLimiterConfig(
    request_delay_seconds=1.5,
    max_concurrent_requests=3,
    respect_robots_txt=True,
))
```

## URL Deduplication

URLs are tracked across runs to prevent reprocessing:

```python
from src.etl.utils.url_deduplication import URLDeduplicator

with URLDeduplicator(state_file="data/state/discovery_state.json") as dedup:
    # Check if URL was processed
    if not dedup.is_processed(url):
        # Process article...
        dedup.mark_processed(url, source="bundesregierung.de")

    # Filter new URLs from a list
    new_urls = dedup.filter_new_urls(all_urls)

    # Cleanup old entries (>90 days)
    dedup.cleanup_old_entries(days=90)
```

## Testing

Run the test suite:

```bash
# All tests
pytest tests/etl/collectors/website_discovery/ -v

# Specific test file
pytest tests/etl/collectors/website_discovery/test_keyword_scorer.py -v

# With coverage
pytest tests/etl/collectors/website_discovery/ --cov=src/etl/collectors/website_discovery
```

## Environment Variables

```bash
# Optional - for LLM filtering
OPENAI_API_KEY=sk-...

# Required for Airflow
PYTHONPATH=.
AIRFLOW_HOME=/opt/airflow
```

## Monitoring & Troubleshooting

### Check DAG Status

```bash
# View recent runs
airflow dags list-runs -d website_discovery_collection

# View task logs
airflow tasks logs website_discovery_collection discover_all_sites 2024-01-15
```

### Common Issues

1. **No articles discovered**
   - Check if RSS feeds are accessible
   - Verify section URLs exist
   - Review robots.txt restrictions

2. **All articles filtered out**
   - Lower `low_confidence_threshold` in filtering config
   - Add more keywords to `additional_keywords`
   - Enable `include_uncertain: true`

3. **Rate limiting errors**
   - Increase `request_delay_seconds`
   - Reduce `max_concurrent_requests`

4. **Duplicate articles**
   - Check state file exists and is writable
   - Verify `lookback_days` is appropriate

### View Deduplication State

```python
import json

with open("data/state/website_discovery_state.json") as f:
    state = json.load(f)

print(f"URLs tracked: {len(state['processed_urls'])}")
print(f"Last run: {state['last_run']}")
print(f"Total saved: {state['total_saved']}")
```

## Integration with Flow 1

When `ENABLE_AUTO_TRIGGER_FLOW1=true`, the pipeline automatically triggers the Flow 1 orchestration DAG after saving new documents:

```
website_discovery_dag → (saves markdown files) → triggers → flow_orchestration_dag
                                                                    ↓
                                                            Graphiti ingestion
```

## Adding New Websites

1. Add site configuration to `websites.yaml`:

```yaml
websites:
  new_site:
    domain: example.de
    name: Example Site
    language: de
    enabled: true
    discovery_strategies:
      - type: rss
        priority: 1
        config:
          feeds:
            - url: https://example.de/rss.xml
```

2. Test discovery:

```python
from src.etl.collectors.website_discovery import create_orchestrator_from_yaml
import yaml

with open("src/etl/config/websites.yaml") as f:
    config = yaml.safe_load(f)

orchestrator = create_orchestrator_from_yaml("new_site", config)
result = await orchestrator.discover_content(limit=10)
```

3. Enable in DAG (site will be auto-included if `enabled: true`)

## Performance Considerations

- **RSS is fastest**: Prioritize RSS feeds when available
- **Section crawling**: Limit `max_pages` to avoid deep crawls
- **Sitemap**: Use `include_patterns` to filter relevant URLs early
- **Batch processing**: Articles are processed sequentially to respect rate limits
- **State cleanup**: Run `cleanup_old_entries()` periodically to manage state file size
