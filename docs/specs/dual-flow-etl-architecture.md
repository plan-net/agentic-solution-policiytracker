# Dual-Flow ETL Architecture v0.2.0

## Overview

The Political Monitoring Agent implements a comprehensive dual-flow ETL pipeline designed to collect documents from two distinct sources with different purposes, schedules, and processing requirements.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ETL ORCHESTRATION LAYER                            │
│                         (Apache Airflow)                                    │
├─────────────────────────────────┬───────────────────────────────────────────┤
│         FLOW 1: POLICY         │         FLOW 2: CLIENT NEWS              │
│      (Regulatory Landscape)     │        (Company-Specific)                │
└─────────────────────────────────┴───────────────────────────────────────────┘
┌─────────────────────────────────┬───────────────────────────────────────────┐
│ PolicyLandscapeCollector        │ ExaDirectCollector + ApifyCollector       │
│                                 │                                           │
│ • Weekly Schedule (Sundays)     │ • Daily Schedule                          │
│ • Exa.ai API                    │ • Multiple APIs                          │
│ • 33 targeted queries           │ • Client-specific queries                │
│ • EU regulatory focus           │ • Company + industry focus               │
└─────────────────────────────────┴───────────────────────────────────────────┘
┌─────────────────────────────────┬───────────────────────────────────────────┐
│ PolicyQueryGenerator            │ ClientConfigLoader                        │
│                                 │                                           │
│ • Topic patterns parsing        │ • Company terms extraction               │
│ • Market + industry combination │ • Search query generation                │
│ • Regulatory category mapping   │ • Filter configuration                   │
└─────────────────────────────────┴───────────────────────────────────────────┘
┌─────────────────────────────────┬───────────────────────────────────────────┐
│ data/input/policy/              │ data/input/news/                          │
│                                 │                                           │
│ • YYYY-MM/ structure            │ • YYYY-MM/ structure                      │
│ • Regulatory documents          │ • News articles                          │
│ • Policy analysis focus         │ • Company monitoring focus               │
└─────────────────────────────────┴───────────────────────────────────────────┘
```

## Flow 1: Policy Landscape Collection

### Purpose
Monitor the broader regulatory environment affecting the client's industry, providing comprehensive policy intelligence for strategic planning.

### Collection Strategy
- **Schedule**: Weekly (Sundays at 2 AM UTC)
- **Rationale**: Policy changes occur slowly; weekly collection captures all developments without overwhelming the system
- **Initialization**: 90 days of historical data for comprehensive policy context

### Query Generation
The PolicyQueryGenerator creates targeted searches by combining:

```yaml
# From client.yaml
topic_patterns:
  data-protection: [gdpr, data privacy, ...]
  ecommerce-regulation: [digital services act, dsa, ...]
  sustainability: [esg, environmental, ...]
  compliance: [regulatory compliance, ...]
  competition: [antitrust, competition law, ...]

primary_markets: [european union, germany, france, ...]
core_industries: [e-commerce, fashion, marketplace, ...]
```

**Query Formula**: `"{topic}" AND "{market}" AND "{industry}"`

**Example Generated Queries**:
- `"gdpr" AND "european union" AND "e-commerce"`
- `"digital services act" AND "germany" AND "marketplace"`
- `"esg" AND "france" AND "fashion"`

### Content Types Collected
- Regulatory guidance documents
- Policy implementation timelines
- Enforcement actions and penalties
- Legislative updates and amendments
- Cross-border regulatory cooperation
- Industry-specific compliance requirements

### Quality Controls
- **Query Optimization**: Limited to 33 total queries to respect API limits
- **Relevance Filtering**: Combines 3+ terms to ensure targeted results
- **Deduplication**: URL-based duplicate removal
- **Content Validation**: Full-text article extraction via Exa.ai

## Flow 2: Client News Collection

### Purpose
Track company-specific news, industry developments, and competitive intelligence for operational awareness.

### Collection Strategy
- **Schedule**: Daily (configurable timing)
- **Rationale**: News moves fast; daily collection ensures no important developments are missed
- **Initialization**: 30 days of historical data for immediate context

### Query Generation
Uses client-specific terms for focused collection:

```yaml
# From client.yaml
company_terms: [zalando, zln, zalando se]
core_industries: [e-commerce, online retail, fashion, ...]
strategic_themes: [digital transformation, sustainability, ...]
exclusion_terms: [sports, automotive, ...]  # Filter irrelevant content
```

### Content Types Collected
- Company announcements and press releases
- Industry analysis and commentary
- Competitive intelligence
- Market trends and developments
- Technology and innovation coverage
- Regulatory impact on business operations

### Multi-Source Strategy
- **Primary**: Exa.ai for high-quality, full-text articles
- **Fallback**: Apify for additional coverage and reliability
- **Factory Pattern**: Dynamic source selection based on availability

## Shared Infrastructure

### Initialization Tracking
Both flows support smart initialization:

```python
class ETLInitializationTracker:
    def is_initialized(self, collector_type: str) -> bool
    def mark_initialized(self, collector_type: str) -> None
    def get_collection_days(self, init_days: int, daily_days: int) -> int
