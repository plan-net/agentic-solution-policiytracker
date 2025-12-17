"""
Airflow DAG for collecting news articles using configurable collectors.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add project root to path for imports - Airflow container paths
sys.path.insert(0, "/opt/airflow")

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago

from src.etl.collectors.factory import (
    create_news_collector,
    get_available_collectors,
    get_enabled_collectors,
)
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

    # Get enabled collectors (supports multi-collector via NEWS_COLLECTORS env var)
    enabled_collectors = get_enabled_collectors()

    if not enabled_collectors:
        raise ValueError("No news collectors available. Please configure API keys.")

    # Initialize tracker and determine collection scope per collector
    tracker = ETLInitializationTracker(storage_type="local")

    # Determine days_back based on initialization status
    # Use the maximum days needed across all enabled collectors
    collector_days = {}
    any_initialization = False
    for collector_type in enabled_collectors:
        days = tracker.get_collection_days(collector_type)
        is_init = not tracker.is_initialized(collector_type)
        collector_days[collector_type] = {"days_back": days, "is_initialization": is_init}
        if is_init:
            any_initialization = True

    # Use max days_back across all collectors
    max_days_back = max(info["days_back"] for info in collector_days.values())

    # Store in XCom for next tasks
    context["task_instance"].xcom_push(key="company_name", value=company_name)
    context["task_instance"].xcom_push(
        key="search_queries", value=config_loader.get_search_queries()
    )
    context["task_instance"].xcom_push(key="enabled_collectors", value=enabled_collectors)
    context["task_instance"].xcom_push(key="collector_days", value=collector_days)
    context["task_instance"].xcom_push(key="available_collectors", value=available_collectors)
    context["task_instance"].xcom_push(key="days_back", value=max_days_back)
    context["task_instance"].xcom_push(key="is_initialization", value=any_initialization)

    # For backwards compatibility
    context["task_instance"].xcom_push(key="collector_type", value=enabled_collectors[0])

    print(f"Loaded client config. Primary company: {company_name}")
    print(f"Enabled collectors: {enabled_collectors}")
    print(f"Available collectors: {available_collectors}")
    print(f"Collector settings: {collector_days}")
    print(
        f"Collection mode: {'INITIALIZATION' if any_initialization else 'DAILY'} (max {max_days_back} days back)"
    )

    return True


async def collect_news_async(company_name: str, collector_type: str, days_back: int = 1):
    """Async function to collect news using specified collector."""
    collector = create_news_collector(collector_type)
    articles = await collector.collect_news(query=company_name, days_back=days_back, max_items=100)
    return articles


async def collect_from_all_collectors(
    company_name: str, enabled_collectors: list[str], days_back: int
) -> tuple[list[dict], dict[str, int]]:
    """Collect news from all enabled collectors sequentially."""
    all_articles = []
    collector_stats = {}

    for collector_type in enabled_collectors:
        try:
            print(f"Collecting from {collector_type}...")
            collector = create_news_collector(collector_type)
            articles = await collector.collect_news(
                query=company_name, days_back=days_back, max_items=100
            )
            # Tag articles with collector source
            for article in articles:
                article["_collector_type"] = collector_type
            all_articles.extend(articles)
            collector_stats[collector_type] = len(articles)
            print(f"  ✓ Collected {len(articles)} articles from {collector_type}")
        except Exception as e:
            print(f"  ✗ Failed to collect from {collector_type}: {e}")
            collector_stats[collector_type] = 0
            # Continue with other collectors

    return all_articles, collector_stats


def collect_news_data(**context):
    """Collect news articles using all enabled collectors."""
    company_name = context["task_instance"].xcom_pull(key="company_name")
    enabled_collectors = context["task_instance"].xcom_pull(key="enabled_collectors")
    days_back = context["task_instance"].xcom_pull(key="days_back")
    is_initialization = context["task_instance"].xcom_pull(key="is_initialization")

    # For backwards compatibility, fall back to single collector if needed
    if not enabled_collectors:
        collector_type = context["task_instance"].xcom_pull(key="collector_type")
        enabled_collectors = [collector_type] if collector_type else []

    if not enabled_collectors:
        print("No collectors enabled!")
        context["task_instance"].xcom_push(key="articles", value=[])
        context["task_instance"].xcom_push(key="collector_stats", value={})
        return 0

    # Run async collection from all collectors
    articles, collector_stats = asyncio.run(
        collect_from_all_collectors(company_name, enabled_collectors, days_back)
    )

    # Store in XCom
    context["task_instance"].xcom_push(key="articles", value=articles)
    context["task_instance"].xcom_push(key="collector_stats", value=collector_stats)
    context["task_instance"].xcom_push(key="collectors_used", value=enabled_collectors)
    context["task_instance"].xcom_push(key="days_back_used", value=days_back)
    context["task_instance"].xcom_push(key="was_initialization", value=is_initialization)

    # For backwards compatibility
    context["task_instance"].xcom_push(key="collector_used", value=enabled_collectors[0])

    mode = "INITIALIZATION" if is_initialization else "DAILY"
    print(f"\n{'='*50}")
    print(f"Collection Summary ({mode}: {days_back} days)")
    print(f"{'='*50}")
    print(f"Company: {company_name}")
    print(f"Collectors used: {enabled_collectors}")
    for collector, count in collector_stats.items():
        print(f"  - {collector}: {count} articles")
    print(f"Total collected: {len(articles)} articles")
    print(f"{'='*50}\n")

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
    """Mark initialization as complete for all collectors that were initializing."""
    collectors_used = context["task_instance"].xcom_pull(key="collectors_used") or []
    collector_days = context["task_instance"].xcom_pull(key="collector_days") or {}
    collector_stats = context["task_instance"].xcom_pull(key="collector_stats") or {}
    was_initialization = context["task_instance"].xcom_pull(key="was_initialization")
    days_back_used = context["task_instance"].xcom_pull(key="days_back_used")
    saved_count = context["task_instance"].xcom_pull(key="saved_count") or 0

    # For backwards compatibility
    if not collectors_used:
        collector_used = context["task_instance"].xcom_pull(key="collector_used")
        collectors_used = [collector_used] if collector_used else []

    if was_initialization:
        tracker = ETLInitializationTracker(storage_type="local")

        for collector_type in collectors_used:
            collector_info = collector_days.get(collector_type, {})
            if collector_info.get("is_initialization", False):
                articles_from_collector = collector_stats.get(collector_type, 0)
                tracker.mark_initialized(
                    collector_type=collector_type,
                    initialization_days=collector_info.get("days_back", days_back_used),
                    articles_collected=articles_from_collector,
                )
                print(
                    f"✅ Marked {collector_type} as initialized with {articles_from_collector} articles"
                )
            else:
                print(f"ℹ️  {collector_type} was already initialized, skipping")
    else:
        print("ℹ️  Regular daily collection, no initialization marking needed")

    return was_initialization


def check_auto_trigger(**context):
    """Check if auto-trigger for Flow 1 is enabled."""
    from src.config import graphrag_settings

    saved_count = context["task_instance"].xcom_pull(key="saved_count") or 0

    # Check if auto-trigger is enabled and we have new documents
    if graphrag_settings.ENABLE_AUTO_TRIGGER_FLOW1 and saved_count > 0:
        print(f"✅ Auto-trigger enabled and {saved_count} new documents saved")
        print(f"Will trigger DAG: {graphrag_settings.FLOW1_ORCHESTRATION_DAG_ID}")
        return "trigger_flow_orchestration"
    else:
        if not graphrag_settings.ENABLE_AUTO_TRIGGER_FLOW1:
            print("ℹ️  Auto-trigger disabled in config")
        if saved_count == 0:
            print("ℹ️  No new documents to trigger Flow 1 with")
        return "generate_summary"


def generate_summary(**context):
    """Generate summary of the collection run."""
    company_name = context["task_instance"].xcom_pull(key="company_name")
    collectors_used = context["task_instance"].xcom_pull(key="collectors_used") or []
    collector_stats = context["task_instance"].xcom_pull(key="collector_stats") or {}
    available_collectors = context["task_instance"].xcom_pull(key="available_collectors") or []
    was_initialization = context["task_instance"].xcom_pull(key="was_initialization")
    days_back_used = context["task_instance"].xcom_pull(key="days_back_used")
    articles = context["task_instance"].xcom_pull(key="articles") or []
    saved_count = context["task_instance"].xcom_pull(key="saved_count") or 0
    failed_count = context["task_instance"].xcom_pull(key="failed_count") or 0

    # For backwards compatibility
    if not collectors_used:
        collector_used = context["task_instance"].xcom_pull(key="collector_used")
        collectors_used = [collector_used] if collector_used else []

    mode = "INITIALIZATION" if was_initialization else "DAILY"

    # Build collector stats string
    collector_stats_str = ""
    for collector in collectors_used:
        count = collector_stats.get(collector, 0)
        collector_stats_str += f"\n  - {collector}: {count} articles"

    summary = f"""
{'='*60}
News Collection Summary
{'='*60}
Company: {company_name}
Collection Mode: {mode} ({days_back_used} days back)
Run Date: {context['ds']}

Collectors Used: {', '.join(collectors_used)}
Available Collectors: {', '.join(available_collectors)}

Collector Stats:{collector_stats_str}

Results:
  - Total Collected: {len(articles)}
  - Articles Saved: {saved_count}
  - Articles Failed: {failed_count}
  - Duplicates Skipped: {len(articles) - saved_count - failed_count}
{'='*60}
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

check_trigger_task = BranchPythonOperator(
    task_id="check_auto_trigger",
    python_callable=check_auto_trigger,
    dag=dag,
)

trigger_orchestration_task = TriggerDagRunOperator(
    task_id="trigger_flow_orchestration",
    trigger_dag_id="flow_orchestration",
    dag=dag,
)

summary_task = PythonOperator(
    task_id="generate_summary",
    python_callable=generate_summary,
    dag=dag,
)

# Set task dependencies
load_config_task >> collect_news_task >> transform_task >> mark_complete_task >> check_trigger_task
check_trigger_task >> [trigger_orchestration_task, summary_task]
