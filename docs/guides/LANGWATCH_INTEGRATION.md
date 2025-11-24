# LangWatch Integration Guide

## Overview

LangWatch is integrated as a self-hosted LLMOps observability platform for the Political Monitoring Agent v0.2.0. It provides comprehensive monitoring, tracing, and analytics for the LangGraph-based multi-agent chat system.

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                   Political Monitoring Agent                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │   Chat API   │───│ Orchestrator │───│    Agents    │   │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   │
│         │                  │                   │            │
│         └──────────────────┴───────────────────┘            │
│                            │                                │
│                     LangWatch SDK                           │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                ┌────────────▼────────────┐
                │  LangWatch Platform     │
                │  (Docker Services)      │
                ├─────────────────────────┤
                │ • PostgreSQL            │
                │ • ClickHouse            │
                │ • Elasticsearch         │
                │ • LangWatch Server      │
                └─────────────────────────┘
                             │
                    http://localhost:5560
```

### Observability Points

1. **Multi-Agent Orchestrator** (`src/chat/agent/orchestrator.py`)
   - Traces: `multi_agent_political_analysis`
   - Captures: Full workflow execution, agent transitions, tool executions

2. **Chat Server** (`src/chat/server/app.py`)
   - Initialization of LangWatch SDK
   - Request/response lifecycle monitoring

3. **Individual Agents**
   - Query Understanding Agent
   - Tool Planning Agent
   - Tool Execution Agent
   - Response Synthesis Agent

## Installation & Setup

### 1. Deploy LangWatch Services

Start the LangWatch Docker services:

```bash
just langwatch-up
```

This starts:
- PostgreSQL (data storage)
- ClickHouse (analytics database)
- Elasticsearch (search and indexing)
- LangWatch Server (web UI and API)

### 2. Initial Configuration

Access the LangWatch UI:

```bash
just langwatch-ui
# Opens http://localhost:5560
```

Or visit manually: http://localhost:5560

**Setup Steps:**
1. Create an account (any email/password)
2. Create a new project: "Political Monitoring Agent"
3. Navigate to **Settings → API Keys**
4. Click **Generate new API key**
5. Copy the API key

### 3. Configure Environment

Update your `.env` file:

```bash
# Enable LangWatch
ENABLE_LANGWATCH=true

# Add your API key from step 2
LANGWATCH_API_KEY=lw_xxxxxxxxxxxxxxxxxxxxxx

# Endpoint (default is correct for Docker setup)
LANGWATCH_ENDPOINT=http://langwatch-server:5560

# Generate a random secret (or use default for development)
LANGWATCH_NEXTAUTH_SECRET=your-secure-random-string-here
```

### 4. Install Dependencies

```bash
uv sync
```

This installs:
- `langwatch>=0.5.0` - LangWatch Python SDK
- `opentelemetry-api>=1.20.0` - OpenTelemetry API
- `opentelemetry-sdk>=1.20.0` - OpenTelemetry SDK
- `openinference-instrumentation-langchain>=0.1.0` - LangChain instrumentation

### 5. Restart Services

```bash
just restart
```

## Usage

### Automatic Tracing

Once configured, LangWatch automatically traces:

1. **Every chat query** through the multi-agent system
2. **Agent transitions** (understanding → planning → execution → synthesis)
3. **Tool executions** (knowledge graph queries)
4. **LLM calls** (token usage, latency, costs)
5. **Errors and exceptions** in the workflow

### View Traces

1. Open LangWatch UI: http://localhost:5560
2. Navigate to **Traces** section
3. View real-time traces as queries are processed
4. Click on individual traces to see:
   - Agent execution times
   - Tool call details
   - LLM token usage
   - Error messages
   - State transitions

### Example Trace Data

```json
{
  "trace_id": "multi_agent_political_analysis_xyz123",
  "duration_ms": 2847,
  "agents": [
    {
      "name": "query_understanding",
      "duration_ms": 421,
      "llm_calls": 1,
      "tokens": 150
    },
    {
      "name": "tool_planning",
      "duration_ms": 312,
      "llm_calls": 1,
      "tokens": 200
    },
    {
      "name": "tool_execution",
      "duration_ms": 1520,
      "tools_executed": 3,
      "success_rate": 1.0
    },
    {
      "name": "response_synthesis",
      "duration_ms": 594,
      "llm_calls": 1,
      "tokens": 350
    }
  ],
  "total_tokens": 700,
  "estimated_cost": 0.0042
}
```

## Testing

### Run Integration Tests

```bash
just test-langwatch
```

This runs comprehensive tests in `tests/integration/test_langwatch_integration.py`:

- Configuration initialization
- Environment variable handling
- Trace decorator functionality
- Synchronous and asynchronous function tracing
- Error handling
- Nested trace calls

### Manual Testing

1. Start all services:
   ```bash
   just start
   ```

2. Open Chat Interface:
   ```bash
   open http://localhost:3000
   ```

3. Submit a test query:
   ```
   "What is the EU AI Act and how does it affect companies?"
   ```

4. Check LangWatch UI for the trace:
   ```bash
   open http://localhost:5560
   ```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_LANGWATCH` | Yes | `false` | Enable/disable LangWatch observability |
| `LANGWATCH_API_KEY` | Yes* | - | API key from LangWatch UI |
| `LANGWATCH_ENDPOINT` | No | `http://langwatch-server:5560` | LangWatch server endpoint |
| `LANGWATCH_NEXTAUTH_SECRET` | No | Auto-generated | Secret for NextAuth sessions |

*Required when `ENABLE_LANGWATCH=true`

### Disable Observability

To disable LangWatch (no performance impact):

```bash
# In .env
ENABLE_LANGWATCH=false
```

Then restart:

```bash
just restart
```

The system will run normally without tracing overhead.

