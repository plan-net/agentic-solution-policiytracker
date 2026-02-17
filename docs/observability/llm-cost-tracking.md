# LLM Cost Tracking System

## Overview

The LLM Cost Tracking system provides comprehensive monitoring of token usage and costs for all LLM API calls routed through the APISIX gateway. It captures requests to OpenAI, Anthropic, and other LLM providers, calculates costs based on model pricing, and stores the data in TimescaleDB for analysis.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────┐     ┌─────────────────┐
│                 │     │              APISIX Gateway           │     │                 │
│   Application   │────▶│  ┌────────────────────────────────┐  │────▶│   LLM Provider  │
│   (Agents)      │     │  │   llm-cost-tracker plugin      │  │     │   (OpenAI/      │
│                 │     │  │   - Captures headers           │  │     │    Anthropic)   │
└─────────────────┘     │  │   - Parses responses           │  │     └─────────────────┘
                        │  │   - Calculates costs           │  │
                        │  └──────────────┬─────────────────┘  │
                        └─────────────────┼────────────────────┘
                                          │ HTTP POST
                                          ▼
                        ┌─────────────────────────────────────┐
                        │       Cost Analytics Service        │
                        │       (FastAPI on port 8090)        │
                        │  ┌─────────────────────────────┐    │
                        │  │  /api/ingest/costs          │    │
                        │  │  /api/costs/summary         │    │
                        │  │  /api/costs/by-agent        │    │
                        │  │  /api/costs/by-model        │    │
                        │  └──────────────┬──────────────┘    │
                        └─────────────────┼───────────────────┘
                                          │
                                          ▼
                        ┌─────────────────────────────────────┐
                        │          TimescaleDB                │
                        │    ┌─────────────────────────┐      │
                        │    │    llm_requests table   │      │
                        │    │    (hypertable)         │      │
                        │    ├─────────────────────────┤      │
                        │    │  llm_costs_hourly       │      │
                        │    │  llm_costs_daily        │      │
                        │    │  (continuous aggregates)│      │
                        │    └─────────────────────────┘      │
                        └─────────────────────────────────────┘
```

## Components

### 1. APISIX Plugin (`llm-cost-tracker`)

**Location:** `apisix/plugins/llm-cost-tracker.lua`

The main plugin that runs on every LLM request through APISIX.

#### Plugin Phases

| Phase | Purpose |
|-------|---------|
| `access` | Capture agent headers, start timing, extract model from request |
| `body_filter` | Accumulate response body (non-streaming only) |
| `log` | Parse usage, calculate cost, async write to database |

#### Captured Data

- **Request metadata**: timestamp, endpoint, request size
- **Agent information**: agent_type, agent_name, flow_name, session_id, trace_id, project_id
- **LLM details**: provider (openai/anthropic), model name
- **Usage metrics**: prompt_tokens, completion_tokens, total_tokens
- **Cost**: calculated USD cost based on model pricing
- **Performance**: latency_ms, status_code

#### Configuration

The plugin is configured via `plugin_attr` in `apisix/config-2.15.yaml`:

```yaml
plugin_attr:
  llm-cost-tracker:
    db_host: "timescaledb"
    db_port: 5432
    db_name: "llm_costs"
    db_user: "timescale"
    db_password: "timescale_secure_password"
    batch_size: 10
    flush_interval: 5.0
    log_debug: true
