"""
Airflow DAG for collecting news articles from Apify.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path for imports - Airflow container paths
sys.path.insert(0, '/opt/airflow')

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.etl.collectors.apify_news import ApifyNewsCollector
from src.etl.transformers.markdown_transformer import MarkdownTransformer
from src.etl.storage import get_storage
from src.etl.utils.config_loader import ClientConfigLoader

# Default arguments for the DAG
default_args = {
    'owner': 'political-monitoring',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'news_collection',
    default_args=default_args,
    description='Collect news articles from Apify for political monitoring',
    schedule_interval='@daily',  # Run daily
    catchup=False,
    tags=['etl', 'news', 'apify'],
)


def load_client_config(**context):
    """Load client configuration."""
    config_loader = ClientConfigLoader()
    company_name = config_loader.get_primary_company_name()
    
    # Store in XCom for next tasks
    context['task_instance'].xcom_push(key='company_name', value=company_name)
    context['task_instance'].xcom_push(key='search_queries', value=config_loader.get_search_queries())
    
    print(f"Loaded client config. Primary company: {company_name}")
    return True


async def collect_news_async(company_name: str, days_back: int = 1):
    """Async function to collect news."""
    collector = ApifyNewsCollector()
    articles = await collector.collect_news(
        query=company_name,
        days_back=days_back,
        max_items=100
    )
    return articles


def collect_news_data(**context):
    """Collect news articles from Apify."""
    company_name = context['task_instance'].xcom_pull(key='company_name')
    
    # Run async collector
    articles = asyncio.run(collect_news_async(company_name))
    
    # Store in XCom
    context['task_instance'].xcom_push(key='articles', value=articles)
    
    print(f"Collected {len(articles)} articles for {company_name}")
    return len(articles)


async def transform_and_save_async(articles, storage_type="local"):
    """Async function to transform and save articles."""
    transformer = MarkdownTransformer()
    storage = get_storage(storage_type)
    
    saved_count = 0
    failed_count = 0
    
    # Get existing documents for deduplication
    existing_docs = await storage.list_documents()
    existing_urls = []
    
    # Extract URLs from existing documents
    for doc_path in existing_docs:
        metadata = await storage.get_metadata(doc_path)
        if metadata and metadata.get('url'):
            existing_urls.append(metadata['url'])
    
    # Process each article
    for article in articles:
        try:
            # Skip if already exists
            if article['url'] in existing_urls:
                print(f"Skipping duplicate: {article['url']}")
                continue
            
            # Transform to markdown
            markdown_content, filename = transformer.transform_article(article)
            
            # Determine path with date-based subdirectory
            pub_date = article.get('published_date', '')[:10] if article.get('published_date') else datetime.now().strftime('%Y-%m-%d')
            year_month = pub_date[:7]  # YYYY-MM
            file_path = f"{year_month}/{filename}"
            
            # Save document with metadata
            metadata = {
                'url': article['url'],
                'source': article.get('source'),
                'published_date': article.get('published_date'),
                'apify_id': article.get('apify_id')
            }
            
            success = await storage.save_document(markdown_content, file_path, metadata)
            
            if success:
                saved_count += 1
            else:
                failed_count += 1
                
        except Exception as e:
            print(f"Failed to process article: {e}")
            failed_count += 1
    
    return saved_count, failed_count


def transform_to_markdown(**context):
    """Transform articles to markdown and save to storage."""
    articles = context['task_instance'].xcom_pull(key='articles')
    
    if not articles:
        print("No articles to process")
        return 0
    
    # Run async transformer
    saved_count, failed_count = asyncio.run(transform_and_save_async(articles))
    
    # Store results
    context['task_instance'].xcom_push(key='saved_count', value=saved_count)
    context['task_instance'].xcom_push(key='failed_count', value=failed_count)
    
    print(f"Saved {saved_count} articles, {failed_count} failed")
    return saved_count


def generate_summary(**context):
    """Generate summary of the collection run."""
    company_name = context['task_instance'].xcom_pull(key='company_name')
    articles = context['task_instance'].xcom_pull(key='articles') or []
    saved_count = context['task_instance'].xcom_pull(key='saved_count') or 0
    failed_count = context['task_instance'].xcom_pull(key='failed_count') or 0
    
    summary = f"""
News Collection Summary
======================
Company: {company_name}
Articles Collected: {len(articles)}
Articles Saved: {saved_count}
Articles Failed: {failed_count}
Duplicates Skipped: {len(articles) - saved_count - failed_count}
Run Date: {context['ds']}
"""
    
    print(summary)
    
    # Could save summary to a file or send notification
    return summary


# Define tasks
load_config_task = PythonOperator(
    task_id='load_client_config',
    python_callable=load_client_config,
    dag=dag,
)

collect_news_task = PythonOperator(
    task_id='collect_news_data',
    python_callable=collect_news_data,
    dag=dag,
)

transform_task = PythonOperator(
    task_id='transform_to_markdown',
    python_callable=transform_to_markdown,
    dag=dag,
)

summary_task = PythonOperator(
    task_id='generate_summary',
    python_callable=generate_summary,
    dag=dag,
)

# Set task dependencies
load_config_task >> collect_news_task >> transform_task >> summary_task