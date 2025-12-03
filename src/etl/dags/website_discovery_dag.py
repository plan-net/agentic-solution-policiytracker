"""
Airflow DAG for website content discovery and collection.

Discovers and collects relevant content (blogs, articles, news, press releases)
from German government and political websites, filters for relevance based on
client.yaml, and saves as markdown for downstream Graphiti ingestion.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add project root to path for imports - Airflow container paths
sys.path.insert(0, "/opt/airflow")

import yaml
from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago

# Default arguments for the DAG
default_args = {
    "owner": "political-monitoring",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

# Create the DAG
dag = DAG(
    "website_discovery_collection",
    default_args=default_args,
    description="Discover and collect content from German government and political websites",
    schedule_interval="0 6 * * *",  # Daily at 6 AM
    catchup=False,
    max_active_runs=1,
    tags=["etl", "discovery", "websites", "political"],
)


def load_configurations(**context) -> bool:
    """Load websites.yaml and client.yaml configurations."""
    import structlog

    logger = structlog.get_logger()

    try:
        # Load websites.yaml
        websites_path = Path("/opt/airflow/src/etl/config/websites.yaml")
        if not websites_path.exists():
            # Try local path
            websites_path = Path("src/etl/config/websites.yaml")

        with open(websites_path, "r") as f:
            websites_config = yaml.safe_load(f)

        # Load client.yaml
        client_path = Path("/opt/airflow/data/context/client.yaml")
        if not client_path.exists():
            client_path = Path("data/context/client.yaml")

        with open(client_path, "r") as f:
            client_config = yaml.safe_load(f)

        # Get enabled sites
        enabled_sites = [
            site_key
            for site_key, site_data in websites_config.get("websites", {}).items()
            if site_data.get("enabled", True)
        ]

        # Store in XCom
        context["task_instance"].xcom_push(key="websites_config", value=websites_config)
        context["task_instance"].xcom_push(key="client_config", value=client_config)
        context["task_instance"].xcom_push(key="enabled_sites", value=enabled_sites)

        logger.info(
            f"Loaded configurations",
            enabled_sites=enabled_sites,
            filtering_strategy=websites_config.get("filtering", {}).get("strategy", "hybrid"),
        )

        return True

    except Exception as e:
        logger.error(f"Failed to load configurations: {e}")
        raise


async def discover_site_async(
    site_key: str,
    websites_config: dict,
    limit: int = 100,
) -> dict[str, Any]:
    """Async function to discover content from a single site."""
    from src.etl.collectors.website_discovery import (
        RateLimiter,
        RateLimiterConfig,
        create_orchestrator_from_yaml,
    )

    import structlog

    logger = structlog.get_logger()

    # Get discovery settings
    discovery_settings = websites_config.get("discovery_settings", {})

    # Create rate limiter
    rate_limiter = RateLimiter(
        RateLimiterConfig(
            request_delay_seconds=discovery_settings.get("request_delay_seconds", 1.5),
            max_concurrent_requests=discovery_settings.get("max_concurrent_requests", 3),
            request_timeout_seconds=discovery_settings.get("request_timeout_seconds", 30),
            respect_robots_txt=discovery_settings.get("respect_robots_txt", True),
        )
    )

    # Check robots.txt
    site_config = websites_config["websites"][site_key]
    await rate_limiter.check_robots_txt(site_config["domain"])

    # Create orchestrator
    orchestrator = create_orchestrator_from_yaml(
        site_key=site_key,
        websites_config=websites_config,
        rate_limiter=rate_limiter,
    )

    try:
        # Discover content
        result = await orchestrator.discover_content(limit=limit)

        return {
            "site_key": site_key,
            "success": result.success,
            "articles": [
                {
                    "url": a.url,
                    "title": a.title,
                    "published_date": a.published_date.isoformat() if a.published_date else None,
                    "description": a.description,
                    "discovery_strategy": a.discovery_strategy.value,
                }
                for a in result.articles
            ],
            "urls_discovered": result.urls_discovered,
            "strategy_used": result.strategy.value,
            "duration_seconds": result.duration_seconds,
            "errors": result.errors,
        }

    except Exception as e:
        logger.error(f"Discovery failed for {site_key}", error=str(e))
        return {
            "site_key": site_key,
            "success": False,
            "articles": [],
            "errors": [str(e)],
        }

    finally:
        await orchestrator.close()


def discover_all_sites(**context) -> int:
    """Discover content from all enabled sites."""
    import structlog

    logger = structlog.get_logger()

    websites_config = context["task_instance"].xcom_pull(key="websites_config")
    enabled_sites = context["task_instance"].xcom_pull(key="enabled_sites")

    async def run_all_discoveries():
        results = []
        for site_key in enabled_sites:
            logger.info(f"Discovering content from {site_key}")
            result = await discover_site_async(site_key, websites_config)
            results.append(result)
        return results

    # Run async discoveries
    discovery_results = asyncio.run(run_all_discoveries())

    # Store results
    context["task_instance"].xcom_push(key="discovery_results", value=discovery_results)

    # Calculate totals
    total_articles = sum(len(r.get("articles", [])) for r in discovery_results)
    successful_sites = sum(1 for r in discovery_results if r.get("success"))

    logger.info(
        f"Discovery complete",
        total_articles=total_articles,
        successful_sites=successful_sites,
        total_sites=len(enabled_sites),
    )

    return total_articles


def deduplicate_urls(**context) -> int:
    """Deduplicate discovered URLs against persistent state."""
    import structlog

    from src.etl.utils.url_deduplication import URLDeduplicator

    logger = structlog.get_logger()

    discovery_results = context["task_instance"].xcom_pull(key="discovery_results")
    websites_config = context["task_instance"].xcom_pull(key="websites_config")

    # Get deduplication config
    dedup_config = websites_config.get("deduplication", {})
    state_file = dedup_config.get("state_file", "data/state/website_discovery_state.json")
    lookback_days = dedup_config.get("lookback_days", 90)

    with URLDeduplicator(state_file=state_file, lookback_days=lookback_days) as deduplicator:
        # Clean up old entries
        deduplicator.cleanup_old_entries()

        deduplicated_results = []

        for result in discovery_results:
            if not result.get("success"):
                deduplicated_results.append(result)
                continue

            # Filter out already processed URLs
            site_key = result["site_key"]
            new_articles = []

            for article in result.get("articles", []):
                if not deduplicator.is_processed(article["url"]):
                    new_articles.append(article)
                else:
                    logger.debug(f"Skipping duplicate URL", url=article["url"])

            result["articles"] = new_articles
            result["urls_after_dedup"] = len(new_articles)
            deduplicated_results.append(result)

        # Save state (but don't mark as processed yet - do that after save)
        deduplicator.save_state()

    context["task_instance"].xcom_push(key="deduplicated_results", value=deduplicated_results)

    total_new = sum(len(r.get("articles", [])) for r in deduplicated_results)
    logger.info(f"Deduplication complete", new_articles=total_new)

    return total_new


async def filter_articles_async(
    articles: list[dict],
    client_config: dict,
    filter_config: dict,
) -> list[dict]:
    """Filter articles for relevance."""
    from src.etl.filtering import RelevanceFilter, create_filter_from_config

    relevance_filter = create_filter_from_config(client_config, filter_config)

    relevant_articles = []

    for article in articles:
        title = article.get("title", "")
        content = article.get("description", "")
        published_date = None

        if article.get("published_date"):
            try:
                published_date = datetime.fromisoformat(article["published_date"])
            except (ValueError, TypeError):
                pass

        result = await relevance_filter.filter_content(title, content, published_date)

        if result.decision.value == "relevant":
            article["relevance_score"] = result.final_score
            article["matched_keywords"] = result.matched_keywords
            relevant_articles.append(article)

    return relevant_articles


def filter_relevance(**context) -> int:
    """Filter discovered articles for relevance."""
    import structlog

    logger = structlog.get_logger()

    deduplicated_results = context["task_instance"].xcom_pull(key="deduplicated_results")
    client_config = context["task_instance"].xcom_pull(key="client_config")
    websites_config = context["task_instance"].xcom_pull(key="websites_config")

    filter_config = websites_config.get("filtering", {})

    async def run_filtering():
        filtered_results = []

        for result in deduplicated_results:
            if not result.get("success") or not result.get("articles"):
                filtered_results.append(result)
                continue

            relevant_articles = await filter_articles_async(
                result["articles"],
                client_config,
                filter_config,
            )

            result["articles"] = relevant_articles
            result["articles_after_filter"] = len(relevant_articles)
            filtered_results.append(result)

        return filtered_results

    filtered_results = asyncio.run(run_filtering())

    context["task_instance"].xcom_push(key="filtered_results", value=filtered_results)

    total_relevant = sum(len(r.get("articles", [])) for r in filtered_results)
    logger.info(f"Filtering complete", relevant_articles=total_relevant)

    return total_relevant


async def extract_and_save_async(
    articles: list[dict],
    site_key: str,
) -> tuple[int, int]:
    """Extract full content and save as markdown."""
    from src.etl.storage import get_storage
    from src.etl.transformers.markdown_transformer import MarkdownTransformer
    from src.flows.shared.url_to_markdown import URLToMarkdownConverter

    import structlog

    logger = structlog.get_logger()

    converter = URLToMarkdownConverter()
    transformer = MarkdownTransformer()
    storage = get_storage("local", base_path="data/input/website")

    saved_count = 0
    failed_count = 0

    for article in articles:
        try:
            # Fetch full content
            article_data = await converter._fetch_url(article["url"])

            if not article_data:
                logger.warning(f"Failed to fetch content", url=article["url"])
                failed_count += 1
                continue

            # Merge with discovery metadata
            article_data["title"] = article.get("title") or article_data.get("title", "Untitled")
            article_data["published_date"] = article.get("published_date") or article_data.get(
                "published_date"
            )
            article_data["collection_type"] = "website_discovery"
            article_data["discovery_method"] = article.get("discovery_strategy", "unknown")
            article_data["relevance_score"] = article.get("relevance_score")
            article_data["language"] = "de"

            # Transform to markdown
            markdown_content, filename = transformer.transform_article(article_data)

            # Determine path with date-based subdirectory
            pub_date = (
                article_data.get("published_date", "")[:10]
                if article_data.get("published_date")
                else datetime.now().strftime("%Y-%m-%d")
            )
            year_month = pub_date[:7]  # YYYY-MM
            file_path = f"{year_month}/{filename}"

            # Save document
            metadata = {
                "url": article["url"],
                "source": site_key,
                "published_date": article_data.get("published_date"),
                "discovery_method": article.get("discovery_strategy"),
                "collection_type": "website_discovery",
            }

            success = await storage.save_document(markdown_content, file_path, metadata)

            if success:
                saved_count += 1
                logger.debug(f"Saved article", path=file_path)
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Failed to process article", url=article["url"], error=str(e))
            failed_count += 1

    return saved_count, failed_count


def extract_and_save(**context) -> int:
    """Extract full content and save as markdown."""
    import structlog

    logger = structlog.get_logger()

    filtered_results = context["task_instance"].xcom_pull(key="filtered_results")

    async def run_extraction():
        total_saved = 0
        total_failed = 0

        for result in filtered_results:
            if not result.get("success") or not result.get("articles"):
                continue

            saved, failed = await extract_and_save_async(
                result["articles"],
                result["site_key"],
            )

            total_saved += saved
            total_failed += failed
            result["saved_count"] = saved
            result["failed_count"] = failed

        return total_saved, total_failed, filtered_results

    total_saved, total_failed, updated_results = asyncio.run(run_extraction())

    context["task_instance"].xcom_push(key="final_results", value=updated_results)
    context["task_instance"].xcom_push(key="total_saved", value=total_saved)
    context["task_instance"].xcom_push(key="total_failed", value=total_failed)

    logger.info(f"Extraction complete", saved=total_saved, failed=total_failed)

    return total_saved


def update_discovery_state(**context) -> bool:
    """Update persistent state with processed URLs."""
    import structlog

    from src.etl.utils.url_deduplication import URLDeduplicator

    logger = structlog.get_logger()

    final_results = context["task_instance"].xcom_pull(key="final_results")
    websites_config = context["task_instance"].xcom_pull(key="websites_config")
    total_saved = context["task_instance"].xcom_pull(key="total_saved") or 0

    dedup_config = websites_config.get("deduplication", {})
    state_file = dedup_config.get("state_file", "data/state/website_discovery_state.json")

    with URLDeduplicator(state_file=state_file) as deduplicator:
        for result in final_results:
            if not result.get("success"):
                continue

            site_key = result["site_key"]

            # Mark saved URLs as processed
            for article in result.get("articles", []):
                deduplicator.mark_processed(
                    url=article["url"],
                    source=site_key,
                    metadata={"saved_at": datetime.now().isoformat()},
                )

            # Update site statistics
            deduplicator.update_run_stats(
                discovered=result.get("urls_discovered", 0),
                saved=result.get("saved_count", 0),
                site=site_key,
            )

    logger.info(f"State updated", urls_marked=total_saved)

    return True


def check_auto_trigger(**context) -> str:
    """Check if auto-trigger for Flow 1 is enabled."""
    import os

    import structlog

    logger = structlog.get_logger()

    total_saved = context["task_instance"].xcom_pull(key="total_saved") or 0

    # Read setting directly from environment variable to avoid pydantic_settings dependency
    enable_auto_trigger = os.getenv("ENABLE_AUTO_TRIGGER_FLOW1", "false").lower() == "true"

    if enable_auto_trigger and total_saved > 0:
        logger.info(f"Auto-trigger enabled, {total_saved} new documents saved")
        return "trigger_flow_orchestration"
    else:
        if not enable_auto_trigger:
            logger.info("Auto-trigger disabled in config")
        if total_saved == 0:
            logger.info("No new documents to trigger Flow 1 with")
        return "generate_summary"


def generate_summary(**context) -> str:
    """Generate summary of the discovery run."""
    import structlog

    logger = structlog.get_logger()

    final_results = context["task_instance"].xcom_pull(key="final_results") or []
    total_saved = context["task_instance"].xcom_pull(key="total_saved") or 0
    total_failed = context["task_instance"].xcom_pull(key="total_failed") or 0

    # Calculate totals
    total_discovered = sum(r.get("urls_discovered", 0) for r in final_results)
    successful_sites = sum(1 for r in final_results if r.get("success"))
    strategies_used = set(r.get("strategy_used", "unknown") for r in final_results if r.get("success"))

    summary = f"""
