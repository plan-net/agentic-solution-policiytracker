"""
Airflow DAG for collecting news articles using configurable collectors.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add project root to path for imports - Airflow container paths
sys.path.insert(0, "/opt/airflow")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.etl.collectors.factory import create_news_collector, get_available_collectors
from src.etl.storage import get_storage
from src.etl.transformers.markdown_transformer import MarkdownTransformer
from src.etl.utils.config_loader import ClientConfigLoader
from src.etl.utils.initialization_tracker import ETLInitializationTracker

# Default arguments for the DAG
default_args = {
    "owner": "political-monitoring",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    "news_collection",
    default_args=default_args,
    description="Collect news articles using configurable collectors for political monitoring",
    schedule_interval="@daily",  # Run daily
    catchup=False,
    tags=["etl", "news", "collectors"],
)


def load_client_config(**context):
    """Load client configuration and determine collection parameters."""
    config_loader = ClientConfigLoader()
    company_name = config_loader.get_primary_company_name()
    available_collectors = get_available_collectors()
    collector_type = os.getenv("NEWS_COLLECTOR", "exa_direct").lower()

    # Validate collector availability
    if collector_type not in available_collectors:
        if available_collectors:
            collector_type = available_collectors[0]
            print(
                f"Configured collector '{os.getenv('NEWS_COLLECTOR')}' not available. Using '{collector_type}'"
            )
        else:
            raise ValueError("No news collectors available. Please configure API keys.")

    # Initialize tracker and determine collection scope
    tracker = ETLInitializationTracker(storage_type="local")
    days_back = tracker.get_collection_days(collector_type)
    is_initialization = not tracker.is_initialized(collector_type)

    # Store in XCom for next tasks
    context["task_instance"].xcom_push(key="company_name", value=company_name)
    context["task_instance"].xcom_push(
        key="search_queries", value=config_loader.get_search_queries()
    )
    context["task_instance"].xcom_push(key="collector_type", value=collector_type)
    context["task_instance"].xcom_push(key="available_collectors", value=available_collectors)
    context["task_instance"].xcom_push(key="days_back", value=days_back)
    context["task_instance"].xcom_push(key="is_initialization", value=is_initialization)

    print(f"Loaded client config. Primary company: {company_name}")
    print(f"Using collector: {collector_type}")
    print(f"Available collectors: {available_collectors}")
    print(
        f"Collection mode: {'INITIALIZATION' if is_initialization else 'DAILY'} ({days_back} days back)"
    )

    return True


async def collect_news_async(company_name: str, collector_type: str, days_back: int = 1):
    """Async function to collect news using specified collector."""
    collector = create_news_collector(collector_type)
    articles = await collector.collect_news(query=company_name, days_back=days_back, max_items=100)
    return articles


def collect_news_data(**context):
    """Collect news articles using configured collector."""
    company_name = context["task_instance"].xcom_pull(key="company_name")
    collector_type = context["task_instance"].xcom_pull(key="collector_type")
    days_back = context["task_instance"].xcom_pull(key="days_back")
    is_initialization = context["task_instance"].xcom_pull(key="is_initialization")

    # Run async collector with determined days_back
    articles = asyncio.run(collect_news_async(company_name, collector_type, days_back))

    # Store in XCom
    context["task_instance"].xcom_push(key="articles", value=articles)
    context["task_instance"].xcom_push(key="collector_used", value=collector_type)
    context["task_instance"].xcom_push(key="days_back_used", value=days_back)
    context["task_instance"].xcom_push(key="was_initialization", value=is_initialization)

    mode = "INITIALIZATION" if is_initialization else "DAILY"
    print(
        f"Collected {len(articles)} articles for {company_name} using {collector_type} ({mode}: {days_back} days)"
    )
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
        if metadata and metadata.get("url"):
            existing_urls.append(metadata["url"])

    # Process each article
    for article in articles:
        try:
            # Skip if already exists
            if article["url"] in existing_urls:
                print(f"Skipping duplicate: {article['url']}")
                continue

            # Transform to markdown
            markdown_content, filename = transformer.transform_article(article)

            # Determine path with date-based subdirectory
            pub_date = (
                article.get("published_date", "")[:10]
                if article.get("published_date")
                else datetime.now().strftime("%Y-%m-%d")
            )
            year_month = pub_date[:7]  # YYYY-MM
            file_path = f"{year_month}/{filename}"

            # Save document with metadata (support both collectors)
            metadata = {
                "url": article["url"],
                "source": article.get("source"),
                "published_date": article.get("published_date"),
                "apify_id": article.get("apify_id"),
                "exa_id": article.get("exa_id"),
                "collector_type": article.get("_raw", {}).get("collector_type", "unknown"),
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
    articles = context["task_instance"].xcom_pull(key="articles")

    if not articles:
        print("No articles to process")
        return 0

    # Run async transformer
    saved_count, failed_count = asyncio.run(transform_and_save_async(articles))

    # Store results
    context["task_instance"].xcom_push(key="saved_count", value=saved_count)
    context["task_instance"].xcom_push(key="failed_count", value=failed_count)

    print(f"Saved {saved_count} articles, {failed_count} failed")
    return saved_count


def mark_initialization_complete(**context):
    """Mark initialization as complete if this was an initialization run."""
    collector_used = context["task_instance"].xcom_pull(key="collector_used")
    was_initialization = context["task_instance"].xcom_pull(key="was_initialization")
    days_back_used = context["task_instance"].xcom_pull(key="days_back_used")
    articles = context["task_instance"].xcom_pull(key="articles") or []
    saved_count = context["task_instance"].xcom_pull(key="saved_count") or 0

    if was_initialization:
        tracker = ETLInitializationTracker(storage_type="local")
        tracker.mark_initialized(
            collector_type=collector_used,
            initialization_days=days_back_used,
            articles_collected=saved_count,  # Use saved count, not total collected
        )
        print(
            f"✅ Marked {collector_used} as initialized with {saved_count} articles from {days_back_used} days"
        )
    else:
        print("ℹ️  Regular daily collection, no initialization marking needed")

    return was_initialization


def generate_summary(**context):
    """Generate summary of the collection run."""
    company_name = context["task_instance"].xcom_pull(key="company_name")
    collector_used = context["task_instance"].xcom_pull(key="collector_used")
    available_collectors = context["task_instance"].xcom_pull(key="available_collectors") or []
    was_initialization = context["task_instance"].xcom_pull(key="was_initialization")
    days_back_used = context["task_instance"].xcom_pull(key="days_back_used")
    articles = context["task_instance"].xcom_pull(key="articles") or []
    saved_count = context["task_instance"].xcom_pull(key="saved_count") or 0
    failed_count = context["task_instance"].xcom_pull(key="failed_count") or 0

    mode = "INITIALIZATION" if was_initialization else "DAILY"

    summary = f"""
News Collection Summary
======================
Company: {company_name}
Collector Used: {collector_used}
Collection Mode: {mode} ({days_back_used} days back)
Available Collectors: {', '.join(available_collectors)}
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
    task_id="load_client_config",
    python_callable=load_client_config,
    dag=dag,
)

collect_news_task = PythonOperator(
    task_id="collect_news_data",
    python_callable=collect_news_data,
    dag=dag,
)

transform_task = PythonOperator(
    task_id="transform_to_markdown",
    python_callable=transform_to_markdown,
    dag=dag,
)

mark_complete_task = PythonOperator(
    task_id="mark_initialization_complete",
    python_callable=mark_initialization_complete,
    dag=dag,
)

summary_task = PythonOperator(
    task_id="generate_summary",
    python_callable=generate_summary,
    dag=dag,
)

# Set task dependencies
load_config_task >> collect_news_task >> transform_task >> mark_complete_task >> summary_task
