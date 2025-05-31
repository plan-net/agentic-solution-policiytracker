"""
Policy Landscape Collector for ETL Pipeline

Specialized collector for gathering policy and regulatory documents
using targeted search queries derived from client context.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..storage import get_storage
from ..transformers.markdown_transformer import MarkdownTransformer
from ..utils.policy_query_generator import PolicyQueryGenerator
from .exa_direct import ExaDirectCollector

logger = logging.getLogger(__name__)


class PolicyLandscapeCollector:
    """Collector specialized for policy and regulatory document gathering."""

    def __init__(
        self,
        exa_api_key: str,
        client_context_path: str = "data/context/client.yaml",
        storage_type: str = "local",
    ):
        """
        Initialize policy landscape collector.

        Args:
            exa_api_key: API key for Exa search
            client_context_path: Path to client context YAML
            storage_type: Storage type ("local" or "azure")
        """
        self.exa_collector = ExaDirectCollector(exa_api_key)
        self.query_generator = PolicyQueryGenerator(client_context_path)
        self.transformer = MarkdownTransformer()
        self.storage = get_storage(storage_type, base_path="data/input")

    async def collect_policy_documents(
        self, days_back: int = 7, max_results_per_query: int = 10, max_concurrent_queries: int = 3
    ) -> Dict[str, Any]:
        """
        Collect policy documents using generated queries.

        Args:
            days_back: How many days back to search
            max_results_per_query: Maximum results per search query
            max_concurrent_queries: Maximum concurrent API calls

        Returns:
            Collection results with statistics
        """
        start_time = datetime.now()
        logger.info(f"Starting policy document collection (days_back={days_back})")

        # Generate targeted queries
        queries = self.query_generator.generate_policy_queries()
        logger.info(f"Generated {len(queries)} policy search queries")

        # Collect documents in batches to respect API limits
        all_results = []
        failed_queries = []

        # Process queries in batches
        for i in range(0, len(queries), max_concurrent_queries):
            batch = queries[i : i + max_concurrent_queries]
            batch_results = await self._process_query_batch(batch, days_back, max_results_per_query)

            for result in batch_results:
                if result.get("success"):
                    all_results.extend(result.get("articles", []))
                else:
                    failed_queries.append(result.get("query"))

            # Small delay between batches to be API-friendly
            if i + max_concurrent_queries < len(queries):
                await asyncio.sleep(1)

        # Transform and save documents
        saved_documents = await self._save_policy_documents(all_results)

        # Generate summary
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        summary = {
            "collection_type": "policy_landscape",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "processing_time_seconds": processing_time,
            "queries_processed": len(queries),
            "queries_failed": len(failed_queries),
            "total_articles_found": len(all_results),
            "documents_saved": len(saved_documents),
            "categories_covered": self._get_categories_summary(queries),
            "failed_queries": failed_queries[:5],  # Sample of failed queries
            "sample_documents": saved_documents[:3],  # Sample of saved documents
        }

        logger.info(
            f"Policy collection completed: {len(saved_documents)} documents "
            f"saved in {processing_time:.1f}s"
        )

        return summary

    async def _process_query_batch(
        self, queries: List[Dict[str, str]], days_back: int, max_results_per_query: int
    ) -> List[Dict[str, Any]]:
        """Process a batch of queries concurrently."""
        tasks = []

        for query_info in queries:
            task = self._execute_single_query(query_info, days_back, max_results_per_query)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict)]

    async def _execute_single_query(
        self, query_info: Dict[str, str], days_back: int, max_results_per_query: int
    ) -> Dict[str, Any]:
        """Execute a single search query."""
        try:
            # Use the same date range logic as news collection
            start_date = datetime.now() - timedelta(days=days_back)

            logger.debug(f"Executing query: {query_info['query'][:50]}...")

            articles = await self.exa_collector.collect_news(
                query=query_info["query"], max_items=max_results_per_query, days_back=days_back
            )

            # Add category metadata to articles
            for article in articles:
                article["policy_category"] = query_info["category"]
                article["query_description"] = query_info["description"]
                article["collection_type"] = "policy_landscape"

            return {
                "success": True,
                "query": query_info["query"],
                "category": query_info["category"],
                "articles": articles,
            }

        except Exception as e:
            logger.error(f"Query failed: {query_info['query'][:50]}... - {e}")
            return {
                "success": False,
                "query": query_info["query"],
                "category": query_info["category"],
                "error": str(e),
            }

    async def _save_policy_documents(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform and save policy documents."""
        saved_documents = []

        # Remove duplicates based on URL
        unique_articles = {}
        for article in articles:
            url = article.get("url", "")
            if url and url not in unique_articles:
                unique_articles[url] = article

        logger.info(f"Saving {len(unique_articles)} unique policy documents")

        for article in unique_articles.values():
            try:
                # Add collection metadata to article before transformation
                article["collection_type"] = "policy_landscape"

                # Transform to markdown
                markdown_content, _ = self.transformer.transform_article(article)

                # Generate filename
                published_date = article.get("published_date", datetime.now())
                if isinstance(published_date, str):
                    try:
                        published_date = datetime.fromisoformat(
                            published_date.replace("Z", "+00:00")
                        )
                    except:
                        published_date = datetime.now()

                filename = self._generate_policy_filename(article, published_date)

                # Save using standardized storage interface
                file_path = f"policy/{published_date.strftime('%Y-%m')}/{filename}"

                # Create metadata for consistency with news collection
                metadata = {
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "published_date": article.get("published_date"),
                    "policy_category": article.get("policy_category", "unknown"),
                    "collection_type": article.get("collection_type", "policy_landscape"),
                    "query_description": article.get("query_description", ""),
                    "collector_type": "exa_direct",
                }

                # Use standardized storage save method
                success = await self.storage.save_document(markdown_content, file_path, metadata)

                if success:
                    saved_documents.append(
                        {
                            "filename": filename,
                            "file_path": file_path,
                            "category": article.get("policy_category", "unknown"),
                            "title": article.get("title", "Unknown"),
                            "url": article.get("url", ""),
                            "published_date": published_date.isoformat(),
                        }
                    )
                else:
                    logger.error(f"Failed to save document: {file_path}")

            except Exception as e:
                logger.error(f"Failed to save document {article.get('url', 'unknown')}: {e}")
                continue

        return saved_documents

    def _generate_policy_filename(self, article: Dict[str, Any], published_date: datetime) -> str:
        """Generate standardized filename for policy documents."""
        # Extract domain from URL for source identification
        url = article.get("url", "")
        domain = "unknown"

        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "").replace(".", "-")
        except:
            pass

        # Clean title for filename
        title = article.get("title", "untitled")
        clean_title = self._clean_filename(title)

        # Format: YYYYMMDD_source_title-slug.md
        date_str = published_date.strftime("%Y%m%d")
        return f"{date_str}_{domain}_{clean_title}.md"

    def _clean_filename(self, text: str, max_length: int = 50) -> str:
        """Clean text for use in filename."""
        import re

        # Convert to lowercase and replace spaces/special chars
        cleaned = re.sub(r"[^\w\s-]", "", text.lower())
        cleaned = re.sub(r"[-\s]+", "-", cleaned)

        # Truncate if too long
        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length].rstrip("-")

        return cleaned

    def _get_categories_summary(self, queries: List[Dict[str, str]]) -> Dict[str, int]:
        """Get summary of categories covered."""
        summary: Dict[str, int] = {}
        for query in queries:
            category = query["category"]
            summary[category] = summary.get(category, 0) + 1
        return summary

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about policy collection configuration."""
        queries = self.query_generator.generate_policy_queries()
        query_summary = self.query_generator.get_query_summary()

        is_valid, validation_errors = self.query_generator.validate_queries()

        return {
            "total_queries": len(queries),
            "categories": query_summary,
            "validation": {"is_valid": is_valid, "errors": validation_errors},
            "estimated_api_calls": len(queries),
            "estimated_max_documents": len(queries) * 10,  # 10 per query default
        }


async def main() -> None:
    """Test the policy landscape collector."""
    import os

    print("=== Policy Landscape Collector Test ===")

    # Check if API key is available
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        print("❌ EXA_API_KEY not found in environment")
        return

    # Initialize collector
    collector = PolicyLandscapeCollector(
        exa_api_key=api_key, client_context_path="data/context/client.yaml"
    )

    # Get collection stats
    print("\n📊 Collection Statistics:")
    stats = await collector.get_collection_stats()
    print(f"  • Total queries: {stats['total_queries']}")
    print(f"  • Categories: {list(stats['categories'].keys())}")
    print(f"  • Validation: {'✅ Valid' if stats['validation']['is_valid'] else '❌ Invalid'}")

    if not stats["validation"]["is_valid"]:
        print("  • Errors:")
        for error in stats["validation"]["errors"]:
            print(f"    - {error}")
        return

    # Test collection with limited scope
    print("\n🔍 Testing Policy Collection (limited scope)...")

    try:
        result = await collector.collect_policy_documents(
            days_back=7,
            max_results_per_query=2,  # Limited for testing
            max_concurrent_queries=2,
        )

        print("\n✅ Collection completed:")
        print(f"  • Processing time: {result['processing_time_seconds']:.1f}s")
        print(f"  • Queries processed: {result['queries_processed']}")
        print(f"  • Documents found: {result['total_articles_found']}")
        print(f"  • Documents saved: {result['documents_saved']}")

        if result["failed_queries"]:
            print(f"  • Failed queries: {len(result['failed_queries'])}")

        # Show sample documents
        if result["sample_documents"]:
            print("\n📄 Sample Documents:")
            for doc in result["sample_documents"]:
                print(f"  • {doc['filename']} ({doc['category']})")

    except Exception as e:
        print(f"❌ Collection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