Website Discovery Summary
=========================
Run Date: {context['ds']}

Sites:
  - Total: {len(final_results)}
  - Successful: {successful_sites}

Discovery:
  - URLs Discovered: {total_discovered}
  - Strategies Used: {', '.join(strategies_used)}

Results:
  - Articles Saved: {total_saved}
  - Articles Failed: {total_failed}

Per-Site Breakdown:
"""

    for result in final_results:
        site_key = result.get("site_key", "unknown")
        status = "OK" if result.get("success") else "FAILED"
        saved = result.get("saved_count", 0)
        summary += f"  - {site_key}: {status} ({saved} saved)\n"

    logger.info(summary)

    return summary


# Define tasks
load_config_task = PythonOperator(
    task_id="load_configurations",
    python_callable=load_configurations,
    dag=dag,
)

discover_task = PythonOperator(
    task_id="discover_all_sites",
    python_callable=discover_all_sites,
    dag=dag,
)

dedup_task = PythonOperator(
    task_id="deduplicate_urls",
    python_callable=deduplicate_urls,
    dag=dag,
)

filter_task = PythonOperator(
    task_id="filter_relevance",
    python_callable=filter_relevance,
    dag=dag,
)

extract_task = PythonOperator(
    task_id="extract_and_save",
    python_callable=extract_and_save,
    dag=dag,
)

state_task = PythonOperator(
    task_id="update_discovery_state",
    python_callable=update_discovery_state,
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
    trigger_rule="none_failed_min_one_success",
)

# Set task dependencies
(
    load_config_task
    >> discover_task
    >> dedup_task
    >> filter_task
    >> extract_task
    >> state_task
    >> check_trigger_task
)
check_trigger_task >> [trigger_orchestration_task, summary_task]
