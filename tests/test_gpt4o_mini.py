"""
Test GPT-4o-mini for Graphiti Entity Extraction (Standalone)

This is a focused test that runs ONLY gpt-4o-mini to compare with gpt-4.1-nano.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Dict

import structlog
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

from src.config import graphrag_settings
from src.graphrag.political_schema_v5 import (
    ENTITY_TYPE_REGISTRY_GENERAL,
    EDGE_TYPE_REGISTRY_GENERAL,
)

# Load environment
load_dotenv()
logger = structlog.get_logger()


def select_latest_documents(
    base_path: str,
    num_docs: int = 2,
    max_size_kb: float = 100.0
) -> List[str]:
    """Select the most recent SMALL documents from a directory."""
    path = Path(base_path)
    max_size_bytes = max_size_kb * 1024

    if not path.exists():
        return []

    subdirs = [d for d in path.iterdir() if d.is_dir() and d.name.startswith('202')]

    if subdirs:
        latest_subdir = max(subdirs, key=lambda d: d.name)
        md_files = sorted(latest_subdir.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)
    else:
        md_files = sorted(path.glob('*.md'), key=lambda f: f.stat().st_mtime, reverse=True)

    selected = []
    for f in md_files:
        if len(selected) >= num_docs:
            break
        if f.stat().st_size <= max_size_bytes:
            selected.append(str(f))

    return selected


async def query_extraction_results(group_id: str) -> Dict:
    """Query Neo4j for extraction results."""
    driver = AsyncGraphDatabase.driver(
        graphrag_settings.NEO4J_URI,
        auth=(graphrag_settings.NEO4J_USERNAME, graphrag_settings.NEO4J_PASSWORD)
    )

    try:
        async with driver.session(database=graphrag_settings.NEO4J_DATABASE) as session:
            # Query entities
            entities_result = await session.run("""
                MATCH (e:Entity)
                WHERE e.group_id = $group_id
                RETURN labels(e) as types, count(e) as count
            """, group_id=group_id)

            entities = {}
            async for record in entities_result:
                labels = record['types']
                entity_type = next((l for l in labels if l != 'Entity'), 'Unknown')
                entities[entity_type] = record['count']

            # Query relationships
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


async def test_gpt4o_mini():
    """Test GPT-4o-mini provider in isolation."""
    print("\n" + "=" * 80)
    print("GPT-4o-mini Test for Graphiti Entity Extraction")
    print("=" * 80 + "\n")

    # Select test documents (same as other tests)
    print("📁 Selecting test documents...")
    news_docs = select_latest_documents("data/input/news", num_docs=2, max_size_kb=100.0)
    policy_docs = select_latest_documents("data/input/policy", num_docs=2, max_size_kb=100.0)
    adhoc_docs = select_latest_documents("data/input/documents_md", num_docs=2, max_size_kb=100.0)
    document_paths = news_docs + policy_docs + adhoc_docs

    print(f"✅ Selected {len(document_paths)} documents\n")
    for doc in document_paths:
        print(f"  - {Path(doc).name}")

    # Clear document tracker
    print("\n🧹 Clearing document tracker...")
    tracker_file = Path("data/processed_documents.json")
    if tracker_file.exists():
        with open(tracker_file, 'r', encoding='utf-8') as f:
            processed = json.load(f)

        for doc_path in document_paths:
            if doc_path in processed:
                del processed[doc_path]

        with open(tracker_file, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
        print("✅ Tracker cleared\n")

    # Set environment for OpenAI with gpt-4o-mini
    group_id = "test_gpt4o_mini"
    os.environ["GRAPHITI_LLM_PROVIDER"] = "openai"
    os.environ["OPENAI_MODEL"] = "gpt-4o-mini"  # Used by create_graphiti_llm_client
    os.environ["GRAPHITI_GROUP_ID"] = group_id
    # Use OpenAI API directly (bypass APISIX)
    os.environ["APISIX_GATEWAY_URL"] = "https://api.openai.com/v1"

    print(f"🔧 Configuration:")
    print(f"  Provider: openai")
    print(f"  Model: gpt-4o-mini")
    print(f"  Group ID: {group_id}\n")

    # Process documents
    print("🚀 Processing documents with GPT-4o-mini...\n")
    start_time = time.time()

    import ray
    from src.flows.data_ingestion.document_processor import DocumentProcessorActor

    try:
        # Initialize Ray (ignore any RAY_ADDRESS env var)
        if "RAY_ADDRESS" in os.environ:
            del os.environ["RAY_ADDRESS"]
        if not ray.is_initialized():
            ray.init(log_to_driver=True)

        # Create actors
        num_actors = min(2, len(document_paths))
        actors = [DocumentProcessorActor.remote(i, clear_mode=False) for i in range(num_actors)]

        # Initialize actors
        init_results = await asyncio.gather(*[actor.initialize.remote() for actor in actors])
        successful_actors = [actor for actor, success in zip(actors, init_results) if success]

        print(f"✅ Initialized {len(successful_actors)}/{num_actors} actors\n")

        # Distribute documents
        from src.flows.data_ingestion_bulk_auto.processor import distribute_documents_to_actors
        batches = distribute_documents_to_actors(document_paths, len(successful_actors))

        # Process batches
        batch_refs = []
        for actor, batch in zip(successful_actors, batches):
            if batch:
                ref = actor.process_batch.remote(batch)
                batch_refs.append(ref)

        print("⏳ Processing...")
        batch_results = ray.get(batch_refs)

        # Aggregate results
        processing_results = []
        for batch_result in batch_results:
            processing_results.extend(batch_result)

        successful = sum(1 for r in processing_results if r.get("status") == "completed")
        total_entities_reported = sum(r.get("entities_extracted", 0) for r in processing_results)
        total_relationships_reported = sum(r.get("relationships_extracted", 0) for r in processing_results)

        print(f"\n✅ Processing complete!")
        print(f"  Successful: {successful}/{len(processing_results)}")
        print(f"  Entities (reported): {total_entities_reported}")
        print(f"  Relationships (reported): {total_relationships_reported}")

    finally:
        if ray.is_initialized():
            ray.shutdown()
            print("\n🛑 Ray shutdown complete")

    processing_time = time.time() - start_time

    # Query Neo4j to verify
    print(f"\n🔍 Querying Neo4j for group_id: {group_id}...")
    extraction_results = await query_extraction_results(group_id)

    print(f"\n📊 Neo4j Results:")
    print(f"  Total Entities: {extraction_results['total_entities']}")
    print(f"  Total Relationships: {extraction_results['total_relationships']}")
    print(f"  Processing Time: {processing_time:.2f}s")

    if extraction_results['total_entities'] == 0:
        print("\n⚠️ WARNING: No entities found in Neo4j!")
        print("   Checking default group_id 'political_monitoring_v2'...")
        default_results = await query_extraction_results("political_monitoring_v2")
        print(f"   Default group has {default_results['total_entities']} entities")
    else:
        print("\n✅ SUCCESS: Entities extracted and stored correctly!")
        print("\nEntity Types:")
        for entity_type, count in sorted(extraction_results['entities'].items(), key=lambda x: -x[1])[:10]:
            print(f"  - {entity_type}: {count}")

    print("\n" + "=" * 80 + "\n")

    return {
        "model": "gpt-4o-mini",
        "total_entities": extraction_results['total_entities'],
        "total_relationships": extraction_results['total_relationships'],
        "processing_time": processing_time,
        "entities_by_type": extraction_results['entities'],
        "relationships_by_type": extraction_results['relationships']
    }


if __name__ == "__main__":
    asyncio.run(test_gpt4o_mini())
