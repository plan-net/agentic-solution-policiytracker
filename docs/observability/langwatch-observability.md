# LangWatch Observability Integration

This document describes the LangWatch observability integration for the Policy Tracker agents, enabling comprehensive tracing and monitoring of agent sessions, tool calls, and LLM interactions.

## Overview

The integration captures detailed observability data including:
- **Session-level traces**: Complete lifecycle of each user query
- **Turn-by-turn tracking**: Each iteration of the agentic loop
- **Tool call data**: Full input/output for every MCP tool execution
- **Token usage**: Per-turn and cumulative token consumption
- **Knowledge graph data**: Entity and relationship information from queries

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# LangWatch Observability
ENABLE_LANGWATCH=true
LANGWATCH_API_KEY=your-langwatch-api-key
LANGWATCH_ENDPOINT=http://localhost:5560

# Optional: OpenTelemetry settings (for advanced instrumentation)
LANGWATCH_OTLP_ENDPOINT=http://localhost:5560/api/otel/v1/traces
ENABLE_ANTHROPIC_INSTRUMENTATION=true
```

### Settings Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_LANGWATCH` | bool | `false` | Enable/disable LangWatch integration |
| `LANGWATCH_API_KEY` | string | None | API key for LangWatch authentication |
| `LANGWATCH_ENDPOINT` | string | `http://localhost:5560` | LangWatch server endpoint |
| `LANGWATCH_OTLP_ENDPOINT` | string | Auto-derived | OTLP endpoint for OpenTelemetry traces |
| `ENABLE_ANTHROPIC_INSTRUMENTATION` | bool | `true` | Enable auto-instrumentation of Anthropic SDK |

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Policy Tracker Agent                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   query()   │  │ _execute_   │  │ capture_agentic_    │  │
│  │             │──│   tool()    │──│      turn()         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                │                    │              │
│         ▼                ▼                    ▼              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              LangWatchConfig (Singleton)               │  │
│  │  - Session collector (accumulates data per session)    │  │
│  │  - Smart truncation (preserves entity/relationship)    │  │
│  │  - Embedding filtering (removes large vectors)         │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
└────────────────────────────│─────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   LangWatch     │
                    │   REST API      │
                    │  /api/collector │
                    └─────────────────┘
```

### Data Flow

1. **Session Start**: `set_session_query()` initializes a session collector
2. **Each Turn**: `capture_agentic_turn()` records turn metadata and token usage
3. **Tool Calls**: `capture_tool_call_with_response()` stores full input/output
4. **Session End**: `finalize_session()` aggregates data, then `send_trace_via_rest_api()` sends to LangWatch

## Key Features

### 1. Smart Truncation

Large data is truncated while preserving critical information:

```python
# Priority keys (always preserved first):
priority_keys = {
    'name', 'type', 'uuid', 'id', 'status', 'success', 'error', 'tool_name',
    # Knowledge graph critical keys
    'entities', 'relationships', 'nodes', 'edges', 'properties',
    'entity', 'relationship', 'node', 'source', 'target'
}

# Verbose keys (truncated aggressively to 500 bytes):
verbose_keys = {'description', 'summary', 'content', 'text', 'body', 'raw_response', 'fact'}
```

### 2. Embedding Filtering

Embedding vectors are automatically filtered to reduce payload size:

```python
# Filtered keys:
embedding_keys = {
    'embedding', 'embeddings', 'vector', 'vectors', 'embed',
    'dense_vector', 'sparse_vector', 'text_embedding', 'node_embedding',
    'relationship_embedding', 'fact_embedding'
}

# Also filters: Lists with 100+ numeric elements (detected as embedding vectors)
```

### 3. Payload Size Management

- **Per-tool-call limit**: 50KB for output, 10KB for input
- **Minimum budget**: 10KB per tool call (even with many calls)
- **Total payload limit**: 1MB before truncation kicks in

## Usage

### In Policy Tracker Agent

The integration is automatic when `ENABLE_LANGWATCH=true`. Key integration points:

```python
# src/claude_agent/agent.py

class PolicyTrackerAgent:
    def __init__(self):
        # Initialize LangWatch in manual mode (one trace per session)
        langwatch_config.initialize(instrumentation_mode="manual")

    @langwatch_config.trace(name="policy_tracker_query", metadata={"agent": "PolicyTrackerAgent"})
    async def query(self, user_message: str, session_id: Optional[str] = None):
        # Set session context
        langwatch_config.set_thread_id(session_id)
        langwatch_config.set_session_query(session_id, user_message)

        # ... agentic loop ...

        # Each turn is captured
        langwatch_config.capture_agentic_turn(
            turn_number=turn_number,
            session_id=session_id,
            stop_reason=response.stop_reason,
            tool_calls=tool_calls_in_turn,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )

        # Tool calls are captured with full data
        langwatch_config.capture_tool_call_with_response(
            tool_name=tool_name,
            tool_use_id=tool_use_id,
            tool_input=tool_input,
            tool_output=result,
            execution_time=execution_time,
            success=True,
            turn_number=turn_number,
            session_id=session_id,
        )

        # Finalize and send trace
        langwatch_config.set_session_response(session_id, response_text)
        session_data = langwatch_config.finalize_session(session_id)
        langwatch_config.send_trace_via_rest_api(session_data)
