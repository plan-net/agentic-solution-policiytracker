# ETL Pipeline v0.2.0 Patterns

## Dual-Flow ETL Architecture

### Flow 1: Policy Landscape Collection (Weekly)
```python
# Schedule: Sundays at 2 AM UTC
# Sources: Exa.ai with intelligent query generation
# Target: data/input/policy/YYYY-MM/
# Content: EU regulations, policy changes, enforcement actions
```

### Flow 2: Client News Collection (Daily)  
```python
# Schedule: Configurable timing
# Sources: Exa.ai, Apify news aggregators
# Target: data/input/news/YYYY-MM/
# Content: Company-specific news and industry developments
```

## Airflow DAG Patterns

### Policy Collection DAG
```python
# src/etl/dags/policy_collection_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'political-monitoring',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'policy_collection_dag',
    default_args=default_args,
    description='Weekly policy landscape collection',
    schedule_interval='0 2 * * 0',  # Sundays at 2 AM UTC
    catchup=False,
    tags=['policy', 'weekly'],
)

def collect_policy_documents(**context):
    from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
    
    collector = PolicyLandscapeCollector()
    results = collector.collect_documents()
    
    return {
        'documents_collected': results['documents_saved'],
        'execution_time': results['duration'],
        'status': 'success'
    }

policy_task = PythonOperator(
    task_id='collect_policy_documents',
    python_callable=collect_policy_documents,
    dag=dag,
)
```

### News Collection DAG
```python
# src/etl/dags/news_collection_dag.py
dag = DAG(
    'news_collection_dag',
    default_args=default_args,
    description='Daily client news collection',
    schedule_interval='0 6 * * *',  # Daily at 6 AM UTC
    catchup=False,
    tags=['news', 'daily'],
)

def collect_news_articles(**context):
    from src.etl.collectors.exa_news import ExaNewsCollector
    
    collector = ExaNewsCollector()
    results = collector.collect_documents()
    
    # Trigger downstream processing if successful
    if results['documents_saved'] > 0:
        context['task_instance'].xcom_push(
            key='trigger_processing',
            value=True
        )
    
    return results

news_task = PythonOperator(
    task_id='collect_news_articles',
    python_callable=collect_news_articles,
    dag=dag,
)
```

## Collector Implementation Patterns

### Base Collector Pattern
```python
# src/etl/collectors/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import asyncio

class BaseCollector(ABC):
    def __init__(self, storage_client=None, config=None):
        self.storage_client = storage_client
        self.config = config or {}
        self.stats = {
            'documents_collected': 0,
            'documents_saved': 0,
            'errors': [],
            'duration': 0
        }
    
    @abstractmethod
    async def collect_documents(self) -> Dict[str, Any]:
        """Collect documents from external sources."""
        pass
    
    @abstractmethod
    async def transform_documents(self, raw_docs: List) -> List:
        """Transform raw documents to standardized format."""
        pass
    
    async def save_documents(self, documents: List) -> bool:
        """Save documents to storage."""
        for doc in documents:
            success = await self.storage_client.save_document(
                content=doc['content'],
                path=doc['path'],
                metadata=doc['metadata']
            )
            if success:
                self.stats['documents_saved'] += 1
        
        return self.stats['documents_saved'] > 0
```

### Policy Landscape Collector
```python
# src/etl/collectors/policy_landscape.py
class PolicyLandscapeCollector(BaseCollector):
    async def collect_documents(self):
        # Generate queries from client context
        queries = await self._generate_policy_queries()
        
        all_documents = []
        for query in queries:
            # Collect from Exa.ai
            documents = await self.exa_collector.collect_news(
                query=query,
                start_published_date=self._get_collection_start_date(),
                num_results=20
            )
            all_documents.extend(documents)
        
        # Transform and deduplicate
        transformed_docs = await self.transform_documents(all_documents)
        deduplicated_docs = self._deduplicate_by_url(transformed_docs)
        
        # Save to storage
        await self.save_documents(deduplicated_docs)
        
        return self.stats
    
    async def _generate_policy_queries(self) -> List[str]:
        from src.etl.utils.policy_query_generator import PolicyQueryGenerator
        
        generator = PolicyQueryGenerator()
        return await generator.generate_weekly_queries()
```

## Storage Integration Patterns