```

### 2. Supporting Modules

#### Response Parser (`response_parser.lua`)

Parses token usage from LLM provider responses:

- **OpenAI format**: `{"usage": {"prompt_tokens": N, "completion_tokens": N}}`
- **Anthropic format**: `{"usage": {"input_tokens": N, "output_tokens": N}}`

#### Model Pricing (`model_pricing.lua`)

Contains pricing for 30+ models (per 1M tokens):

| Model | Input Price | Output Price |
|-------|-------------|--------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| claude-3-haiku | $0.25 | $1.25 |
| claude-3-opus | $15.00 | $75.00 |
| text-embedding-3-small | $0.02 | $0.00 |

#### Database Writer (`db_writer.lua`)

Handles async batched writes with fallback chain:
1. **HTTP** → Cost Analytics service (primary)
2. **pgmoon** → Direct PostgreSQL (if available)
3. **Socket/Log** → Fallback logging

### 3. Cost Analytics Service

**Location:** `apisix/analytics/`

FastAPI service providing REST APIs for cost data.

#### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | Health check with DB status |
| `POST /api/ingest/costs` | Receive cost records from APISIX |
| `GET /api/costs/summary` | Total costs, requests, tokens for period |
| `GET /api/costs/by-agent` | Breakdown by agent_type, agent_name |
| `GET /api/costs/by-model` | Breakdown by provider/model |
| `GET /api/costs/trends` | Hourly/daily cost trends |
| `GET /api/costs/sessions/{id}` | Per-session cost details |
| `POST /api/budgets/check` | Check spend against thresholds |

#### Query Parameters

Most endpoints support:
- `start_date` - ISO format datetime
- `end_date` - ISO format datetime
- `days` - Number of days to look back (default: 7)

### 4. TimescaleDB Schema

#### Main Table: `llm_requests`

```sql
CREATE TABLE llm_requests (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    endpoint VARCHAR(255),
    agent_type VARCHAR(100),
    agent_name VARCHAR(100),
    flow_name VARCHAR(100),
    chat_agent_name VARCHAR(100),
    session_id VARCHAR(255),
    trace_id VARCHAR(255),
    user_id VARCHAR(255),
    project_id VARCHAR(100) DEFAULT 'political_monitoring_v2',
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(12, 8) DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    status_code INTEGER,
    error_message TEXT,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    request_headers JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Continuous Aggregates

Pre-computed summaries for fast queries:

- `llm_costs_hourly` - Hourly rollups
- `llm_costs_daily` - Daily rollups

## Usage

### Starting the Services

```bash
# Start APISIX gateway with cost tracking
just apisix-up

# Or start all services
just services-up
```

### Viewing Cost Data

#### Via API

```bash
# Get cost summary for last 7 days
curl http://localhost:8090/api/costs/summary

# Get costs by agent
curl http://localhost:8090/api/costs/by-agent?days=30

# Get costs by model
curl http://localhost:8090/api/costs/by-model

# Get hourly trends
curl "http://localhost:8090/api/costs/trends?granularity=hourly&days=1"
```

#### Via TimescaleDB

```bash
# Connect to database
docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs

# Query recent requests
SELECT timestamp, provider, model, agent_name, total_tokens, cost_usd
FROM llm_requests
ORDER BY timestamp DESC
LIMIT 10;

# Daily cost summary
SELECT * FROM llm_costs_daily ORDER BY bucket DESC LIMIT 7;
```

### Adding Agent Headers

Applications should include these headers when making LLM requests:

```python
headers = {
    "X-Agent-Type": "kodosumi_flow",      # Type of agent
    "X-Agent-Name": "policy_analyzer",     # Specific agent name
    "X-Flow-Name": "daily_analysis",       # Workflow/flow name
    "X-Session-ID": "session-123",         # Session identifier
    "X-Trace-ID": "trace-abc",             # Trace ID for debugging
    "X-Project-ID": "political_monitoring_v2"  # Project identifier
}
```

## Configuration Files

| File | Purpose |
|------|---------|
| `apisix/plugins/llm-cost-tracker.lua` | Main plugin |
| `apisix/plugins/llm-cost-tracker/response_parser.lua` | Response parsing |
| `apisix/plugins/llm-cost-tracker/model_pricing.lua` | Model prices |
| `apisix/plugins/llm-cost-tracker/db_writer.lua` | Database writes |
| `apisix/config/llm_pricing.yaml` | YAML pricing config |
| `apisix/config-2.15.yaml` | APISIX config with plugin |
| `apisix/analytics/` | FastAPI analytics service |

## Updating Model Prices

Edit `apisix/plugins/llm-cost-tracker/model_pricing.lua`:

```lua
local DEFAULT_PRICES = {
    ["new-model-name"] = { input = 1.00, output = 3.00 },
    -- prices per 1 million tokens
}
```

Then restart APISIX:

```bash
docker compose restart apisix
```

## Monitoring & Debugging

### Check Plugin Status

```bash
# View APISIX logs for cost tracking
docker compose logs apisix | grep -i "llm-cost"

# Check if plugin is loaded
docker compose logs apisix | grep "new plugins"
```

### Check Analytics Service

```bash
# Health check
curl http://localhost:8090/health

# View logs
docker compose logs cost-analytics
```

### Database Connectivity

```bash
# Check TimescaleDB
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c "SELECT count(*) FROM llm_requests;"
```

## Troubleshooting

### Plugin Not Loading

1. Check plugin is in `plugins` list in `config-2.15.yaml`
2. Verify volume mount in `docker-compose.yml`
3. Check APISIX logs for Lua errors

### Records Not Being Saved

1. Check cost-analytics service is running: `curl http://localhost:8090/health`
2. Verify APISIX can reach cost-analytics: check Docker network
3. Look for HTTP errors in APISIX logs

### Missing Token Data

- Streaming responses are not yet supported
- Error responses (4xx, 5xx) may not include usage data
- Check if the LLM provider includes usage in response

## Limitations

1. **Streaming responses**: Currently ignored (token usage not captured)
2. **Cache hits**: Cached responses from some providers may not include usage
3. **Rate limits**: 429 errors are tracked but have 0 tokens

## Future Enhancements

- [ ] Streaming response support (SSE token counting)
- [ ] Budget alerts and notifications
- [ ] Grafana dashboard integration
- [ ] Cost anomaly detection
- [ ] Per-user/team cost allocation