```

### In Weekly Report Agent

Same pattern applies to the weekly report agent:

```python
# src/flows/weekly_report_sdk/agent/report_agent.py

@langwatch_config.trace(name="weekly_report_generation", metadata={"agent": "WeeklyReportAgent"})
async def generate_report(self, week_start, week_end, week_label, ...):
    # ... similar integration ...
```

## Trace Data Structure

### Session Data (sent to LangWatch)

```json
{
  "session_id": "session_abc123",
  "user_query": "What is the EU AI Act?",
  "final_response": "The EU AI Act is...",
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
    }
  ],
  "tool_calls": [
    {
      "tool_name": "search_knowledge_graph",
      "tool_use_id": "tool_001",
      "input": {"query": "EU AI Act"},
      "output": {
        "entities": [
          {"uuid": "...", "name": "EU AI Act", "type": "Regulation", "status": "Enacted"}
        ],
        "relationships": [
          {"source": "EU AI Act", "target": "European Commission", "type": "REGULATED_BY"}
        ]
      },
      "success": true,
      "execution_time_ms": 234,
      "turn_number": 1
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### 1. Traces Not Appearing in LangWatch

**Symptoms**: `send_trace_via_rest_api()` returns `True` but traces don't appear.

**Check**:
```bash
# Verify LangWatch is running
curl http://localhost:5560/health

# Check API key
echo $LANGWATCH_API_KEY
```

#### 2. Node/Relationship Data Missing

**Symptoms**: Some tool outputs have entities, others don't.

**Cause**: Payload size exceeded limits, triggering aggressive truncation.

**Solution**: The current implementation (as of Jan 2026) includes:
- Priority keys for `entities`, `relationships`, `nodes`
- Minimum 10KB budget per tool call
- Summary placeholders when data is truncated

#### 3. Embedding Data in Traces

**Symptoms**: Large payloads, slow trace sending.

**Solution**: Check that embedding keys are being filtered:
```python
# These should be automatically filtered:
'embedding', 'embeddings', 'vector', 'vectors', 'embed',
'dense_vector', 'sparse_vector', 'text_embedding', 'node_embedding'
```

### Testing the Integration

Run the test scripts:

```bash
# Basic test
source .venv/bin/activate && python test_langwatch_direct.py

# Test with many tool calls
python -c "
from src.chat.observability.langwatch_config import langwatch_config
langwatch_config.enabled = True
langwatch_config._initialized = True

# Test smart truncation preserves entities
test_data = {
    'entities': [{'uuid': '001', 'name': 'Test', 'type': 'Regulation'}],
    'description': 'Long text...' * 100
}
result = langwatch_config._smart_truncate_output(test_data, max_len=500)
print('Entities preserved:', 'entities' in result)
"
```

## API Reference

### LangWatchConfig Methods

| Method | Description |
|--------|-------------|
| `initialize(instrumentation_mode)` | Initialize LangWatch with specified mode ("manual", "auto", "langchain", "anthropic") |
| `set_thread_id(thread_id)` | Set thread ID for trace grouping |
| `set_session_query(session_id, query)` | Record the user's query for a session |
| `set_session_response(session_id, response)` | Record the agent's final response |
| `capture_agentic_turn(...)` | Record metadata for an agentic loop turn |
| `capture_tool_call_with_response(...)` | Record a tool call with full input/output |
| `finalize_session(session_id)` | Finalize session and return aggregated data |
| `send_trace_via_rest_api(session_data)` | Send trace to LangWatch REST API |

### Decorators

```python
@langwatch_config.trace(name="trace_name", metadata={"key": "value"})
async def my_function():
    pass
```

## Performance Considerations

- **Payload size**: Keep under 1MB to avoid truncation
- **Embedding filtering**: Always filter before sending
- **Async operations**: Trace sending is synchronous; consider background tasks for high-throughput scenarios
- **Session cleanup**: Always call `finalize_session()` to prevent memory leaks

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2026 | Initial REST API integration |
| 1.1 | Jan 2026 | Fixed invalid JSON truncation issue |
| 1.2 | Jan 2026 | Added priority keys for entities/relationships |
| 1.3 | Jan 2026 | Minimum per-call budget, verbose field handling |