### Local Storage Pattern
```python
# src/etl/storage/local.py
class LocalStorage:
    def __init__(self, base_path: str = "./data/input"):
        self.base_path = Path(base_path)
    
    async def save_document(self, content: str, path: str, metadata: dict) -> bool:
        try:
            full_path = self.base_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata as frontmatter
            frontmatter_content = self._add_frontmatter(content, metadata)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter_content)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save document {path}: {e}")
            return False
    
    def _add_frontmatter(self, content: str, metadata: dict) -> str:
        frontmatter = "---\n"
        for key, value in metadata.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += "---\n\n"
        return frontmatter + content
```

### Azure Storage Pattern
```python
# src/etl/storage/azure.py
class AzureStorage:
    async def save_document(self, content: str, path: str, metadata: dict) -> bool:
        try:
            # Create blob with metadata
            blob_client = self.container_client.get_blob_client(path)
            
            # Upload with metadata as blob metadata
            await blob_client.upload_blob(
                data=content,
                metadata=metadata,
                overwrite=True
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to save to Azure {path}: {e}")
            return False
```

## Query Generation Patterns

### Context-Aware Query Generation
```python
# src/etl/utils/policy_query_generator.py
class PolicyQueryGenerator:
    def __init__(self, context_path: str = "./data/context/client.yaml"):
        self.context = self._load_client_context(context_path)
    
    async def generate_weekly_queries(self) -> List[str]:
        base_queries = []
        
        # Topic-based queries
        for topic, keywords in self.context.get('topic_patterns', {}).items():
            for keyword in keywords:
                base_queries.append(f'"{keyword}" EU regulation policy')
        
        # Market-specific queries
        for market in self.context.get('primary_markets', []):
            base_queries.append(f'{market} regulatory changes policy')
        
        # Combine with temporal constraints
        queries_with_time = []
        for query in base_queries:
            queries_with_time.append(f"{query} after:2024-01-01")
        
        return queries_with_time
    
    async def generate_news_queries(self) -> List[str]:
        company_queries = []
        
        # Company-specific queries
        for term in self.context.get('company_terms', []):
            company_queries.append(f'"{term}" news')
        
        # Industry queries  
        for industry in self.context.get('core_industries', []):
            company_queries.append(f'{industry} regulation compliance')
        
        return company_queries
```

## Initialization and State Management

### ETL Initialization Tracker
```python
# src/etl/utils/initialization_tracker.py
class InitializationTracker:
    def __init__(self, tracking_file: str = "./data/etl_state.json"):
        self.tracking_file = Path(tracking_file)
        self.state = self._load_state()
    
    def is_collector_initialized(self, collector_name: str) -> bool:
        return self.state.get('collectors', {}).get(collector_name, {}).get('initialized', False)
    
    def mark_collector_initialized(self, collector_name: str):
        if 'collectors' not in self.state:
            self.state['collectors'] = {}
        
        self.state['collectors'][collector_name] = {
            'initialized': True,
            'initialization_date': datetime.now().isoformat(),
            'last_collection': None
        }
        self._save_state()
    
    def get_last_collection_date(self, collector_name: str) -> Optional[datetime]:
        collector_state = self.state.get('collectors', {}).get(collector_name, {})
        last_collection = collector_state.get('last_collection')
        
        if last_collection:
            return datetime.fromisoformat(last_collection)
        return None
    
    def update_last_collection(self, collector_name: str):
        if collector_name in self.state.get('collectors', {}):
            self.state['collectors'][collector_name]['last_collection'] = datetime.now().isoformat()
            self._save_state()
```

## Data Transformation Patterns