```

**First Run Behavior**:
- Policy: Collects 90 days of historical documents
- News: Collects 30 days of historical articles
- Tracks completion in `data/etl_initialization.json`

**Subsequent Runs**:
- Policy: Collects 7 days (weekly overlap for safety)
- News: Collects 1 day (daily incremental)

### Storage Organization

```
data/input/
├── policy/           # Flow 1 output
│   ├── 2025-05/
│   │   ├── 20250527_europa-eu_dsa-guidance.md
│   │   └── 20250527_edpb_gdpr-update.md
│   └── 2025-04/...
└── news/             # Flow 2 output  
    ├── 2025-05/
    │   ├── 20250527_techcrunch_zalando-feature.md
    │   └── 20250527_reuters_ecommerce-news.md
    └── 2025-04/...
```

### Markdown Transformation
Both flows use the same MarkdownTransformer:

```markdown
---
title: "Document Title"
source: "source-domain.com"
published_date: "2025-05-27T10:30:00Z"
url: "https://original-url"
collection_type: "policy_landscape" | "client_news"
policy_category: "data-protection"  # Flow 1 only
---

# Document Title

Full article content with preserved formatting...
```

## DAG Implementation

### Policy Collection DAG
- **File**: `src/etl/dags/policy_collection_dag.py`
- **Schedule**: `0 2 * * 0` (Sundays 2 AM UTC)
- **Tasks**:
  1. `check_policy_initialization`
  2. `collect_policy_documents` 
  3. `mark_policy_initialization_complete`
  4. `generate_policy_collection_summary`

### News Collection DAG
- **File**: `src/etl/dags/news_collection_dag.py`
- **Schedule**: `0 1 * * *` (Daily 1 AM UTC)
- **Tasks**:
  1. `check_news_initialization`
  2. `collect_news_articles`
  3. `mark_news_initialization_complete` 
  4. `generate_news_collection_summary`

## Configuration Management

### Environment Variables
```bash
# Policy Collection (Flow 1)
POLICY_INITIALIZATION_DAYS=90      # Historical collection period
POLICY_COLLECTION_DAYS=7           # Regular collection period
POLICY_MAX_RESULTS_PER_QUERY=10    # API rate limiting
POLICY_MAX_CONCURRENT_QUERIES=3    # Concurrent request limit

# News Collection (Flow 2)  
ETL_INITIALIZATION_DAYS=30         # Historical collection period
ETL_DAILY_COLLECTION_DAYS=1        # Regular collection period
NEWS_COLLECTOR=exa_direct          # Primary collector choice

# Shared Configuration
EXA_API_KEY=your_key_here          # Primary API
APIFY_API_TOKEN=your_token_here    # Fallback API
CLIENT_CONTEXT_PATH=data/context/client.yaml
```

### Client Context Integration
Both flows leverage the same `client.yaml` configuration:

**Flow 1 Uses**:
- `topic_patterns`: For regulatory query generation
- `primary_markets`: For geographic focus
- `core_industries`: For industry-specific queries

**Flow 2 Uses**:
- `company_terms`: For company-specific queries
- `strategic_themes`: For business focus areas
- `exclusion_terms`: For content filtering

## Operational Features

### Testing & Validation
```bash
# Policy Collection Testing
just policy-test           # Core functionality test
just policy-queries        # View generated queries  
just policy-test-full      # Full test with API calls

# News Collection Testing
just etl-status            # Check initialization status
just etl-reset <collector> # Reset specific collector
```

### Monitoring & Management
- **Airflow UI**: http://localhost:8080 for DAG monitoring
- **Collection Metrics**: Success rates, document counts, processing times
- **Error Handling**: Graceful failure with detailed logging
- **Status Tracking**: Real-time visibility into collection progress

### Quality Assurance
- **API Rate Limiting**: Controlled concurrent requests
- **Content Validation**: Full-text extraction verification
- **Duplicate Prevention**: URL-based deduplication
- **Error Recovery**: Retry logic with exponential backoff

## Performance Characteristics

### Flow 1 (Policy Collection)
- **Query Volume**: 33 optimized queries
- **Expected Documents**: 50-200 per week
- **Processing Time**: 5-15 minutes per run
- **API Calls**: ~33 per collection cycle

### Flow 2 (News Collection)  
- **Query Volume**: Variable (client-dependent)
- **Expected Articles**: 10-50 per day
- **Processing Time**: 2-8 minutes per run
- **API Calls**: ~10-20 per collection cycle

## Future Enhancements

### Planned Improvements
1. **LLM Query Enhancement**: AI-powered query expansion and refinement
2. **Content Quality Scoring**: Automatic relevance assessment
3. **Cross-Flow Analysis**: Connections between policy and news content
4. **Temporal Analytics**: Trend analysis across collection periods
5. **Custom Entity Recognition**: Domain-specific entity extraction

### Integration Roadmap
1. **Phase 1**: Basic dual-flow collection (✅ Complete)
2. **Phase 2**: Content quality optimization
3. **Phase 3**: Advanced analytics and insights
4. **Phase 4**: Predictive policy impact modeling

---

**Status**: Production Ready  
**Version**: v0.2.0  
**Last Updated**: 2025-05-28  
**Components**: PolicyLandscapeCollector, ExaDirectCollector, PolicyQueryGenerator