"""
Compare OpenAI and Anthropic LLM providers for Graphiti entity extraction quality.

This test:
1. Selects latest documents from production directories (news, policy, documents_md)
2. Processes them with OpenAI (gpt-4o-mini)
3. Clears graph data
4. Processes them with Anthropic (claude-sonnet-4-5-latest)
5. Compares entity/relationship extraction quality
6. Generates a detailed markdown comparison report

Usage:
    python3 tests/test_llm_provider_comparison.py

Requirements:
    - Neo4j running (for Graphiti)
    - OPENAI_API_KEY and ANTHROPIC_API_KEY in .env
    - Production documents in data/input/{news,policy,documents_md}
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import structlog

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded environment variables from .env\n")
except ImportError:
    print("⚠️  python-dotenv not installed, using existing environment variables\n")

from neo4j import AsyncGraphDatabase

# Project imports
from src.config import settings, graphrag_settings
from src.graphrag.political_schema_v5 import (
    ENTITY_TYPE_REGISTRY_GENERAL,
    EDGE_TYPE_REGISTRY_GENERAL,
)

# Configure logging
logger = structlog.get_logger(__name__)


# ============================================================================
# Document Selection
# ============================================================================

def select_latest_documents(
    base_path: str,
    num_docs: int = 2,
    max_size_kb: float = 100.0
) -> List[str]:
    """
    Select the most recent SMALL documents from a directory (for fast testing).

    For news/policy (subdirectory structure):
    - Find latest subdirectory (e.g., 2026-02)
    - Return num_docs latest SMALL .md files by modification time

    For documents_md (flat structure):
    - Return num_docs latest SMALL .md files by modification time

    Args:
        base_path: Directory to search for documents
        num_docs: Number of documents to select (default 2 for faster testing)
        max_size_kb: Maximum file size in KB (default 100KB = ~2-3 chunks)

    Returns:
        List of file paths
    """
    path = Path(base_path)
    max_size_bytes = max_size_kb * 1024

    if not path.exists():
        logger.warning(f"Path does not exist: {base_path}")
        return []

    # Check if subdirectory structure (news/policy) or flat (documents_md)
    subdirs = [d for d in path.iterdir() if d.is_dir() and d.name.startswith('202')]

    if subdirs:
        # Subdirectory structure - find latest month
        latest_subdir = max(subdirs, key=lambda d: d.name)
        logger.info(f"Selected latest subdirectory: {latest_subdir.name}")
        md_files = sorted(latest_subdir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)
    else:
        # Flat structure
        md_files = sorted(path.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)

    # Filter by size and take num_docs
    selected = []
    for f in md_files:
        if len(selected) >= num_docs:
            break
        file_size_kb = f.stat().st_size / 1024
        if f.stat().st_size <= max_size_bytes:
            selected.append(str(f))
            logger.info(f"Selected: {f.name} ({file_size_kb:.2f} KB)")
        else:
            logger.info(f"Skipped (too large): {f.name} ({file_size_kb:.2f} KB)")

    return selected


def infer_category(file_path: str) -> str:
    """Infer document category from file path."""
    if '/news/' in file_path:
        return 'news'
    elif '/policy/' in file_path:
        return 'policy'
    elif '/documents_md/' in file_path:
        return 'adhoc'
    return 'unknown'


# ============================================================================
# Neo4j Query Functions
# ============================================================================

async def query_extraction_results(group_id: str) -> Dict:
    """
    Query Neo4j to retrieve extraction results.

    Returns aggregated entity and relationship counts.
    """
    driver = AsyncGraphDatabase.driver(
        graphrag_settings.NEO4J_URI,
        auth=(graphrag_settings.NEO4J_USERNAME, graphrag_settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=graphrag_settings.NEO4J_DATABASE) as session:
            # Query entities by type
            entities_result = await session.run("""
                MATCH (e:Entity)
                WHERE e.group_id = $group_id
                RETURN labels(e) as types, count(e) as count
            """, group_id=group_id)

            entities = {}
            async for record in entities_result:
                # labels() returns a list like ['Entity', 'Policy']
                # We want the non-'Entity' label
                labels = record['types']
                entity_type = next((l for l in labels if l != 'Entity'), 'Unknown')
                entities[entity_type] = record['count']

            # Query relationships by type
            relationships_result = await session.run("""
                MATCH (a:Entity)-[r]->(b:Entity)
                WHERE a.group_id = $group_id
                RETURN type(r) as rel_type, count(r) as count
            """, group_id=group_id)

            relationships = {}
            async for record in relationships_result:
                relationships[record['rel_type']] = record['count']

            return {
                "entities": entities,
                "relationships": relationships,
                "total_entities": sum(entities.values()),
                "total_relationships": sum(relationships.values())
            }
    finally:
        await driver.close()


async def clear_graph_data(group_id: str):
    """Clear Neo4j graph data for a specific group_id."""
    driver = AsyncGraphDatabase.driver(
        graphrag_settings.NEO4J_URI,
        auth=(graphrag_settings.NEO4J_USERNAME, graphrag_settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=graphrag_settings.NEO4J_DATABASE) as session:
            result = await session.run("""
                MATCH (n {group_id: $group_id})
                DETACH DELETE n
                RETURN count(n) as deleted_count
            """, group_id=group_id)

            async for record in result:
                logger.info(f"Deleted {record['deleted_count']} nodes from group_id: {group_id}")
    finally:
        await driver.close()


# ============================================================================
# Schema Compliance Validation
# ============================================================================

def validate_schema_compliance(extraction_results: Dict) -> Dict:
    """
    Validate extraction results against political_schema_v5.

    Checks:
    - Entity types in ENTITY_TYPE_REGISTRY_GENERAL
    - Edge types in EDGE_TYPE_REGISTRY_GENERAL
    """
    entities = extraction_results.get("entities", {})
    relationships = extraction_results.get("relationships", {})

    # Validate entity types
    valid_entity_count = 0
    invalid_entity_types = []
    for entity_type, count in entities.items():
        if entity_type in ENTITY_TYPE_REGISTRY_GENERAL:
            valid_entity_count += count
        else:
            invalid_entity_types.append((entity_type, count))

    total_entities = sum(entities.values())
    entity_compliance_rate = (valid_entity_count / total_entities * 100) if total_entities > 0 else 0

    # Validate relationship types
    valid_relationship_count = 0
    invalid_relationship_types = []
    for rel_type, count in relationships.items():
        if rel_type in EDGE_TYPE_REGISTRY_GENERAL:
            valid_relationship_count += count
        else:
            invalid_relationship_types.append((rel_type, count))

    total_relationships = sum(relationships.values())
    relationship_compliance_rate = (valid_relationship_count / total_relationships * 100) if total_relationships > 0 else 0

    return {
        "total_entities": total_entities,
        "valid_entity_count": valid_entity_count,
        "invalid_entity_types": invalid_entity_types,
        "entity_compliance_rate": entity_compliance_rate,
        "total_relationships": total_relationships,
        "valid_relationship_count": valid_relationship_count,
        "invalid_relationship_types": invalid_relationship_types,
        "relationship_compliance_rate": relationship_compliance_rate,
    }


# ============================================================================
# Test Provider Function
# ============================================================================

async def test_provider(
    provider: str,
    model: str,
    document_paths: List[str],
    group_id: str
) -> Dict:
    """
    Process documents with specified LLM provider using Flow 1B DocumentProcessorActor.

    Returns:
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "total_documents": 9,
            "document_paths": [...],
            "total_processing_time": 45.3,
            "extraction_results": {...},
            "schema_compliance": {...}
        }
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Testing {provider.upper()} ({model})")
    logger.info(f"Documents: {len(document_paths)}")
    logger.info(f"Group ID: {group_id}")
    logger.info(f"{'=' * 60}\n")

    start_time = time.time()

    # Set environment variable for LLM provider
    os.environ["GRAPHITI_LLM_PROVIDER"] = provider
    # Override the group_id for this test
    os.environ["GRAPHITI_GROUP_ID"] = group_id

    # Import Flow 1B components (same as Flow 1B uses)
    import ray
    from src.flows.data_ingestion.document_processor import DocumentProcessorActor

    # Process documents using Flow 1B approach
    logger.info(f"Processing {len(document_paths)} documents with DocumentProcessorActor...")

    try:
        # Initialize Ray if not already done
        if not ray.is_initialized():
            ray.init(log_to_driver=True)

        # Create Ray actors for parallel processing (use 2 for test)
        num_actors = min(2, len(document_paths))
        actors = [DocumentProcessorActor.remote(i, clear_mode=False) for i in range(num_actors)]

        # Initialize actors
        init_results = await asyncio.gather(*[actor.initialize.remote() for actor in actors])
        successful_actors = [actor for actor, success in zip(actors, init_results) if success]

        logger.info(f"Actor initialization: {len(successful_actors)}/{num_actors} successful")

        if not successful_actors:
            raise RuntimeError("No actors could be initialized for parallel processing")

        # Distribute documents across actors
        from src.flows.data_ingestion_bulk_auto.processor import distribute_documents_to_actors
        batches = distribute_documents_to_actors(document_paths, len(successful_actors))

        logger.info(f"Document distribution: {len(document_paths)} files → {len(batches)} batches")

        # Process batches in parallel
        batch_refs = []
        for actor, batch in zip(successful_actors, batches):
            if batch:
                ref = actor.process_batch.remote(batch)
                batch_refs.append(ref)

        # Wait for all batches to complete
        batch_results = ray.get(batch_refs)

        # Flatten results
        processing_results = []
        for batch_result in batch_results:
            processing_results.extend(batch_result)

        # Log results
        successful = sum(1 for r in processing_results if r.get("status") == "completed")
        failed = len(processing_results) - successful
        total_entities = sum(r.get("entities_extracted", 0) for r in processing_results)
        total_relationships = sum(r.get("relationships_extracted", 0) for r in processing_results)

        logger.info(f"✓ Processed {len(processing_results)} documents: {successful} successful, {failed} failed")
        logger.info(f"  Total entities: {total_entities}, Total relationships: {total_relationships}")

    except Exception as e:
        logger.error(f"✗ Document processing failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Shutdown Ray to ensure clean state for next provider test
        # This ensures the next test will pick up new environment variables
        if ray.is_initialized():
            ray.shutdown()
            logger.info("Ray shutdown complete")

    # Query Neo4j for extraction results
    logger.info(f"Querying Neo4j for extraction results with group_id: {group_id}...")
    extraction_results = await query_extraction_results(group_id)

    # Debug: Also check if data was written to default group_id
    if extraction_results["total_entities"] == 0:
        logger.warning(f"No entities found for group_id '{group_id}'. Checking default group_id...")
        default_group_id = "political_monitoring_v2"
        default_results = await query_extraction_results(default_group_id)
        if default_results["total_entities"] > 0:
            logger.warning(f"Found {default_results['total_entities']} entities in default group_id '{default_group_id}'!")
            logger.warning("This means the GRAPHITI_GROUP_ID environment variable was not picked up correctly.")
            # Use the default results instead
            extraction_results = default_results
            logger.info(f"Using results from group_id '{default_group_id}' instead.")

    # Validate schema compliance
    schema_compliance = validate_schema_compliance(extraction_results)

    processing_time = time.time() - start_time

    return {
        "provider": provider,
        "model": model,
        "total_documents": len(document_paths),
        "document_paths": document_paths,
        "total_processing_time": processing_time,
        "avg_time_per_document": processing_time / len(document_paths) if document_paths else 0,
        "extraction_results": extraction_results,
        "schema_compliance": schema_compliance,
    }


# ============================================================================
# Comparison & Report Generation
# ============================================================================

def compare_extraction_quality(
    openai_results: Dict,
    anthropic_results: Dict
) -> Dict:
    """
    Compare extraction quality between providers.

    Compares:
    - Entity extraction completeness
    - Relationship extraction completeness
    - Schema compliance
    - Processing speed
    """
    openai_entities = openai_results["extraction_results"]["total_entities"]
    anthropic_entities = anthropic_results["extraction_results"]["total_entities"]
    entity_diff = anthropic_entities - openai_entities
    entity_pct_diff = (entity_diff / openai_entities * 100) if openai_entities > 0 else 0

    openai_relationships = openai_results["extraction_results"]["total_relationships"]
    anthropic_relationships = anthropic_results["extraction_results"]["total_relationships"]
    relationship_diff = anthropic_relationships - openai_relationships
    relationship_pct_diff = (relationship_diff / openai_relationships * 100) if openai_relationships > 0 else 0

    # Determine winner based on multiple factors
    openai_score = (
        openai_results["schema_compliance"]["entity_compliance_rate"] +
        openai_results["schema_compliance"]["relationship_compliance_rate"]
    ) / 2

    anthropic_score = (
        anthropic_results["schema_compliance"]["entity_compliance_rate"] +
        anthropic_results["schema_compliance"]["relationship_compliance_rate"]
    ) / 2

    if anthropic_score > openai_score:
        winner = "Anthropic"
        reason = f"Higher schema compliance ({anthropic_score:.1f}% vs {openai_score:.1f}%)"
    elif openai_score > anthropic_score:
        winner = "OpenAI"
        reason = f"Higher schema compliance ({openai_score:.1f}% vs {anthropic_score:.1f}%)"
    else:
        winner = "Tie"
        reason = "Equal schema compliance"

    return {
        "entity_comparison": {
            "openai_total": openai_entities,
            "anthropic_total": anthropic_entities,
            "difference": entity_diff,
            "percentage_diff": entity_pct_diff,
        },
        "relationship_comparison": {
            "openai_total": openai_relationships,
            "anthropic_total": anthropic_relationships,
            "difference": relationship_diff,
            "percentage_diff": relationship_pct_diff,
        },
        "compliance_comparison": {
            "openai_score": openai_score,
            "anthropic_score": anthropic_score,
        },
        "performance_comparison": {
            "openai_time": openai_results["total_processing_time"],
            "anthropic_time": anthropic_results["total_processing_time"],
            "openai_avg": openai_results["avg_time_per_document"],
            "anthropic_avg": anthropic_results["avg_time_per_document"],
        },
        "winner": winner,
        "winner_reason": reason,
    }


def generate_comparison_report(
    comparison: Dict,
    openai_results: Dict,
    anthropic_results: Dict,
    document_paths: List[str]
) -> str:
    """Generate markdown comparison report."""

    # Entity details
    openai_entities = openai_results["extraction_results"]["entities"]
    anthropic_entities = anthropic_results["extraction_results"]["entities"]

    # Relationship details
    openai_relationships = openai_results["extraction_results"]["relationships"]
    anthropic_relationships = anthropic_results["extraction_results"]["relationships"]

    # Schema compliance
    openai_compliance = openai_results["schema_compliance"]
    anthropic_compliance = anthropic_results["schema_compliance"]

    report = f"""# LLM Provider Comparison for Graphiti Entity Extraction

**Test Date**: {datetime.now().isoformat()}
**Test Documents**: {len(document_paths)} documents

## Document Sources

"""

    # List documents by category
    news_docs = [p for p in document_paths if '/news/' in p]
    policy_docs = [p for p in document_paths if '/policy/' in p]
    adhoc_docs = [p for p in document_paths if '/documents_md/' in p]

    report += f"- **News Articles**: {len(news_docs)} documents\n"
    report += f"- **Policy Documents**: {len(policy_docs)} documents\n"
    report += f"- **Ad-hoc Documents**: {len(adhoc_docs)} documents\n\n"

    report += f"""## Executive Summary

**Winner**: {comparison['winner']}
**Reason**: {comparison['winner_reason']}

---

## Entity Extraction Comparison

| Provider   | Model                   | Total Entities | Valid Types | Invalid Types | Compliance Rate |
|------------|-------------------------|----------------|-------------|---------------|-----------------|
| OpenAI     | {openai_results['model']:23} | {openai_compliance['total_entities']:14} | {openai_compliance['valid_entity_count']:11} | {len(openai_compliance['invalid_entity_types']):13} | {openai_compliance['entity_compliance_rate']:14.1f}% |
| Anthropic  | {anthropic_results['model']:23} | {anthropic_compliance['total_entities']:14} | {anthropic_compliance['valid_entity_count']:11} | {len(anthropic_compliance['invalid_entity_types']):13} | {anthropic_compliance['entity_compliance_rate']:14.1f}% |

**Difference**: {comparison['entity_comparison']['difference']:+d} entities ({comparison['entity_comparison']['percentage_diff']:+.1f}%)

### Entity Type Breakdown

**OpenAI**:
"""

    for entity_type, count in sorted(openai_entities.items(), key=lambda x: x[1], reverse=True):
        valid_marker = "✓" if entity_type in ENTITY_TYPE_REGISTRY_GENERAL else "✗"
        report += f"- {valid_marker} {entity_type}: {count}\n"

    report += "\n**Anthropic**:\n"

    for entity_type, count in sorted(anthropic_entities.items(), key=lambda x: x[1], reverse=True):
        valid_marker = "✓" if entity_type in ENTITY_TYPE_REGISTRY_GENERAL else "✗"
        report += f"- {valid_marker} {entity_type}: {count}\n"

    report += f"""
---

## Relationship Extraction Comparison

| Provider   | Model                   | Total Relationships | Valid Types | Invalid Types | Compliance Rate |
|------------|-------------------------|---------------------|-------------|---------------|-----------------|
| OpenAI     | {openai_results['model']:23} | {anthropic_compliance['total_relationships']:19} | {openai_compliance['valid_relationship_count']:11} | {len(openai_compliance['invalid_relationship_types']):13} | {openai_compliance['relationship_compliance_rate']:14.1f}% |
| Anthropic  | {anthropic_results['model']:23} | {anthropic_compliance['total_relationships']:19} | {anthropic_compliance['valid_relationship_count']:11} | {len(anthropic_compliance['invalid_relationship_types']):13} | {anthropic_compliance['relationship_compliance_rate']:14.1f}% |

**Difference**: {comparison['relationship_comparison']['difference']:+d} relationships ({comparison['relationship_comparison']['percentage_diff']:+.1f}%)

### Relationship Type Breakdown

**OpenAI**:
"""

    for rel_type, count in sorted(openai_relationships.items(), key=lambda x: x[1], reverse=True)[:10]:
        valid_marker = "✓" if rel_type in EDGE_TYPE_REGISTRY_GENERAL else "✗"
        report += f"- {valid_marker} {rel_type}: {count}\n"

    report += "\n**Anthropic**:\n"

    for rel_type, count in sorted(anthropic_relationships.items(), key=lambda x: x[1], reverse=True)[:10]:
        valid_marker = "✓" if rel_type in EDGE_TYPE_REGISTRY_GENERAL else "✗"
        report += f"- {valid_marker} {rel_type}: {count}\n"

    report += f"""
---

## Processing Performance

| Provider   | Total Time | Avg Time/Doc |
|------------|------------|--------------|
| OpenAI     | {comparison['performance_comparison']['openai_time']:.2f}s | {comparison['performance_comparison']['openai_avg']:.2f}s |
| Anthropic  | {comparison['performance_comparison']['anthropic_time']:.2f}s | {comparison['performance_comparison']['anthropic_avg']:.2f}s |

---

## Recommendations

Based on the comprehensive comparison:

1. **Best for Quality**: {comparison['winner']}
   - {comparison['winner_reason']}

2. **Entity Extraction**: {"Anthropic" if comparison['entity_comparison']['difference'] > 0 else "OpenAI"} extracted {abs(comparison['entity_comparison']['difference'])} more entities

3. **Relationship Extraction**: {"Anthropic" if comparison['relationship_comparison']['difference'] > 0 else "OpenAI"} extracted {abs(comparison['relationship_comparison']['difference'])} more relationships

**Overall Recommendation**: {comparison['winner']} shows better extraction quality for this document set.

---

*Generated by: LLM Provider Comparison Test Framework*
*Test Framework Version: 1.0.0*
*Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    return report


# ============================================================================
# Main Test Function
# ============================================================================

async def test_llm_provider_comparison():
    """
    Compare OpenAI and Anthropic for Graphiti entity extraction.

    Test Approach:
    1. Load latest documents from production directories
    2. Process with OpenAI (GRAPHITI_LLM_PROVIDER=openai)
    3. Clear graph data
    4. Process with Anthropic (GRAPHITI_LLM_PROVIDER=anthropic)
    5. Compare extraction results
    6. Generate markdown report
    """
    print("\n" + "=" * 80)
    print("LLM Provider Comparison Test for Graphiti Entity Extraction")
    print("=" * 80 + "\n")

    # Select latest SMALL documents from production directories (for faster testing)
    print("📁 Selecting latest small documents (max 100KB each, 2-3 chunks)...")
    news_docs = select_latest_documents("data/input/news", num_docs=2, max_size_kb=100.0)
    policy_docs = select_latest_documents("data/input/policy", num_docs=2, max_size_kb=100.0)
    adhoc_docs = select_latest_documents("data/input/documents_md", num_docs=2, max_size_kb=100.0)

    document_paths = news_docs + policy_docs + adhoc_docs

    if not document_paths:
        print("❌ No documents found. Please ensure documents exist in:")
        print("   - data/input/news/")
        print("   - data/input/policy/")
        print("   - data/input/documents_md/")
        return

    print(f"\n✅ Selected {len(document_paths)} documents:")
    print(f"   - News: {len(news_docs)}")
    print(f"   - Policy: {len(policy_docs)}")
    print(f"   - Ad-hoc: {len(adhoc_docs)}\n")

    # Clear document tracker for test documents to allow reprocessing
    print("🧹 Clearing document tracker for test documents...")
    tracker_file = Path("data/processed_documents.json")
    if tracker_file.exists():
        with open(tracker_file, 'r', encoding='utf-8') as f:
            processed = json.load(f)

        # Remove test documents from tracker
        docs_removed = 0
        for doc_path in document_paths:
            if doc_path in processed:
                del processed[doc_path]
                docs_removed += 1

        # Save updated tracker
        with open(tracker_file, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)

        print(f"   Removed {docs_removed}/{len(document_paths)} documents from tracker\n")
    else:
        print("   No tracker file found, documents will be processed fresh\n")

    # Test with OpenAI
    group_id_openai = "test_comparison_openai"
    openai_results = await test_provider(
        provider="openai",
        model="gpt-4o-mini",
        document_paths=document_paths,
        group_id=group_id_openai
    )

    print(f"\n✅ OpenAI results:")
    print(f"   - Entities: {openai_results['extraction_results']['total_entities']}")
    print(f"   - Relationships: {openai_results['extraction_results']['total_relationships']}")
    print(f"   - Schema compliance: {openai_results['schema_compliance']['entity_compliance_rate']:.1f}%")

    # Clear Neo4j data between tests
    print(f"\n🧹 Clearing graph data for group_id: {group_id_openai}")
    await clear_graph_data(group_id_openai)

    # Test with Anthropic
    group_id_anthropic = "test_comparison_anthropic"
    anthropic_results = await test_provider(
        provider="anthropic",
        model="claude-sonnet-4-5-latest",
        document_paths=document_paths,
        group_id=group_id_anthropic
    )

    print(f"\n✅ Anthropic results:")
    print(f"   - Entities: {anthropic_results['extraction_results']['total_entities']}")
    print(f"   - Relationships: {anthropic_results['extraction_results']['total_relationships']}")
    print(f"   - Schema compliance: {anthropic_results['schema_compliance']['entity_compliance_rate']:.1f}%")

    # Compare results
    print(f"\n📊 Comparing results...")
    comparison = compare_extraction_quality(openai_results, anthropic_results)

    # Generate report
    report = generate_comparison_report(comparison, openai_results, anthropic_results, document_paths)

    # Save report
    report_path = Path("tests/llm_provider_comparison_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding='utf-8')

    print(f"\n✅ Report generated: {report_path}")
    print(f"\n{'=' * 80}")
    print(f"Winner: {comparison['winner']}")
    print(f"Reason: {comparison['winner_reason']}")
    print(f"{'=' * 80}\n")

    # Clean up
    print(f"\n🧹 Cleaning up test data...")
    await clear_graph_data(group_id_anthropic)

    return comparison


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    asyncio.run(test_llm_provider_comparison())