### Markdown Transformer
```python
# src/etl/transformers/markdown_transformer.py
class MarkdownTransformer:
    def transform_article(self, article: dict) -> dict:
        """Transform article to standardized markdown format."""
        
        # Extract metadata
        metadata = {
            'title': article.get('title', 'Untitled'),
            'url': article.get('url', ''),
            'published_date': article.get('published_date', ''),
            'source': article.get('source', 'unknown'),
            'collection_date': datetime.now().isoformat(),
            'content_type': 'article',
            'language': self._detect_language(article.get('text', ''))
        }
        
        # Generate filename
        filename = self._generate_filename(
            article.get('published_date'),
            article.get('source'),
            article.get('title')
        )
        
        # Format content
        content = self._format_markdown_content(article)
        
        return {
            'content': content,
            'metadata': metadata,
            'filename': filename,
            'path': self._generate_storage_path(filename, metadata)
        }
    
    def _format_markdown_content(self, article: dict) -> str:
        content = f"# {article.get('title', 'Untitled')}\n\n"
        
        if article.get('summary'):
            content += f"## Summary\n{article['summary']}\n\n"
        
        if article.get('text'):
            content += f"## Content\n{article['text']}\n\n"
        
        if article.get('url'):
            content += f"**Source**: [{article.get('source', 'Link')}]({article['url']})\n"
        
        return content
    
    def _generate_filename(self, date: str, source: str, title: str) -> str:
        # Format: YYYYMMDD_source_title-slug.md
        date_str = self._parse_date_string(date)
        source_slug = self._slugify(source)
        title_slug = self._slugify(title)[:50]  # Limit length
        
        return f"{date_str}_{source_slug}_{title_slug}.md"
```

## Error Handling and Monitoring

### Robust Collection with Error Handling
```python
async def collect_with_retry(self, collector_func, max_retries: int = 3):
    """Execute collection with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            results = await collector_func()
            return results
            
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt * 60  # Exponential backoff
                logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                await asyncio.sleep(wait_time)
            else:
                raise
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Collection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(10)
            else:
                logger.error(f"Collection failed after {max_retries} attempts: {e}")
                raise
```

### Collection Metrics and Monitoring
```python
def track_collection_metrics(self, results: dict):
    """Track collection metrics for monitoring."""
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'documents_collected': results.get('documents_saved', 0),
        'execution_time_seconds': results.get('duration', 0),
        'errors_count': len(results.get('errors', [])),
        'collection_rate': results.get('documents_saved', 0) / max(results.get('duration', 1), 1),
        'success_rate': (results.get('documents_saved', 0) / max(results.get('documents_collected', 1), 1)) * 100
    }
    
    # Log metrics for monitoring system
    logger.info(f"Collection metrics: {json.dumps(metrics)}")
    
    # Optional: Send to monitoring service
    # await self.metrics_client.send_metrics(metrics)
```

## Testing ETL Patterns

### ETL Integration Testing
```python
# tests/integration/test_etl_pipeline.py
async def test_policy_collection_end_to_end():
    # Test with mock Exa.ai responses
    with patch('src.etl.collectors.exa_direct.ExaDirectCollector.collect_news') as mock_collect:
        mock_collect.return_value = sample_policy_articles
        
        collector = PolicyLandscapeCollector()
        results = await collector.collect_documents()
        
        # Verify collection metrics
        assert results['documents_saved'] > 0
        assert results['duration'] > 0
        assert len(results['errors']) == 0
        
        # Verify files were created
        policy_files = list(Path("./data/input/policy").rglob("*.md"))
        assert len(policy_files) > 0
```

### Collector Unit Testing
```python
async def test_markdown_transformer():
    transformer = MarkdownTransformer()
    
    sample_article = {
        'title': 'EU AI Act Implementation Guidelines',
        'url': 'https://example.com/ai-act',
        'text': 'The EU AI Act introduces new requirements...',
        'published_date': '2024-05-27',
        'source': 'europa.eu'
    }
    
    result = transformer.transform_article(sample_article)
    
    assert result['filename'].endswith('.md')
    assert 'EU AI Act' in result['content']
    assert result['metadata']['content_type'] == 'article'
```

## Common Anti-Patterns

❌ **Synchronous blocking operations**:
```python
# DON'T: Block the event loop
response = requests.get(url)  # Blocks
```

❌ **No deduplication**:
```python
# DON'T: Save duplicate documents
for article in articles:
    save_document(article)  # May create duplicates
```

❌ **Hardcoded paths**:
```python
# DON'T: Hardcode storage paths
path = "/data/input/policy/file.md"  # Not flexible
```

✅ **Correct patterns**:
```python
# DO: Use async HTTP clients
async with aiohttp.ClientSession() as session:
    response = await session.get(url)

# DO: Implement deduplication
unique_articles = deduplicate_by_url(articles)

# DO: Use configurable paths
path = self.storage_config.get_policy_path(filename)
```