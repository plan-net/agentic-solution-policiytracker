# ETL Airflow Implementation Plan

## Overview
Implement Apache Airflow-based ETL pipeline to collect news data from Apify, transform to markdown files, and integrate with Flow 1/2 for political monitoring.

## Architecture

### Components
1. **Apache Airflow** (latest version) - Orchestration
2. **Apify Client** - Data collection 
3. **Local/Azure Storage** - Document persistence
4. **Kodosumi Integration** - Flow triggering

### Data Flow
```
Apify API → Airflow DAG → Transform to Markdown → Storage → Trigger Flow 2
```

## Implementation Phases

### Phase 1: Airflow Setup & Basic Pipeline ✅ COMPLETED
- [x] Add Airflow to Docker Compose with proper configuration
- [x] Update justfile with Airflow commands
- [x] Create basic DAG structure
- [x] Implement Apify data collection task
- [x] Transform JSON to Markdown with metadata
- [x] Store files locally in data/input/news/

### Phase 2: Client-Specific Collection ✅ COMPLETED
- [x] Parse client.yaml for query terms
- [x] Build dynamic queries from company_terms and strategic_themes
- [x] Implement deduplication logic
- [x] Add metadata enrichment

### Phase 3: Flow Integration
- [ ] Research Ray/Kodosumi integration options
- [ ] Implement Flow 2 triggering mechanism
- [ ] Add processing status tracking
- [ ] Create monitoring dashboard

### Phase 4: Production Features
- [ ] Azure Blob Storage integration
- [ ] Advanced scheduling (daily + manual triggers)
- [ ] Error handling and retries
- [ ] Performance optimization

## Technical Details

### Docker Compose Updates
```yaml
airflow:
  image: apache/airflow:latest
  environment:
    - AIRFLOW__CORE__EXECUTOR=LocalExecutor
    - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
    - AIRFLOW__CORE__LOAD_EXAMPLES=False
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs
    - ./data:/opt/airflow/data
  depends_on:
    - postgres
```

### DAG Structure
```python
# dags/news_collection_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'political-monitoring',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'news_collection',
    default_args=default_args,
    description='Collect news from Apify for client monitoring',
    schedule_interval=timedelta(days=1),
    catchup=False,
)
```

### Markdown Format
```markdown
---
title: {article_title}
url: {article_url}
published_date: {publication_date}
source: {source_name}
author: {author}
topics: [{topics}]
collected_date: {collection_timestamp}
apify_id: {unique_id}
---

# {article_title}

{article_full_text}
```

## TODO List

### Week 1: Foundation ✅ COMPLETED
- [x] Create src/etl/ directory structure (cleaner than airflow/ folder)
- [x] Add Airflow service to docker-compose.yml
- [x] Update justfile with commands:
  - `just airflow-up` - Start Airflow
  - `just airflow-logs` - View logs
  - `just airflow-trigger-news` - Manual news collection trigger
  - `just airflow-trigger-flows` - Manual flow orchestration trigger
- [x] Dependencies handled via _PIP_ADDITIONAL_REQUIREMENTS (no requirements.txt needed)
- [x] Set up Airflow database initialization
- [x] Create .env entries for APIFY_API_TOKEN

### Week 2: Core Implementation ✅ COMPLETED
- [x] Implement ApifyNewsCollector class with async support
- [x] Create MarkdownTransformer with temporal metadata focus
- [x] Build news_collection_dag.py with tasks:
  - load_client_config
  - collect_news_data
  - transform_to_markdown
  - save_to_storage
- [x] Add deduplication based on article URL
- [x] Implement comprehensive error handling and structured logging

### Week 3: Integration
- [ ] Research Kodosumi/Ray triggering options:
  - Option A: HTTP API calls to Kodosumi
  - Option B: Ray job submission
  - Option C: File watcher pattern
- [ ] Implement chosen integration method
- [ ] Create flow_orchestration_dag.py
- [ ] Add processing status tracking table
- [ ] Test end-to-end pipeline

### Week 4: Production Readiness
- [ ] Add Azure Blob Storage support
- [ ] Implement comprehensive monitoring
- [ ] Create operational documentation
- [ ] Add performance metrics
- [ ] Set up alerting for failures

## Configuration Files

### airflow/requirements.txt
```
apify-client==1.6.0
pyyaml==6.0
azure-storage-blob==12.19.0
structlog==24.1.0
```

### airflow/dags/config.py
```python
import os
from pathlib import Path

APIFY_API_TOKEN = os.getenv('APIFY_API_TOKEN')
APIFY_ACTOR_ID = "eWUEW5YpCaCBAa0Zs"
CLIENT_CONFIG_PATH = Path("/opt/airflow/data/context/client.yaml")
OUTPUT_PATH = Path("/opt/airflow/data/input/news")
MAX_ITEMS_PER_RUN = 100
FETCH_ARTICLE_DETAILS = True
```

## Monitoring & Logging
- Airflow UI for DAG monitoring
- Structured logging with correlation IDs
- Metrics: articles collected, processing time, error rate
- Alerts: API failures, quota exceeded, processing errors

## Security Considerations
- Move API key to environment variables
- Implement secret rotation
- Add rate limiting to prevent API abuse
- Secure Airflow UI with authentication

## Future Enhancements
1. Multi-source data collection (beyond Apify)
2. Advanced NLP preprocessing
3. Real-time streaming pipeline
4. ML-based relevance scoring
5. Automated report generation

## Success Criteria
- [ ] Daily automated news collection
- [ ] 99% uptime for scheduled runs
- [ ] < 5 minute processing time per batch
- [ ] Zero data loss
- [ ] Seamless Flow 2 integration

## Open Questions
1. Historical data backfill strategy?
2. Handling of non-English content?
3. Storage retention policy?
4. Disaster recovery plan?
5. Multi-client support architecture?