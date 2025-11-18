#!/usr/bin/env python3
"""
Test script to verify Graphiti is routing LLM calls through APISIX.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path

from graphiti_core import Graphiti
from graphiti_core.llm_client.openai_client import OpenAIClient
from graphiti_core.llm_client.config import LLMConfig
from graphiti_core.nodes import EpisodeType


async def test_graphiti_apisix_routing():
    """Test that Graphiti routes through APISIX."""

    print("🔍 Testing Graphiti APISIX Routing\n")

    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    apisix_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080/v1")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")

    print(f"✓ OPENAI_API_KEY: {'Set' if api_key else 'NOT SET'}")
    print(f"✓ APISIX_GATEWAY_URL: {apisix_url}")
    print(f"✓ NEO4J_URI: {neo4j_uri}\n")

    if not api_key:
        print("❌ OPENAI_API_KEY not set!")
        return

    # Create Graphiti client with APISIX routing
    print("📝 Creating Graphiti client with APISIX routing...")
    config = LLMConfig(
        api_key=api_key,
        model="gpt-4o-mini",
        base_url=apisix_url,  # Route through APISIX
        temperature=0.1
    )
    llm_client = OpenAIClient(config=config, cache=False)

    print(f"   LLM Config base_url: {config.base_url}")
    print(f"   LLM Config model: {config.model}")

    # Initialize Graphiti
    graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password, llm_client=llm_client)
    await graphiti.build_indices_and_constraints()
    print("✓ Graphiti client initialized\n")

    # Create a simple test episode
    print("🧪 Adding test episode to Graphiti...")
    print("   (This should make LLM calls through APISIX)\n")

    test_content = """
    The European Union has implemented the AI Act, a comprehensive regulation
    for artificial intelligence systems. Major tech companies like Google and
    Microsoft must comply with these new rules by 2026.
    """

    try:
        result = await graphiti.add_episode(
            name="test_apisix_routing",
            episode_body=test_content,
            source_description="APISIX routing test",
            reference_time=datetime.now(),
            source=EpisodeType.text
        )

        print(f"✅ Episode added successfully!")
        print(f"   Episode ID: {result.episode.uuid if hasattr(result, 'episode') else 'N/A'}")
        print(f"   Entities extracted: {len(result.nodes) if hasattr(result, 'nodes') else 0}")
        print(f"   Relationships: {len(result.edges) if hasattr(result, 'edges') else 0}\n")

        print("🎯 Check APISIX logs now:")
        print("   docker logs policiytracker-apisix 2>&1 | tail -20")
        print("   Look for POST /v1/chat/completions requests\n")

    except Exception as e:
        print(f"❌ Error: {e}\n")
    finally:
        await graphiti.close()
        print("✓ Graphiti client closed")


if __name__ == "__main__":
    asyncio.run(test_graphiti_apisix_routing())
