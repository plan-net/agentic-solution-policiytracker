#!/usr/bin/env python3
"""Quick test for Tool 3 (get_entity_relationships) improvements."""

import asyncio
import json
from graphiti_core import Graphiti
from src.chat.tools.entity import EntityRelationshipsTool


async def test_tool3():
    """Quick test of Tool 3 improvements."""
    client = Graphiti("bolt://localhost:7687", "neo4j", "password123")
    tool = EntityRelationshipsTool(graphiti_client=client)

    print("=" * 70)
    print("TOOL 3 (get_entity_relationships) QUICK TEST")
    print("=" * 70)
    print()

    # Test 1: Structured output
    print("TEST 1: Structured output for 'Apple'")
    print("-" * 70)
    result = await tool._arun("Apple", max_relationships=5, output_format="structured")

    if isinstance(result, dict):
        print("✅ Returns dict (structured format)")
        print(f"Entity: {result.get('entity', {}).get('name', 'N/A')}")
        print(f"Total relationships: {result.get('summary', {}).get('total_relationships', 0)}")
        print(f"Outgoing: {result.get('summary', {}).get('outgoing_count', 0)}")
        print(f"Incoming: {result.get('summary', {}).get('incoming_count', 0)}")

        # Test serialization
        try:
            json_str = json.dumps(result)
            print(f"✅ JSON serializable ({len(json_str)} bytes)")
        except TypeError as e:
            print(f"❌ Serialization failed: {e}")
    else:
        print(f"❌ Expected dict, got {type(result)}")

    print()

    # Test 2: Text output
    print("TEST 2: Text output for 'GDPR'")
    print("-" * 70)
    result_text = await tool._arun("GDPR", max_relationships=3, output_format="text")

    if isinstance(result_text, str):
        print("✅ Returns string (text format)")
        print(f"Length: {len(result_text)} chars")
        if "Relationships for:" in result_text:
            print("✅ Contains expected markdown")
        lines = result_text.split("\n")[:10]
        for line in lines:
            print(f"  {line}")
    else:
        print(f"❌ Expected str, got {type(result_text)}")

    print()

    # Test 3: Bidirectional flag
    print("TEST 3: Unidirectional (outgoing only) for 'Meta'")
    print("-" * 70)
    result_uni = await tool._arun(
        "Meta", max_relationships=5, include_bidirectional=False, output_format="structured"
    )

    if isinstance(result_uni, dict):
        outgoing = len(result_uni.get("relationships", {}).get("outgoing", []))
        incoming = len(result_uni.get("relationships", {}).get("incoming", []))
        print(f"Outgoing: {outgoing}")
        print(f"Incoming: {incoming}")
        if incoming == 0:
            print("✅ Correctly excludes incoming relationships")
        else:
            print("⚠️ Should have 0 incoming when include_bidirectional=False")
    else:
        print(f"❌ Expected dict, got {type(result_uni)}")

    print()
    print("=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)

    await client.close()


if __name__ == "__main__":
    asyncio.run(test_tool3())
