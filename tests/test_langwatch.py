"""Test script to verify LangWatch integration with dummy data."""

import asyncio
import json
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import settings


async def test_langwatch_dummy_data():
    """Send dummy agent data to LangWatch to verify integration."""

    print(f"LangWatch enabled: {settings.ENABLE_LANGWATCH}")
    print(f"LangWatch endpoint: {settings.LANGWATCH_ENDPOINT}")
    print(f"LangWatch API key set: {bool(settings.LANGWATCH_API_KEY)}")

    if not settings.ENABLE_LANGWATCH or not settings.LANGWATCH_API_KEY:
        print("ERROR: LangWatch not configured properly")
        return

    import langwatch

    # Initialize LangWatch
    langwatch.setup(
        api_key=settings.LANGWATCH_API_KEY,
        endpoint_url=settings.LANGWATCH_ENDPOINT,
        debug=True,
    )
    print("LangWatch initialized successfully")

    # Create dummy session data
    session_id = "test_session_12345"

    dummy_turns = [
        {
            "turn_number": 1,
            "stop_reason": "tool_use",
            "tool_calls_count": 2,
            "tool_names": ["search_knowledge_graph", "get_entity_info"],
            "input_tokens": 150,
            "output_tokens": 200,
            "total_tokens": 350,
            "model": "claude-sonnet-4-20250514",
        },
        {
            "turn_number": 2,
            "stop_reason": "end_turn",
            "tool_calls_count": 0,
            "tool_names": [],
            "input_tokens": 500,
            "output_tokens": 300,
            "total_tokens": 800,
            "model": "claude-sonnet-4-20250514",
        },
    ]

    dummy_tool_calls = [
        {
            "tool_name": "search_knowledge_graph",
            "tool_use_id": "tool_001",
            "input": {"query": "EU AI Act regulations", "limit": 10},
            "output": {
                "entities": [
                    {
                        "uuid": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "EU AI Act",
                        "type": "Regulation",
                        "status": "Enacted",
                        "effective_date": "2024-08-01",
                        "jurisdiction": "European Union",
                        "description": "Comprehensive AI regulation framework for the EU"
                    },
                    {
                        "uuid": "550e8400-e29b-41d4-a716-446655440002",
                        "name": "European Commission",
                        "type": "Organization",
                        "role": "Regulatory Body",
                        "country": "EU"
                    }
                ],
                "relationships": [
                    {
                        "source": "EU AI Act",
                        "target": "European Commission",
                        "type": "REGULATED_BY",
                        "properties": {"since": "2024-08-01"}
                    }
                ],
                "total_results": 5
            },
            "success": True,
            "execution_time_ms": 234,
            "turn_number": 1,
        },
        {
            "tool_name": "get_entity_info",
            "tool_use_id": "tool_002",
            "input": {"entity_id": "550e8400-e29b-41d4-a716-446655440001"},
            "output": {
                "entity": {
                    "uuid": "550e8400-e29b-41d4-a716-446655440001",
                    "name": "EU AI Act",
                    "type": "Regulation",
                    "status": "Enacted",
                    "effective_date": "2024-08-01",
                    "jurisdiction": "European Union",
                    "risk_categories": ["Unacceptable", "High", "Limited", "Minimal"],
                    "key_requirements": [
                        "Transparency obligations",
                        "Human oversight",
                        "Data governance",
                        "Technical documentation"
                    ],
                    "penalties": {
                        "max_fine": "35M EUR or 7% global turnover",
                        "enforcement_start": "2025-08-01"
                    }
                },
                "related_entities": [
                    {"name": "European Commission", "relationship": "REGULATED_BY"},
                    {"name": "GDPR", "relationship": "COMPLEMENTS"}
                ]
            },
            "success": True,
            "execution_time_ms": 156,
            "turn_number": 1,
        },
    ]

    output_summary = {
        "session_id": session_id,
        "total_turns": len(dummy_turns),
        "total_tool_calls": len(dummy_tool_calls),
        "total_tokens": 1150,
        "model": "claude-sonnet-4-20250514",
        "turns": dummy_turns,
        "tool_calls": dummy_tool_calls,
    }

    user_query = "What are the latest updates on EU AI Act?"
    final_response = "Based on my research, the EU AI Act has several recent updates..."

    print(f"\nSending dummy trace to LangWatch...")
    print(f"Session ID: {session_id}")
    print(f"Turns: {len(dummy_turns)}")
    print(f"Tool calls: {len(dummy_tool_calls)}")

    # Method 1: Using trace context manager directly
    try:
        with langwatch.trace(
            name="test_policy_tracker_query",
            metadata={
                "agent": "PolicyTrackerAgent",
                "thread_id": session_id,
                "test": True,
            },
        ) as trace:
            print(f"Trace created: {trace}")
            print(f"Trace type: {type(trace)}")

            # Update trace with input/output
            if trace:
                trace.update(
                    input=user_query,
                    output=json.dumps(output_summary, indent=2),
                    metadata={
                        "thread_id": session_id,
                        "total_turns": len(dummy_turns),
                        "total_tool_calls": len(dummy_tool_calls),
                        "total_tokens": 1150,
                        "model": "claude-sonnet-4-20250514",
                        "final_response_preview": final_response[:200],
                    },
                )
                print("Trace updated with input/output/metadata")

            # Simulate some work
            await asyncio.sleep(0.1)

        print("\nTrace context closed - data should be sent to LangWatch")

    except Exception as e:
        print(f"ERROR with trace: {e}")
        import traceback
        traceback.print_exc()

    # Force flush the tracer provider
    print("\nForcing flush of tracer provider...")
    try:
        from opentelemetry import trace as otel_trace
        provider = otel_trace.get_tracer_provider()
        if hasattr(provider, 'force_flush'):
            result = provider.force_flush(timeout_millis=10000)
            print(f"Force flush result: {result}")
        else:
            print(f"Provider type: {type(provider)} - no force_flush method")
    except Exception as e:
        print(f"Force flush error: {e}")

    # Give LangWatch time to flush
    print("\nWaiting for LangWatch to flush data...")
    await asyncio.sleep(3)

    print("\n" + "="*50)
    print("TEST COMPLETE")
    print("="*50)
    print(f"\nCheck LangWatch dashboard at: {settings.LANGWATCH_ENDPOINT}")
    print(f"Look for trace named: test_policy_tracker_query")
    print(f"With thread_id: {session_id}")


if __name__ == "__main__":
    asyncio.run(test_langwatch_dummy_data())
