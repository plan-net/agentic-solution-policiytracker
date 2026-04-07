"""Test LangWatch by sending trace directly via REST API."""

import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from src.config import settings


def test_langwatch_rest_api():
    """Send a trace directly to LangWatch REST API with rich structured data."""

    print(f"LangWatch endpoint: {settings.LANGWATCH_ENDPOINT}")
    print(f"API key set: {bool(settings.LANGWATCH_API_KEY)}")

    if not settings.LANGWATCH_API_KEY:
        print("ERROR: LANGWATCH_API_KEY not set")
        return

    # Create trace data
    trace_id = uuid.uuid4().hex
    session_id = f"test_direct_{int(time.time())}"

    # Rich structured output with complete tool call data (similar to what the agent captures)
    output_summary = {
        "session_id": session_id,
        "total_turns": 2,
        "total_tool_calls": 2,
        "total_tokens": 1150,
        "model": "claude-sonnet-4-20250514",
        "turns": [
            {
                "turn_number": 1,
                "stop_reason": "tool_use",
                "tool_calls_count": 2,
                "tool_names": ["search_knowledge_graph", "get_entity_info"],
                "input_tokens": 150,
                "output_tokens": 200,
                "total_tokens": 350
            },
            {
                "turn_number": 2,
                "stop_reason": "end_turn",
                "tool_calls_count": 0,
                "tool_names": [],
                "input_tokens": 500,
                "output_tokens": 300,
                "total_tokens": 800
            }
        ],
        "tool_calls": [
            {
                "tool_name": "search_knowledge_graph",
                "tool_use_id": "tool_001",
                "input": json.dumps({
                    "query": "EU AI Act regulations",
                    "limit": 10
                }, indent=2),
                "output": json.dumps({
                    "entities": [
                        {
                            "uuid": "550e8400-e29b-41d4-a716-446655440001",
                            "name": "EU AI Act",
                            "type": "Regulation",
                            "status": "Enacted",
                            "effective_date": "2024-08-01",
                            "jurisdiction": "European Union",
                            "description": "Comprehensive AI regulation framework for the EU",
                            "risk_categories": ["Unacceptable", "High", "Limited", "Minimal"],
                            "key_requirements": [
                                "Transparency obligations",
                                "Human oversight",
                                "Data governance",
                                "Technical documentation"
                            ]
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
                }, indent=2),
                "success": True,
                "execution_time_ms": 234,
                "turn_number": 1
            },
            {
                "tool_name": "get_entity_info",
                "tool_use_id": "tool_002",
                "input": json.dumps({
                    "entity_id": "550e8400-e29b-41d4-a716-446655440001"
                }, indent=2),
                "output": json.dumps({
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
                }, indent=2),
                "success": True,
                "execution_time_ms": 156,
                "turn_number": 1
            }
        ]
    }

    # Build the trace payload for LangWatch collector API
    trace_data = {
        "trace_id": trace_id,
        "spans": [
            {
                "type": "llm",
                "name": "policy_tracker_query",
                "span_id": uuid.uuid4().hex[:16],
                "trace_id": trace_id,
                "input": {"type": "text", "value": "What are the latest updates on EU AI Act?"},
                "output": {
                    "type": "json",
                    "value": json.dumps(output_summary, default=str)
                },
                "timestamps": {
                    "started_at": int(time.time() * 1000) - 5000,
                    "finished_at": int(time.time() * 1000)
                },
                "metrics": {
                    "prompt_tokens": 650,
                    "completion_tokens": 500
                },
                "params": {
                    "model": "claude-sonnet-4-20250514"
                }
            }
        ],
        "metadata": {
            "thread_id": session_id,
            "user_id": "policy_tracker",
            "labels": ["agent", "policy_tracker", "test"],
            "total_turns": 2,
            "total_tool_calls": 2
        }
    }

    # Send to LangWatch collector endpoint
    collector_url = f"{settings.LANGWATCH_ENDPOINT}/api/collector"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": settings.LANGWATCH_API_KEY,
    }

    print(f"\nSending trace to: {collector_url}")
    print(f"Trace ID: {trace_id}")
    print(f"Session ID: {session_id}")
    print(f"Output summary size: {len(json.dumps(output_summary))} bytes")

    try:
        response = requests.post(
            collector_url,
            headers=headers,
            json=trace_data,
            timeout=10
        )
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text[:500]}")

        if response.status_code == 200:
            print("\n✓ Trace sent successfully!")
            print(f"Check LangWatch at: {settings.LANGWATCH_ENDPOINT}")
            print(f"Look for trace_id: {trace_id}")
            print(f"Thread ID (session): {session_id}")
        else:
            print(f"\n✗ Failed to send trace")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


def test_langwatch_config_rest_api():
    """Test the langwatch_config.send_trace_via_rest_api method."""
    from src.chat.observability.langwatch_config import langwatch_config

    print("\n" + "=" * 60)
    print("Testing langwatch_config.send_trace_via_rest_api()")
    print("=" * 60)

    # Enable langwatch for this test
    langwatch_config.enabled = True
    langwatch_config._initialized = True

    session_id = f"test_config_{int(time.time())}"

    # Simulate session data like the agent would collect
    # Note: input and output should be objects (not JSON strings) for proper serialization
    session_data = {
        "session_id": session_id,
        "user_query": "What is the EU AI Act?",
        "final_response": "The EU AI Act is comprehensive regulation...",
        "total_tokens": 1150,
        "model": "claude-sonnet-4-20250514",
        "turns": [
            {
                "turn_number": 1,
                "stop_reason": "tool_use",
                "tool_calls_count": 1,
                "tool_names": ["search_knowledge_graph"],
                "input_tokens": 150,
                "output_tokens": 200,
                "total_tokens": 350,
                "model": "claude-sonnet-4-20250514"
            },
            {
                "turn_number": 2,
                "stop_reason": "end_turn",
                "tool_calls_count": 0,
                "tool_names": [],
                "input_tokens": 500,
                "output_tokens": 300,
                "total_tokens": 800,
                "model": "claude-sonnet-4-20250514"
            }
        ],
        "tool_calls": [
            {
                "tool_name": "search_knowledge_graph",
                "tool_use_id": "test_001",
                "input": {"query": "EU AI Act"},  # Object, not JSON string
                "output": {  # Object, not JSON string
                    "entities": [
                        {
                            "uuid": "550e8400-e29b-41d4-a716-446655440001",
                            "name": "EU AI Act",
                            "type": "Regulation",
                            "status": "Enacted",
                            "effective_date": "2024-08-01",
                            "jurisdiction": "European Union"
                        }
                    ],
                    "relationships": [
                        {
                            "source": "EU AI Act",
                            "target": "European Commission",
                            "type": "REGULATED_BY"
                        }
                    ]
                },
                "success": True,
                "execution_time_ms": 234,
                "turn_number": 1
            }
        ]
    }

    print(f"Session ID: {session_id}")
    print(f"Turns: {len(session_data['turns'])}")
    print(f"Tool calls: {len(session_data['tool_calls'])}")

    success = langwatch_config.send_trace_via_rest_api(session_data)

    if success:
        print("\n✓ Trace sent via langwatch_config.send_trace_via_rest_api()")
    else:
        print("\n✗ Failed to send trace")


if __name__ == "__main__":
    test_langwatch_rest_api()
    test_langwatch_config_rest_api()