## Architecture Details

### SDK Integration

The integration uses a singleton configuration pattern:

**`src/chat/observability/langwatch_config.py`:**
- `LangWatchConfig` class manages SDK initialization
- `langwatch_config` singleton instance used throughout the application
- Graceful fallback if LangWatch is disabled or unavailable

### Trace Decorator

The `@langwatch_config.trace()` decorator:
- No-op decorator when LangWatch is disabled (zero overhead)
- Automatic trace context propagation
- Supports both sync and async functions
- Captures exceptions and error traces

**Example Usage:**

```python
from src.chat.observability.langwatch_config import langwatch_config

@langwatch_config.trace(name="my_agent_process")
async def process_query(query: str) -> dict:
    # Your agent logic here
    return result
```

### LangChain Instrumentation

Automatic instrumentation via `OpenInference`:
- Captures all LangChain/LangGraph operations
- Tracks LLM calls (OpenAI, Anthropic)
- Monitors tool executions
- Records agent state transitions

## Monitoring & Analytics

### Key Metrics

LangWatch provides:

1. **Performance Metrics**
   - Average query latency
   - Agent execution times
   - Tool call performance
   - LLM response times

2. **Cost Metrics**
   - Token usage per query
   - Estimated costs (OpenAI/Anthropic)
   - Cost breakdown by agent

3. **Quality Metrics**
   - Success rates
   - Error rates by agent
   - Tool execution success rates

4. **Usage Metrics**
   - Queries per hour/day
   - Peak usage times
   - User patterns

### Dashboards

Access dashboards in LangWatch UI:
- **Overview**: Real-time system health
- **Traces**: Detailed execution traces
- **Analytics**: Historical trends and patterns
- **Costs**: Token usage and cost analysis

## Troubleshooting

### LangWatch Services Not Starting

**Check service status:**
```bash
just langwatch-status
```

**View logs:**
```bash
just langwatch-logs
```

**Common issues:**
- Port 5560 already in use
- Insufficient Docker resources
- Database initialization errors

**Solution:**
```bash
# Stop and restart
just langwatch-down
sleep 5
just langwatch-up
```

### No Traces Appearing

**Checklist:**
1. Verify `ENABLE_LANGWATCH=true` in `.env`
2. Check API key is set correctly
3. Ensure services are running: `just langwatch-status`
4. Check application logs: `just ray-logs`

**Test configuration:**
```bash
# Run integration tests
just test-langwatch

# Test a simple query
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "political-monitoring-agent", "messages": [{"role": "user", "content": "test"}]}'
```

### Import Errors

**Error:**
```
ImportError: No module named 'langwatch'
```

**Solution:**
```bash
uv sync
just restart
```

### Performance Issues

If you notice performance degradation:

1. **Disable LangWatch temporarily:**
   ```bash
   # In .env
   ENABLE_LANGWATCH=false
   ```

2. **Restart services:**
   ```bash
   just restart
   ```

3. **Check LangWatch resource usage:**
   ```bash
   docker stats policiytracker-langwatch
   ```

## Best Practices

### 1. Development vs Production

**Development:**
- Enable LangWatch for detailed debugging
- Keep all trace details
- Use verbose logging

**Production:**
- Enable LangWatch for monitoring
- Configure trace sampling if high volume
- Set up alerts for error rates

### 2. Trace Naming

Use descriptive trace names:

```python
# Good
@langwatch_config.trace(name="query_understanding_agent")

# Better
@langwatch_config.trace(
    name="query_understanding_agent",
    metadata={
        "agent_version": "2.0",
        "model": "gpt-4o-mini"
    }
)
```

### 3. Sensitive Data

LangWatch traces may contain:
- User queries
- LLM responses
- Tool parameters

For sensitive data:
1. Review LangWatch data retention policies
2. Configure trace filtering if needed
3. Ensure compliance with data protection regulations

### 4. Resource Management

Monitor resource usage:

```bash
# Check Docker resources
docker stats

# Check LangWatch specific
docker stats policiytracker-langwatch-postgres \
             policiytracker-langwatch-clickhouse \
             policiytracker-langwatch-elasticsearch \
             policiytracker-langwatch
```

## Advanced Configuration

### Custom Metadata

Add custom metadata to traces:

```python
@langwatch_config.trace(
    name="custom_agent",
    metadata={
        "user_id": user_id,
        "session_id": session_id,
        "query_complexity": "high",
        "custom_field": "value"
    }
)
async def process_complex_query(query: str):
    # Processing logic
    pass
```

### Conditional Tracing

Enable tracing only for specific conditions:

```python
async def process_query(query: str, trace_enabled: bool = True):
    if trace_enabled and langwatch_config.enabled:
        decorator = langwatch_config.trace(name="conditional_trace")
    else:
        decorator = lambda f: f  # No-op

    @decorator
    async def _process():
        # Processing logic
        return result

    return await _process()
```

## Support & Resources

### LangWatch Documentation
- Official Docs: https://docs.langwatch.ai
- LangGraph Integration: https://docs.langwatch.ai/integration/python/integrations/langgraph
- GitHub: https://github.com/langwatch/langwatch

### Project Support
- Issues: Create GitHub issue in project repository
- Justfile commands: `just --list | grep langwatch`
- Quick setup: `just langwatch-setup`

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| LangWatch | >= 0.5.0 | Python SDK |
| OpenTelemetry | >= 1.20.0 | Tracing infrastructure |
| LangGraph | >= 0.2.59 | Multi-agent framework |
| Docker | >= 20.10 | Container runtime |

## Changelog

### v0.2.0 - Initial Integration
- Self-hosted LangWatch deployment
- Multi-agent orchestrator tracing
- Chat server integration
- Justfile commands
- Integration tests
- Comprehensive documentation
