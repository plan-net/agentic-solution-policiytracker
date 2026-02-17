# LLM Cost Analytics Solution

**Policy Tracker v0.2.0**

This document describes the comprehensive LLM cost-tracking solution implemented using Apache APISIX as an API gateway, TimescaleDB for time-series storage, and Grafana for visualization.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Components](#components)
3. [APISIX Configuration](#apisix-configuration)
4. [LLM Cost Tracker Plugin](#llm-cost-tracker-plugin)
5. [Database Schema](#database-schema)
6. [Cost Analytics API](#cost-analytics-api)
7. [Grafana Dashboard](#grafana-dashboard)
8. [Pricing Models](#pricing-models)
9. [Deployment](#deployment)
10. [Usage Guide](#usage-guide)
11. [Configuration Reference](#configuration-reference)
12. [Troubleshooting](#troubleshooting)
13. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM API Requests                                   │
│                    (OpenAI / Anthropic / Azure)                              │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      APISIX Gateway (Port 9080)                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    llm-cost-tracker Plugin                             │  │
│  │  ┌─────────────┐  ┌─────────────────┐  ┌───────────────────────────┐  │  │
│  │  │   Access    │  │  Header/Body    │  │      Log Phase            │  │  │
│  │  │   Phase     │──│    Filter       │──│  • Parse tokens           │  │  │
│  │  │ • Headers   │  │  • Accumulate   │  │  • Calculate cost         │  │  │
│  │  │ • Timing    │  │    response     │  │  • Enqueue async write    │  │  │
│  │  └─────────────┘  └─────────────────┘  └───────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            ▼                    ▼                    ▼
┌───────────────────┐ ┌──────────────────┐ ┌────────────────────┐
│   TimescaleDB     │ │  Cost Analytics  │ │      Grafana       │
│   (Port 5433)     │ │   API (8090)     │ │    (Port 3002)     │
│                   │ │                  │ │                    │
│ • llm_requests    │ │ • REST Endpoints │ │ • LLM Costs        │
│ • llm_costs_hourly│ │ • Budget Checks  │ │   Dashboard        │
│ • llm_costs_daily │ │ • Trend Analysis │ │ • Real-time        │
│ • Retention 90d   │ │ • Batch Ingest   │ │   Updates          │
└───────────────────┘ └──────────────────┘ └────────────────────┘
```

### Data Flow

1. **Client Request** → Application sends LLM API request through APISIX gateway
2. **Access Phase** → Plugin captures request metadata, agent headers, timing
3. **Proxy** → Request forwarded to upstream LLM provider (OpenAI/Anthropic)
4. **Response Capture** → Plugin accumulates response body chunks
5. **Log Phase** → Parse token usage, calculate cost, enqueue for database write
6. **Async Write** → Batched records written to TimescaleDB via Cost Analytics API
7. **Visualization** → Grafana queries materialized views for dashboard

---

## Components

### Service Overview

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| APISIX | policiytracker-apisix | 9080, 9443, 9180 | API Gateway with cost tracking |
| APISIX Dashboard | policiytracker-apisix-dashboard | 9000 | Gateway management UI |
| etcd | policiytracker-etcd | 2379 | APISIX configuration store |
| TimescaleDB | policiytracker-timescaledb | 5433 | Time-series cost storage |
| Cost Analytics API | policiytracker-cost-analytics | 8090 | REST API for cost queries |
| Grafana | policiytracker-grafana | 3002 | Cost visualization dashboard |

### File Structure

```
apisix/
├── apisix.yaml                    # Routes and upstreams
├── config-2.15.yaml               # APISIX configuration
├── plugins/
│   ├── llm-cost-tracker.lua       # Main plugin
│   └── llm-cost-tracker/
│       ├── response_parser.lua    # Token extraction
│       ├── model_pricing.lua      # Cost calculation
│       └── db_writer.lua          # Async database writes
├── init-scripts/
│   └── 01_init_cost_tracking.sql  # Database schema
├── analytics/
│   ├── app.py                     # FastAPI application
│   ├── config.py                  # Configuration
│   ├── database.py                # Connection pooling
│   ├── models/schemas.py          # Pydantic models
│   ├── services/cost_service.py   # Query logic
│   └── routers/
│       ├── costs.py               # Cost endpoints
│       ├── budgets.py             # Budget checking
│       └── ingest.py              # Batch ingest
└── dashboard_conf/
    └── conf.yaml                  # Dashboard config

grafana/
├── dashboards/
│   └── llm-costs.json             # Dashboard definition
└── provisioning/
    ├── dashboards/dashboards.yaml # Dashboard provisioning
    └── datasources/timescaledb.yaml # Datasource config
```

---

## APISIX Configuration

### Routes ([apisix/apisix.yaml](../apisix/apisix.yaml))

The gateway defines routes for LLM API proxying:

#### OpenAI Routes
- `POST /v1/chat/completions` → Chat completions with cost tracking
- `POST /v1/embeddings` → Embeddings with cost tracking
- `GET /v1/models*` → Model listing (no cost tracking)

#### Anthropic Routes
- `POST /v1/messages` → Claude messages with cost tracking

### Plugin Chain

Each cost-tracked route uses:

```yaml
plugins:
  serverless-pre-function:    # Inject agent headers
  proxy-rewrite:              # Forward to upstream + disable gzip
    scheme: "https"
    host: "api.openai.com"
    headers:
      Accept-Encoding: ""     # IMPORTANT: Disable gzip for cost tracking
  limit-req:                  # Rate limiting
  api-breaker:                # Circuit breaker
  llm-cost-tracker:           # Cost tracking
    enabled: true
    log_debug: true
```

> **Important:** The `Accept-Encoding: ""` header is required to disable gzip compression.
> Without this, LLM providers return compressed responses that the cost tracker cannot parse.
> See [Troubleshooting: Zero Tokens/Cost](#zero-tokenscost-in-dashboard) for details.

### Agent Header Injection

The `serverless-pre-function` plugin detects requests from specific clients (e.g., Graphiti via `AsyncOpenAI` User-Agent) and injects agent headers:

```lua
core.request.set_header(ctx, "X-Agent-Type", "kodosumi_flow")
core.request.set_header(ctx, "X-Agent-Name", "graphiti_document_processor")
core.request.set_header(ctx, "X-Flow-Name", "data_ingestion")
core.request.set_header(ctx, "X-Project-ID", "political_monitoring_v2")
```

### Upstream Configuration

```yaml
upstreams:
  - id: openai-upstream
    nodes:
      "api.openai.com:443": 1
    timeout:
      read: 300  # 5 minutes for long completions
    retries: 2
    keepalive_pool:
      size: 320
```

---

## LLM Cost Tracker Plugin

### Main Plugin ([apisix/plugins/llm-cost-tracker.lua](../apisix/plugins/llm-cost-tracker.lua))

The plugin operates in four phases:

#### 1. Access Phase
```lua
function _M.access(conf, ctx)
    ctx.llm_start_time = ngx_now()
    ctx.llm_agent_data = {
        agent_type = core.request.header(ctx, "X-Agent-Type"),
        agent_name = core.request.header(ctx, "X-Agent-Name"),
        flow_name = core.request.header(ctx, "X-Flow-Name"),
        -- ... more headers
    }
    -- Detect provider from URI
    -- Extract model from request body
end
```

#### 2. Header Filter Phase
- Detect streaming responses
- Capture HTTP status code
- Initialize response buffer

#### 3. Body Filter Phase
- Accumulate response chunks
- Skip streaming responses

#### 4. Log Phase
```lua
function _M.log(conf, ctx)
    local latency_ms = (ngx_now() - ctx.llm_start_time) * 1000
    local usage = response_parser.extract_usage(ctx.llm_full_response, ctx.llm_provider)
    local cost_usd = model_pricing.calculate_cost(model, usage)
    db_writer.enqueue(record, conf)
end
```

### Response Parser ([response_parser.lua](../apisix/plugins/llm-cost-tracker/response_parser.lua))

Handles different response formats:

**OpenAI Chat Completion:**
```json
{
  "model": "gpt-4o-mini",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

**Anthropic Messages:**
```json
{
  "model": "claude-3-5-sonnet",
  "usage": {
    "input_tokens": 100,
    "output_tokens": 50
  }
}
```

### Model Pricing ([model_pricing.lua](../apisix/plugins/llm-cost-tracker/model_pricing.lua))

Pricing per 1 million tokens (November 2024):

| Model | Input | Output |
|-------|-------|--------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| claude-3-5-sonnet | $3.00 | $15.00 |
| claude-3-5-haiku | $1.00 | $5.00 |
| text-embedding-3-small | $0.02 | $0.00 |

**Cost Calculation:**
```lua
local input_cost = (prompt_tokens / 1000000) * prices.input
local output_cost = (completion_tokens / 1000000) * prices.output
return input_cost + output_cost
```

### Database Writer ([db_writer.lua](../apisix/plugins/llm-cost-tracker/db_writer.lua))

Async batched writes with fallback chain:
1. HTTP POST to Cost Analytics API
2. Direct pgmoon connection (if available)
3. Socket/log fallback

Features:
- Batch size: 10 records
- Flush interval: 5 seconds
- Max queue: 1000 records
- Non-blocking `ngx.timer.at()`

---

## Database Schema

### Main Table: `llm_requests`

```sql
CREATE TABLE llm_requests (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Provider & Model
    provider VARCHAR(50),       -- 'openai', 'anthropic'
    model VARCHAR(100),         -- 'gpt-4o-mini', 'claude-3-5-sonnet'
    endpoint VARCHAR(200),

    -- Agent Attribution
    agent_type VARCHAR(50),     -- 'kodosumi_flow', 'chat_agent'
    agent_name VARCHAR(100),
    flow_name VARCHAR(100),
    chat_agent_name VARCHAR(100),
    session_id VARCHAR(100),
    trace_id VARCHAR(100),

    -- User & Project
    user_id VARCHAR(100),
    project_id VARCHAR(100),

    -- Tokens & Cost
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(12, 8),

    -- Performance
    latency_ms INTEGER,
    status_code INTEGER,

    PRIMARY KEY (id, timestamp)
);

-- TimescaleDB hypertable
SELECT create_hypertable('llm_requests', 'timestamp',
    chunk_time_interval => INTERVAL '1 day');
```

### Continuous Aggregates

**Hourly Aggregation:**
```sql
CREATE MATERIALIZED VIEW llm_costs_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS bucket,
    provider, model, agent_type, agent_name, flow_name,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(latency_ms) as avg_latency
FROM llm_requests
GROUP BY bucket, provider, model, agent_type, agent_name, flow_name;
```

**Daily Aggregation:** Same structure with 1-day buckets.

### Refresh Policies
- Hourly: Every 5 minutes
- Daily: Every 1 hour

### Retention Policy
```sql
SELECT add_retention_policy('llm_requests', INTERVAL '90 days');
```

---

## Cost Analytics API

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/costs/summary` | Overall cost summary |
| GET | `/api/costs/by-model` | Breakdown by model |
| GET | `/api/costs/by-agent` | Breakdown by agent |
| GET | `/api/costs/by-provider` | Breakdown by provider |
| GET | `/api/costs/trends` | Hourly/daily trends |
| GET | `/api/costs/session/{id}` | Session details |
| GET | `/api/budgets/check` | Budget threshold check |
| POST | `/api/ingest/costs` | Batch ingest records |

### Example Queries

**Cost Summary (last 7 days):**
```bash
curl http://localhost:8090/api/costs/summary?days=7
```

Response:
```json
{
  "period_start": "2024-11-21T00:00:00",
  "period_end": "2024-11-28T00:00:00",
  "summary": {
    "total_cost_usd": 45.67,
    "total_requests": 12450,
    "total_tokens": 5234567,
    "avg_latency_ms": 234.5,
    "error_count": 12
  }
}
```

**Cost by Agent:**
```bash
curl http://localhost:8090/api/costs/by-agent?days=7
```

**Budget Check:**
```bash
curl "http://localhost:8090/api/budgets/check?threshold_type=daily&threshold_usd=100"
```

---

## Grafana Dashboard

### Access
- URL: http://localhost:3002
- Username: `admin`
- Password: `admin123`

### Dashboard Panels

#### Row 1: Summary Stats
1. **Total Cost (Today)** - Stat panel with thresholds (green <$10, yellow <$50, red >$50)
2. **Total Tokens (Today)** - Token count
3. **Total Requests (Today)** - Request count
4. **Avg Latency (Today)** - Average latency with thresholds

#### Row 2: Time Series
5. **Cost Over Time (Hourly)** - Line chart from `llm_costs_hourly`
6. **Requests Per Hour** - Request volume trend

#### Row 3: Breakdowns (Pie Charts)
7. **Cost by Model** - Top 10 models
8. **Cost by Agent** - Top 10 agents
9. **Cost by Provider** - OpenAI vs Anthropic

#### Row 4: Tables
10. **Model Usage Summary** - Model, requests, tokens, cost
11. **Agent Usage Summary** - Agent, flow, requests, latency, cost

#### Row 5: Extended Views
12. **Daily Cost (Last 30 Days)** - Bar chart
13. **Top Sessions by Cost** - Session tracking table

### Auto-Refresh
Dashboard refreshes every 30 seconds.

---

## Pricing Models

### Supported Providers

#### OpenAI (November 2024)
| Model | Input ($/1M) | Output ($/1M) |
|-------|-------------|---------------|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-4 | $30.00 | $60.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |
| o1-preview | $15.00 | $60.00 |
| o1-mini | $3.00 | $12.00 |
| text-embedding-3-small | $0.02 | $0.00 |
| text-embedding-3-large | $0.13 | $0.00 |

#### Anthropic (November 2024)
| Model | Input ($/1M) | Output ($/1M) |
|-------|-------------|---------------|
| claude-3-5-sonnet | $3.00 | $15.00 |
| claude-3-5-haiku | $1.00 | $5.00 |
| claude-3-opus | $15.00 | $75.00 |
| claude-3-haiku | $0.25 | $1.25 |

### Fallback Pricing
Unknown models: $1.00/1M input, $3.00/1M output

### Example Cost Calculation

**gpt-4o-mini with 10K prompt + 5K completion:**
```
Input:  (10,000 / 1,000,000) × $0.15 = $0.0015
Output: (5,000 / 1,000,000) × $0.60 = $0.0030
Total:  $0.0045
```

**claude-3-5-sonnet with 100K input + 50K output:**
```
Input:  (100,000 / 1,000,000) × $3.00 = $0.30
Output: (50,000 / 1,000,000) × $15.00 = $0.75
Total:  $1.05
```

---

## Deployment

### Prerequisites
- Docker & Docker Compose
- Environment variables set (OPENAI_API_KEY, etc.)

### Start Services
```bash
# Start all services including cost tracking
docker compose up -d etcd timescaledb apisix apisix-dashboard cost-analytics grafana

# Check health
docker compose ps
```

### Verify Installation

1. **Check APISIX Gateway:**
   ```bash
   curl http://localhost:9080/apisix/status
   ```

2. **Check TimescaleDB:**
   ```bash
   docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c "SELECT COUNT(*) FROM llm_requests;"
   ```

3. **Check Cost Analytics API:**
   ```bash
   curl http://localhost:8090/health
   ```

4. **Access Grafana:**
   Open http://localhost:3002 (admin/admin123)

### Configure Client

Point your LLM client to the APISIX gateway:

```python
import openai

# Route through APISIX gateway
client = openai.OpenAI(
    api_key="your-api-key",
    base_url="http://localhost:9080/v1"
)

# Add agent headers for attribution
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
    extra_headers={
        "X-Agent-Type": "chat_agent",
        "X-Agent-Name": "my_agent",
        "X-Session-ID": "session-123"
    }
)
```

---

## Usage Guide

### Agent Header Convention

Include these headers for cost attribution:

| Header | Description | Example |
|--------|-------------|---------|
| X-Agent-Type | Category of agent | `kodosumi_flow`, `chat_agent` |
| X-Agent-Name | Specific agent ID | `document_processor` |
| X-Flow-Name | Workflow name | `data_ingestion` |
| X-Chat-Agent-Name | Chat component | `query_understanding` |
| X-Session-ID | Conversation ID | `sess-abc123` |
| X-Trace-ID | Distributed trace | `trace-xyz` |
| X-User-ID | User identifier | `user-456` |
| X-Project-ID | Project scope | `political_monitoring_v2` |

### Monitoring Costs

1. **Real-time Dashboard:** Open Grafana at http://localhost:3002
2. **API Queries:** Use Cost Analytics API endpoints
3. **Direct SQL:** Query TimescaleDB views

### Budget Alerts

Check budget status programmatically:
```bash
curl "http://localhost:8090/api/budgets/check?threshold_type=daily&threshold_usd=50"
```

Response indicates if budget is exceeded:
```json
{
  "threshold_type": "daily",
  "threshold_usd": 50.0,
  "current_spend_usd": 45.67,
  "remaining_usd": 4.33,
  "percentage_used": 91.34,
  "is_exceeded": false
}
```

---

## Configuration Reference

### Plugin Configuration

```yaml
llm-cost-tracker:
  enabled: true
  log_debug: false          # Enable debug logging
  db_host: timescaledb
  db_port: 5432
  db_name: llm_costs
  db_user: timescale
  db_password: timescale_secure_password
  batch_size: 10            # Records per batch
  flush_interval: 5.0       # Seconds between flushes
  default_project_id: political_monitoring_v2
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | - | PostgreSQL connection string |
| LOG_LEVEL | INFO | Logging verbosity |
| GF_SECURITY_ADMIN_PASSWORD | admin123 | Grafana admin password |

### Updating Prices

Edit [model_pricing.lua](../apisix/plugins/llm-cost-tracker/model_pricing.lua) and restart APISIX:

```lua
local DEFAULT_PRICES = {
    ["gpt-4o"] = { input = 2.50, output = 10.00 },
    -- Add new models here
}
```

---

## Troubleshooting

### Zero Tokens/Cost in Dashboard

**Symptom:** Dashboard shows requests but `Total Tokens = 0` and `Total Cost = $0`.

**Root Cause:** LLM API responses are gzip-compressed, which the cost tracker cannot parse.

**Diagnosis:** Check APISIX logs for parsing errors:
```bash
docker logs policiytracker-apisix 2>&1 | grep -i "Failed to parse"
```

If you see errors like:
```
LLM Cost Tracker: Failed to parse OpenAI response: Expected value but found invalid token at character 1
```

This confirms the gzip compression issue.

**Solution:** Ensure all LLM routes have `Accept-Encoding: ""` in the `proxy-rewrite` plugin:

```yaml
proxy-rewrite:
  scheme: "https"
  host: "api.openai.com"
  headers:
    Accept-Encoding: ""  # Disables gzip compression
```

After updating `apisix.yaml`, restart APISIX:
```bash
docker compose restart apisix
```

**Why This Happens:**
- The OpenAI/Anthropic Python SDKs automatically send `Accept-Encoding: gzip, deflate`
- LLM providers honor this and return compressed responses
- The cost tracker plugin receives binary gzip data instead of JSON
- Setting `Accept-Encoding: ""` tells the upstream to return uncompressed JSON

### No Data in Grafana

1. **Check if records exist:**
   ```bash
   docker exec policiytracker-timescaledb psql -U timescale -d llm_costs \
     -c "SELECT COUNT(*) FROM llm_requests;"
   ```

2. **Check if materialized views are refreshed:**
   ```bash
   docker exec policiytracker-timescaledb psql -U timescale -d llm_costs \
     -c "SELECT * FROM llm_costs_daily WHERE bucket >= CURRENT_DATE;"
   ```

3. **Manually refresh views if needed:**
   ```bash
   docker exec policiytracker-timescaledb psql -U timescale -d llm_costs \
     -c "CALL refresh_continuous_aggregate('llm_costs_hourly', NULL, NULL);"
   docker exec policiytracker-timescaledb psql -U timescale -d llm_costs \
     -c "CALL refresh_continuous_aggregate('llm_costs_daily', NULL, NULL);"
   ```

4. **Check APISIX logs:**
   ```bash
   docker logs policiytracker-apisix 2>&1 | grep -i "cost_tracker\|LLM_COST" | tail -20
   ```

5. **Verify TimescaleDB connection:**
   ```bash
   docker logs policiytracker-cost-analytics
   ```

### High Latency
- Increase `read` timeout in upstream config (default: 300s)
- Check batch size and flush interval in plugin config
- Monitor database connection pool usage

### Missing Agent Attribution
- Ensure headers are set before request
- Check `serverless-pre-function` plugin for auto-injection
- Verify headers are being forwarded (not stripped by proxy)

### Streaming Responses Not Tracked

Currently, streaming responses (`stream: true`) are **not tracked** for cost.
The plugin skips streaming responses to avoid memory issues from buffering.

**Workaround:** Use non-streaming requests for operations where cost tracking is critical.

**Future Enhancement:** Streaming support is planned (see Future Enhancements).

---

## Future Enhancements

- [ ] Streaming response support (parse SSE chunks for token counts)
- [ ] Azure OpenAI integration
- [ ] Cost forecasting based on historical trends
- [ ] Anomaly detection alerts (spike in costs)
- [ ] Cost allocation reports (PDF export)
- [ ] Gzip decompression in plugin (alternative to stripping Accept-Encoding)
