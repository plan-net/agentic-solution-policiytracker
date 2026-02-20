#!/usr/bin/env python3
"""
Prompt Cache Optimization Benchmark

Processes the same document through Graphiti with 4 configurations:
  1. Anthropic WITH cache optimization (CachedAnthropicClient)
  2. Anthropic WITHOUT cache optimization (plain AnthropicClient)
  3. OpenAI WITH cache optimization (CacheFriendlyOpenAIClient)
  4. OpenAI WITHOUT cache optimization (plain OpenAIClient)

Captures per-chunk and aggregate metrics:
  - Input tokens, cached tokens, output tokens
  - Cost (calculated from token counts + provider pricing)
  - Latency per chunk and total

Usage:
    # Run all 4 tests
    python scripts/benchmark_prompt_cache.py data/input/some_doc.md

    # Run only Anthropic tests
    python scripts/benchmark_prompt_cache.py data/input/some_doc.md --provider anthropic

    # Run only OpenAI tests
    python scripts/benchmark_prompt_cache.py data/input/some_doc.md --provider openai

    # Limit chunks processed (for quick testing)
    python scripts/benchmark_prompt_cache.py data/input/some_doc.md --max-chunks 3

    # Use a specific test database (to avoid polluting production)
    python scripts/benchmark_prompt_cache.py data/input/some_doc.md --database benchmark.v1
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import structlog

from src.flows.data_ingestion.logging_config import configure_logging

configure_logging()
logger = structlog.get_logger()


# ============================================================================
# Instrumented LLM Clients — wrap API calls to capture cache metrics
# ============================================================================

class MetricsCollector:
    """Collects per-call metrics from LLM API responses."""

    def __init__(self):
        self.calls: list[dict[str, Any]] = []
        self.current_chunk_index: int = -1

    def record_anthropic(self, result: Any, elapsed_ms: float):
        """Extract cache metrics from Anthropic API response."""
        usage = result.usage
        metrics = {
            "chunk_index": self.current_chunk_index,
            "provider": "anthropic",
            "model": result.model,
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0),
            "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0),
            "elapsed_ms": elapsed_ms,
            "stop_reason": result.stop_reason,
        }
        self.calls.append(metrics)

    def record_openai(self, result: Any, elapsed_ms: float):
        """Extract cache metrics from OpenAI chat.completions API response."""
        usage = result.usage
        cached_tokens = 0
        if hasattr(usage, "prompt_tokens_details") and usage.prompt_tokens_details:
            cached_tokens = getattr(usage.prompt_tokens_details, "cached_tokens", 0) or 0

        metrics = {
            "chunk_index": self.current_chunk_index,
            "provider": "openai",
            "model": result.model,
            "input_tokens": getattr(usage, "prompt_tokens", 0),
            "output_tokens": getattr(usage, "completion_tokens", 0),
            "cached_tokens": cached_tokens,
            "elapsed_ms": elapsed_ms,
        }
        self.calls.append(metrics)

    def record_openai_response(self, result: Any, elapsed_ms: float):
        """Extract cache metrics from OpenAI responses (beta structured output) API."""
        usage = result.usage
        cached_tokens = 0
        # Responses API uses input_tokens/output_tokens directly
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0

        # Check for cached tokens in input_tokens_details
        if hasattr(usage, "input_tokens_details") and usage.input_tokens_details:
            cached_tokens = getattr(usage.input_tokens_details, "cached_tokens", 0) or 0

        metrics = {
            "chunk_index": self.current_chunk_index,
            "provider": "openai",
            "model": result.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "elapsed_ms": elapsed_ms,
        }
        self.calls.append(metrics)

    def reset(self):
        self.calls.clear()
        self.current_chunk_index = -1

    def summary(self) -> dict[str, Any]:
        """Aggregate metrics across all calls."""
        if not self.calls:
            return {"total_calls": 0}

        provider = self.calls[0]["provider"]
        total_input = sum(c.get("input_tokens", 0) for c in self.calls)
        total_output = sum(c.get("output_tokens", 0) for c in self.calls)
        total_elapsed = sum(c.get("elapsed_ms", 0) for c in self.calls)

        result = {
            "total_calls": len(self.calls),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_elapsed_ms": round(total_elapsed, 1),
        }

        if provider == "anthropic":
            cache_creation = sum(c.get("cache_creation_input_tokens", 0) for c in self.calls)
            cache_read = sum(c.get("cache_read_input_tokens", 0) for c in self.calls)
            result["cache_creation_input_tokens"] = cache_creation
            result["cache_read_input_tokens"] = cache_read
            result["cache_hit_rate"] = (
                f"{cache_read / (cache_creation + cache_read) * 100:.1f}%"
                if (cache_creation + cache_read) > 0
                else "N/A"
            )
            # Cost estimate (Sonnet 4.5 pricing: $3/M input, $15/M output, cache write $3.75/M, cache read $0.30/M)
            uncached_input = total_input - cache_creation - cache_read
            cost = (
                uncached_input * 3.0 / 1_000_000
                + cache_creation * 3.75 / 1_000_000
                + cache_read * 0.30 / 1_000_000
                + total_output * 15.0 / 1_000_000
            )
            result["estimated_cost_usd"] = round(cost, 4)
        else:
            cached = sum(c.get("cached_tokens", 0) for c in self.calls)
            result["cached_tokens"] = cached
            result["cache_hit_rate"] = (
                f"{cached / total_input * 100:.1f}%" if total_input > 0 else "N/A"
            )
            # Cost estimate (GPT-4o-mini: $0.15/M input, $0.60/M output, cached 50% discount)
            model = self.calls[0].get("model", "")
            if "gpt-4o-mini" in model:
                uncached = total_input - cached
                cost = (
                    uncached * 0.15 / 1_000_000
                    + cached * 0.075 / 1_000_000
                    + total_output * 0.60 / 1_000_000
                )
            else:
                # GPT-4o pricing
                uncached = total_input - cached
                cost = (
                    uncached * 2.50 / 1_000_000
                    + cached * 1.25 / 1_000_000
                    + total_output * 10.0 / 1_000_000
                )
            result["estimated_cost_usd"] = round(cost, 4)

        # Per-chunk breakdown
        chunks = defaultdict(list)
        for c in self.calls:
            chunks[c["chunk_index"]].append(c)

        result["chunks_processed"] = len(chunks)
        result["avg_calls_per_chunk"] = round(len(self.calls) / len(chunks), 1) if chunks else 0

        return result

    def per_chunk_summary(self) -> list[dict[str, Any]]:
        """Per-chunk breakdown of metrics."""
        chunks = defaultdict(list)
        for c in self.calls:
            chunks[c["chunk_index"]].append(c)

        summaries = []
        for idx in sorted(chunks.keys()):
            calls = chunks[idx]
            provider = calls[0]["provider"]
            s = {
                "chunk_index": idx,
                "calls": len(calls),
                "input_tokens": sum(c.get("input_tokens", 0) for c in calls),
                "output_tokens": sum(c.get("output_tokens", 0) for c in calls),
                "elapsed_ms": round(sum(c.get("elapsed_ms", 0) for c in calls), 1),
            }
            if provider == "anthropic":
                s["cache_creation"] = sum(c.get("cache_creation_input_tokens", 0) for c in calls)
                s["cache_read"] = sum(c.get("cache_read_input_tokens", 0) for c in calls)
            else:
                s["cached_tokens"] = sum(c.get("cached_tokens", 0) for c in calls)
            summaries.append(s)

        return summaries


# Global metrics collector
_metrics = MetricsCollector()


def _patch_anthropic_client(anthropic_client):
    """Monkey-patch AsyncAnthropic to intercept messages.create() for metrics."""
    original_create = anthropic_client.messages.create

    @wraps(original_create)
    async def instrumented_create(*args, **kwargs):
        start = time.perf_counter()
        result = await original_create(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        _metrics.record_anthropic(result, elapsed_ms)
        return result

    anthropic_client.messages.create = instrumented_create
    return anthropic_client


def _patch_openai_client(openai_client):
    """Monkey-patch AsyncOpenAI to intercept API calls for metrics.

    Graphiti's OpenAIClient uses two API paths:
    1. client.chat.completions.create — for regular JSON completions
    2. client.responses.parse — for structured output (beta API)

    We patch both to capture usage metrics.
    """
    # 1. Patch chat.completions.create
    completions = openai_client.chat.completions
    original_completions_create = completions.create

    async def instrumented_completions_create(*args, **kwargs):
        start = time.perf_counter()
        result = await original_completions_create(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        _metrics.record_openai(result, elapsed_ms)
        return result

    completions.create = instrumented_completions_create

    # 2. Patch responses.parse (structured output API)
    if hasattr(openai_client, 'responses'):
        responses = openai_client.responses
        original_parse = responses.parse

        async def instrumented_parse(*args, **kwargs):
            start = time.perf_counter()
            result = await original_parse(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            # responses.parse returns a different format — extract usage
            _metrics.record_openai_response(result, elapsed_ms)
            return result

        responses.parse = instrumented_parse

    return openai_client


# ============================================================================
# Client Factory — create LLM clients with/without cache optimization
# ============================================================================

def create_benchmark_anthropic_client(cache_enabled: bool):
    """Create Anthropic Graphiti LLM client with metrics instrumentation."""
    from graphiti_core.llm_client.anthropic_client import AnthropicClient
    from graphiti_core.llm_client.config import LLMConfig

    from src.config import graphrag_settings
    from src.graphrag.cached_anthropic_client import CachedAnthropicClient

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    model = graphrag_settings.GRAPHITI_ANTHROPIC_MODEL

    config = LLMConfig(
        api_key=api_key,
        model=model,
        temperature=0.1,
        max_tokens=16000,
    )

    from anthropic import AsyncAnthropic
    raw_client = AsyncAnthropic(api_key=api_key, max_retries=1)
    _patch_anthropic_client(raw_client)

    if cache_enabled:
        llm_client = CachedAnthropicClient(config=config, cache=False, client=raw_client)
    else:
        llm_client = AnthropicClient(config=config, cache=False, client=raw_client)

    return llm_client, model


def create_benchmark_openai_client(cache_enabled: bool):
    """Create OpenAI Graphiti LLM client with metrics instrumentation."""
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_client import OpenAIClient

    from src.graphrag.cached_openai_client import CacheFriendlyOpenAIClient

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    base_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    config = LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=0.1,
        max_tokens=16000,
    )

    if cache_enabled:
        llm_client = CacheFriendlyOpenAIClient(config=config, cache=False)
    else:
        llm_client = OpenAIClient(config=config, cache=False)

    # Patch the internal AsyncOpenAI client (Graphiti stores it as .client)
    _patch_openai_client(llm_client.client)

    return llm_client, model


# ============================================================================
# Document Processing — process chunks through Graphiti add_episode()
# ============================================================================

async def run_benchmark_test(
    llm_client,
    chunks: list[dict],
    test_name: str,
    max_chunks: int = 0,
    database: str = "",
    verbose: bool = False,
) -> dict[str, Any]:
    """Process chunks through Graphiti and collect metrics.

    Args:
        llm_client: Graphiti LLMClient to use
        chunks: Pre-chunked document
        test_name: Human-readable test name
        max_chunks: Max chunks to process (0 = all)
        database: Neo4j database name
        verbose: Print per-chunk progress

    Returns:
        Test results with metrics
    """
    from graphiti_core import Graphiti
    from graphiti_core.driver.neo4j_driver import Neo4jDriver
    from graphiti_core.nodes import EpisodeType

    from src.flows.shared.apisix_llm_client import create_apisix_graphiti_embedder
    from src.graphrag.political_schema_v5 import (
        EDGE_TYPE_MAP_GENERAL as EDGE_TYPE_MAP,
        EDGE_TYPE_REGISTRY_GENERAL as EDGE_TYPE_REGISTRY,
        ENTITY_TYPE_REGISTRY_GENERAL as ENTITY_TYPE_REGISTRY,
    )

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = database or os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")
    group_id = f"benchmark_{test_name.replace(' ', '_').lower()}_{int(time.time())}"

    embedder = create_apisix_graphiti_embedder()

    neo4j_driver = Neo4jDriver(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        database=neo4j_database,
    )

    graphiti = Graphiti(
        llm_client=llm_client,
        embedder=embedder,
        graph_driver=neo4j_driver,
    )

    await graphiti.build_indices_and_constraints()

    _metrics.reset()
    test_start = time.perf_counter()

    chunks_to_process = chunks[:max_chunks] if max_chunks > 0 else chunks
    previous_episode_uuid = None
    successful = 0
    failed = 0
    chunk_extractions = []

    print(f"\n  Processing {len(chunks_to_process)} chunks...")

    for chunk in chunks_to_process:
        chunk_index = chunk["chunk_index"]
        _metrics.current_chunk_index = chunk_index

        try:
            episode_name = f"benchmark_{test_name}_chunk_{chunk_index}"
            source_desc = f"Benchmark chunk {chunk_index + 1}/{len(chunks_to_process)}"
            reference_time = datetime.now()
            previous_episodes = [previous_episode_uuid] if previous_episode_uuid else None

            if verbose:
                print(f"    Chunk {chunk_index + 1}/{len(chunks_to_process)}...", end="", flush=True)

            result = await graphiti.add_episode(
                name=episode_name,
                episode_body=chunk["text"],
                source_description=source_desc,
                reference_time=reference_time,
                source=EpisodeType.text,
                group_id=group_id,
                entity_types=ENTITY_TYPE_REGISTRY,
                edge_types=EDGE_TYPE_REGISTRY,
                edge_type_map=EDGE_TYPE_MAP,
                previous_episode_uuids=previous_episodes,
            )

            episode_uuid = result.episode.uuid if hasattr(result, "episode") else None
            previous_episode_uuid = episode_uuid

            # Extract entity names and edge facts for quality comparison
            entity_names = []
            entity_types = []
            if hasattr(result, "nodes"):
                for node in result.nodes:
                    name = getattr(node, "name", "?")
                    label = getattr(node, "label", "Entity")
                    entity_names.append(name)
                    entity_types.append(f"{name} [{label}]")

            edge_facts = []
            if hasattr(result, "edges"):
                for edge in result.edges:
                    fact = getattr(edge, "fact", getattr(edge, "name", "?"))
                    edge_facts.append(fact)

            entities = len(entity_names)
            edges = len(edge_facts)

            chunk_extraction = {
                "chunk_index": chunk_index,
                "entity_count": entities,
                "edge_count": edges,
                "entity_names": sorted(entity_names),
                "entity_types": sorted(entity_types),
                "edge_facts": edge_facts,
            }
            chunk_extractions.append(chunk_extraction)

            if verbose:
                print(f" {entities} entities, {edges} edges")

            successful += 1

        except Exception as e:
            failed += 1
            if verbose:
                print(f" ERROR: {e}")
            logger.error(f"Benchmark chunk {chunk_index} failed", error=str(e))

    test_elapsed = (time.perf_counter() - test_start) * 1000

    await graphiti.close()

    return {
        "test_name": test_name,
        "group_id": group_id,
        "total_test_time_ms": round(test_elapsed, 1),
        "chunks_processed": successful,
        "chunks_failed": failed,
        "metrics": _metrics.summary(),
        "per_chunk": _metrics.per_chunk_summary(),
        "extractions": chunk_extractions,
    }


# ============================================================================
# Main benchmark orchestration
# ============================================================================

def chunk_document(doc_path: Path) -> list[dict]:
    """Read and chunk a document."""
    from src.config import graphrag_settings
    from src.flows.data_ingestion.document_chunker import HybridDocumentChunker
    from src.flows.data_ingestion.document_preprocessor import preprocess_document

    content = doc_path.read_text(encoding="utf-8")
    content = preprocess_document(content, enable_link_removal=True)

    chunker = HybridDocumentChunker(
        max_tokens=graphrag_settings.MAX_EPISODE_TOKENS,
        overlap_ratio=graphrag_settings.CHUNK_OVERLAP_PERCENTAGE / 100,
        max_chunks_per_document=0,  # Unlimited for benchmark
    )
    return chunker.create_chunks(content)


def print_comparison(results: list[dict]):
    """Print a comparison table of benchmark results."""
    print("\n" + "=" * 90)
    print("BENCHMARK COMPARISON")
    print("=" * 90)

    # Header
    print(
        f"{'Test':<35} {'Calls':>6} {'Input':>8} {'Cached':>8} "
        f"{'Output':>8} {'Cache%':>7} {'Cost':>8} {'Time':>8}"
    )
    print("-" * 90)

    for r in results:
        m = r["metrics"]
        test_name = r["test_name"]
        calls = m.get("total_calls", 0)
        input_tok = m.get("total_input_tokens", 0)
        output_tok = m.get("total_output_tokens", 0)
        cost = m.get("estimated_cost_usd", 0)
        time_s = r.get("total_test_time_ms", 0) / 1000

        # Provider-specific cached tokens
        if m.get("cache_read_input_tokens") is not None:
            cached = m.get("cache_read_input_tokens", 0)
        else:
            cached = m.get("cached_tokens", 0)

        cache_pct = m.get("cache_hit_rate", "N/A")

        print(
            f"{test_name:<35} {calls:>6} {input_tok:>8,} {cached:>8,} "
            f"{output_tok:>8,} {cache_pct:>7} ${cost:>7.4f} {time_s:>7.1f}s"
        )

    print("=" * 90)

    # Savings comparison
    if len(results) >= 2:
        print("\nSAVINGS ANALYSIS:")
        # Group by provider
        providers = defaultdict(list)
        for r in results:
            provider = "anthropic" if "Anthropic" in r["test_name"] else "openai"
            providers[provider].append(r)

        for provider, runs in providers.items():
            if len(runs) == 2:
                # Find cached vs uncached
                cached_run = next(
                    (r for r in runs if "WITH" in r["test_name"]), None
                )
                uncached_run = next(
                    (r for r in runs if "WITHOUT" in r["test_name"]), None
                )
                if cached_run and uncached_run:
                    c_cost = cached_run["metrics"].get("estimated_cost_usd", 0)
                    u_cost = uncached_run["metrics"].get("estimated_cost_usd", 0)
                    c_time = cached_run.get("total_test_time_ms", 0)
                    u_time = uncached_run.get("total_test_time_ms", 0)

                    cost_savings = (
                        f"{(1 - c_cost / u_cost) * 100:.1f}%" if u_cost > 0 else "N/A"
                    )
                    time_savings = (
                        f"{(1 - c_time / u_time) * 100:.1f}%" if u_time > 0 else "N/A"
                    )

                    print(
                        f"  {provider.upper()}: "
                        f"Cost savings: {cost_savings} "
                        f"(${u_cost:.4f} -> ${c_cost:.4f}), "
                        f"Time savings: {time_savings} "
                        f"({u_time / 1000:.1f}s -> {c_time / 1000:.1f}s)"
                    )

    print()


def print_per_chunk_details(results: list[dict]):
    """Print per-chunk metrics for each test."""
    for r in results:
        print(f"\n--- {r['test_name']} (per-chunk) ---")
        per_chunk = r.get("per_chunk", [])
        if not per_chunk:
            print("  No per-chunk data")
            continue

        is_anthropic = any("cache_creation" in c for c in per_chunk)

        if is_anthropic:
            print(f"  {'Chunk':>6} {'Calls':>6} {'Input':>8} {'Create':>8} {'Read':>8} {'Output':>8} {'Time':>8}")
            print("  " + "-" * 60)
            for c in per_chunk:
                print(
                    f"  {c['chunk_index']:>6} {c['calls']:>6} "
                    f"{c['input_tokens']:>8,} {c.get('cache_creation', 0):>8,} "
                    f"{c.get('cache_read', 0):>8,} {c['output_tokens']:>8,} "
                    f"{c['elapsed_ms']:>7.0f}ms"
                )
        else:
            print(f"  {'Chunk':>6} {'Calls':>6} {'Input':>8} {'Cached':>8} {'Output':>8} {'Time':>8}")
            print("  " + "-" * 55)
            for c in per_chunk:
                print(
                    f"  {c['chunk_index']:>6} {c['calls']:>6} "
                    f"{c['input_tokens']:>8,} {c.get('cached_tokens', 0):>8,} "
                    f"{c['output_tokens']:>8,} {c['elapsed_ms']:>7.0f}ms"
                )


def print_extraction_comparison(results: list[dict]):
    """Compare entities and edges extracted across WITH/WITHOUT cache runs."""
    # Group by provider
    providers = defaultdict(list)
    for r in results:
        provider = "anthropic" if "Anthropic" in r["test_name"] else "openai"
        providers[provider].append(r)

    for provider, runs in providers.items():
        if len(runs) != 2:
            continue

        cached_run = next((r for r in runs if "WITH" in r["test_name"]), None)
        uncached_run = next((r for r in runs if "WITHOUT" in r["test_name"]), None)
        if not cached_run or not uncached_run:
            continue

        cached_ext = cached_run.get("extractions", [])
        uncached_ext = uncached_run.get("extractions", [])

        print(f"\n{'='*90}")
        print(f"EXTRACTION QUALITY COMPARISON: {provider.upper()}")
        print(f"{'='*90}")

        # Per-chunk comparison
        total_cached_entities = 0
        total_uncached_entities = 0
        total_cached_edges = 0
        total_uncached_edges = 0
        all_cached_entities = set()
        all_uncached_entities = set()

        max_chunks = max(len(cached_ext), len(uncached_ext))
        for i in range(max_chunks):
            c_chunk = cached_ext[i] if i < len(cached_ext) else None
            u_chunk = uncached_ext[i] if i < len(uncached_ext) else None

            c_entities = set(c_chunk["entity_names"]) if c_chunk else set()
            u_entities = set(u_chunk["entity_names"]) if u_chunk else set()
            c_edges = c_chunk["edge_count"] if c_chunk else 0
            u_edges = u_chunk["edge_count"] if u_chunk else 0

            total_cached_entities += len(c_entities)
            total_uncached_entities += len(u_entities)
            total_cached_edges += c_edges
            total_uncached_edges += u_edges
            all_cached_entities.update(c_entities)
            all_uncached_entities.update(u_entities)

            common = c_entities & u_entities
            only_cached = c_entities - u_entities
            only_uncached = u_entities - c_entities

            print(f"\n  Chunk {i}:")
            print(f"    WITH cache:    {len(c_entities)} entities, {c_edges} edges")
            print(f"    WITHOUT cache: {len(u_entities)} entities, {u_edges} edges")
            print(f"    Common entities ({len(common)}): {', '.join(sorted(common)) if common else '(none)'}")
            if only_cached:
                print(f"    Only WITH cache ({len(only_cached)}): {', '.join(sorted(only_cached))}")
            if only_uncached:
                print(f"    Only WITHOUT cache ({len(only_uncached)}): {', '.join(sorted(only_uncached))}")

            # Show entity types for comparison
            if c_chunk and c_chunk.get("entity_types"):
                print(f"    WITH cache types: {', '.join(c_chunk['entity_types'])}")
            if u_chunk and u_chunk.get("entity_types"):
                print(f"    WITHOUT cache types: {', '.join(u_chunk['entity_types'])}")

            # Show edge facts
            if c_chunk and c_chunk.get("edge_facts"):
                print(f"    WITH cache edges:")
                for fact in c_chunk["edge_facts"]:
                    print(f"      - {fact[:120]}")
            if u_chunk and u_chunk.get("edge_facts"):
                print(f"    WITHOUT cache edges:")
                for fact in u_chunk["edge_facts"]:
                    print(f"      - {fact[:120]}")

        # Overall summary
        common_all = all_cached_entities & all_uncached_entities
        only_cached_all = all_cached_entities - all_uncached_entities
        only_uncached_all = all_uncached_entities - all_cached_entities

        print(f"\n  {'─'*60}")
        print(f"  OVERALL {provider.upper()} SUMMARY:")
        print(f"    WITH cache:    {total_cached_entities} entities, {total_cached_edges} edges ({len(all_cached_entities)} unique entities)")
        print(f"    WITHOUT cache: {total_uncached_entities} entities, {total_uncached_edges} edges ({len(all_uncached_entities)} unique entities)")
        print(f"    Entity overlap: {len(common_all)} common, {len(only_cached_all)} only-cached, {len(only_uncached_all)} only-uncached")

        if len(all_cached_entities) > 0 and len(all_uncached_entities) > 0:
            jaccard = len(common_all) / len(all_cached_entities | all_uncached_entities)
            print(f"    Jaccard similarity: {jaccard:.1%}")

            verdict = (
                "EXCELLENT — nearly identical extraction"
                if jaccard >= 0.8
                else "GOOD — minor differences"
                if jaccard >= 0.6
                else "MODERATE — some divergence"
                if jaccard >= 0.4
                else "POOR — significant divergence"
            )
            print(f"    Verdict: {verdict}")

        if only_cached_all:
            print(f"\n    Entities found ONLY with cache: {', '.join(sorted(only_cached_all))}")
        if only_uncached_all:
            print(f"    Entities found ONLY without cache: {', '.join(sorted(only_uncached_all))}")

    print()


async def main():
    parser = argparse.ArgumentParser(
        description="Benchmark prompt cache optimization for Graphiti LLM calls"
    )
    parser.add_argument("file_path", type=str, help="Path to the markdown file to benchmark")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "both"],
        default="both",
        help="Which provider(s) to benchmark (default: both)",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=0,
        help="Max chunks to process per test (0 = all, recommend 3-5 for quick tests)",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="",
        help="Neo4j database to use (default: from env NEO4J_DATABASE)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-chunk progress during processing",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show per-chunk detailed metrics in output",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="Save results to JSON file",
    )

    args = parser.parse_args()

    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    print("=" * 70)
    print("PROMPT CACHE OPTIMIZATION BENCHMARK")
    print("=" * 70)
    print(f"Document: {file_path}")
    print(f"Provider: {args.provider}")
    print(f"Database: {args.database or os.getenv('NEO4J_DATABASE', 'politicalmonitoring.v3')}")

    # Chunk the document once
    print("\nChunking document...")
    chunks = chunk_document(file_path)
    total_tokens = sum(c["token_count"] for c in chunks)
    print(f"  {len(chunks)} chunks, {total_tokens:,} total tokens")

    if args.max_chunks > 0:
        print(f"  Limiting to {args.max_chunks} chunks per test")

    results = []

    # ---- Anthropic tests ----
    if args.provider in ("anthropic", "both"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("\nWARNING: ANTHROPIC_API_KEY not set, skipping Anthropic tests")
        else:
            # Test 1: Anthropic WITH cache
            print(f"\n{'='*60}")
            print("TEST 1: Anthropic WITH cache optimization")
            print(f"{'='*60}")
            llm_client, model = create_benchmark_anthropic_client(cache_enabled=True)
            print(f"  Model: {model}")
            print(f"  Client: CachedAnthropicClient")
            result = await run_benchmark_test(
                llm_client, chunks,
                test_name="Anthropic WITH cache",
                max_chunks=args.max_chunks,
                database=args.database,
                verbose=args.verbose,
            )
            results.append(result)
            print(f"  Done: {result['metrics'].get('total_calls', 0)} API calls, "
                  f"${result['metrics'].get('estimated_cost_usd', 0):.4f}")

            # Test 2: Anthropic WITHOUT cache
            print(f"\n{'='*60}")
            print("TEST 2: Anthropic WITHOUT cache optimization")
            print(f"{'='*60}")
            llm_client, model = create_benchmark_anthropic_client(cache_enabled=False)
            print(f"  Model: {model}")
            print(f"  Client: AnthropicClient (plain)")
            result = await run_benchmark_test(
                llm_client, chunks,
                test_name="Anthropic WITHOUT cache",
                max_chunks=args.max_chunks,
                database=args.database,
                verbose=args.verbose,
            )
            results.append(result)
            print(f"  Done: {result['metrics'].get('total_calls', 0)} API calls, "
                  f"${result['metrics'].get('estimated_cost_usd', 0):.4f}")

    # ---- OpenAI tests ----
    if args.provider in ("openai", "both"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("\nWARNING: OPENAI_API_KEY not set, skipping OpenAI tests")
        else:
            # Test 3: OpenAI WITH cache
            print(f"\n{'='*60}")
            print("TEST 3: OpenAI WITH cache optimization")
            print(f"{'='*60}")
            llm_client, model = create_benchmark_openai_client(cache_enabled=True)
            print(f"  Model: {model}")
            print(f"  Client: CacheFriendlyOpenAIClient")
            result = await run_benchmark_test(
                llm_client, chunks,
                test_name="OpenAI WITH cache",
                max_chunks=args.max_chunks,
                database=args.database,
                verbose=args.verbose,
            )
            results.append(result)
            print(f"  Done: {result['metrics'].get('total_calls', 0)} API calls, "
                  f"${result['metrics'].get('estimated_cost_usd', 0):.4f}")

            # Test 4: OpenAI WITHOUT cache
            print(f"\n{'='*60}")
            print("TEST 4: OpenAI WITHOUT cache optimization")
            print(f"{'='*60}")
            llm_client, model = create_benchmark_openai_client(cache_enabled=False)
            print(f"  Model: {model}")
            print(f"  Client: OpenAIClient (plain)")
            result = await run_benchmark_test(
                llm_client, chunks,
                test_name="OpenAI WITHOUT cache",
                max_chunks=args.max_chunks,
                database=args.database,
                verbose=args.verbose,
            )
            results.append(result)
            print(f"  Done: {result['metrics'].get('total_calls', 0)} API calls, "
                  f"${result['metrics'].get('estimated_cost_usd', 0):.4f}")

    # Print comparison
    if results:
        print_comparison(results)

        if args.details:
            print_per_chunk_details(results)

        # Always show extraction quality comparison when we have paired runs
        print_extraction_comparison(results)

        # Save to JSON
        if args.output:
            output_path = Path(args.output)
            with open(output_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results saved to: {output_path}")
    else:
        print("\nNo tests were run. Check API keys and provider selection.")


if __name__ == "__main__":
    asyncio.run(main())
