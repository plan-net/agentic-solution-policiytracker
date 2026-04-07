# Cost Tracking Setup Guide

**Version**: 1.0.0
**Last Updated**: February 2026

This document provides comprehensive documentation for the LLM and External API cost tracking system in the Policy Tracker project.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [LLM Cost Tracking](#llm-cost-tracking)
   - [APISIX Plugin (for non-SDK calls)](#apisix-llm-cost-tracker-plugin)
   - [SDK Cost Tracker (for Claude Agent SDK)](#sdk-cost-tracker)
3. [External API Tracking](#external-api-tracking)
4. [Database Schema](#database-schema)
5. [Grafana Dashboards](#grafana-dashboards)
6. [Continuous Aggregates](#continuous-aggregates)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The cost tracking system has two parallel paths for capturing LLM costs:

```
                                ┌─────────────────────────────────────────────┐
                                │           LLM Cost Tracking                 │
                                └─────────────────────────────────────────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    │                               │                               │
                    ▼                               │                               ▼
┌───────────────────────────────────┐               │       ┌───────────────────────────────────┐
│   Path 1: APISIX Gateway          │               │       │   Path 2: SDK Cost Tracker        │
│   (Non-SDK LLM Calls)             │               │       │   (Claude Agent SDK Calls)        │
├───────────────────────────────────┤               │       ├───────────────────────────────────┤
│                                   │               │       │                                   │
│  • Graphiti (OpenAI)              │               │       │  • PolicyTrackerSDKAgent          │
│  • Direct Anthropic calls         │               │       │  • WeeklyReportAgent              │
│  • Any call via localhost:9080    │               │       │  • Any Claude SDK agent           │
│                                   │               │       │                                   │
│  Plugin: llm-cost-tracker.lua     │               │       │  Module: sdk_cost_tracker.py      │
│                                   │               │       │                                   │
└───────────────────┬───────────────┘               │       └───────────────────┬───────────────┘
                    │                               │                           │
                    │                               │                           │
                    └───────────────────────────────┼───────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │   Cost Analytics Service      │
                                    │   POST /api/ingest/costs      │
                                    │   (Port 8090)                 │
                                    └───────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │        TimescaleDB            │
                                    │     Table: llm_requests       │
                                    │                               │
                                    │  Continuous Aggregates:       │
                                    │  • llm_costs_hourly           │
                                    │  • llm_costs_daily            │
                                    └───────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │      Grafana Dashboards       │
                                    │   "LLM Cost Analytics"        │
                                    └───────────────────────────────┘
```

### Why Two Paths?

1. **APISIX Gateway Path**: Most LLM calls go through APISIX at `localhost:9080`. The `llm-cost-tracker` Lua plugin intercepts responses, extracts token usage, calculates costs, and writes to TimescaleDB.

2. **SDK Cost Tracker Path**: The Claude Agent SDK uses an internal CLI that bypasses APISIX. The `sdk_cost_tracker.py` module sends cost records directly to the analytics service after each agent session.

---

## LLM Cost Tracking

### APISIX LLM Cost Tracker Plugin

**Location**: `apisix/plugins/llm-cost-tracker.lua`

This Lua plugin intercepts LLM API responses flowing through APISIX, extracts token usage from the response body, and calculates costs based on model pricing.

#### How It Works

```
Request Flow:
┌──────────┐     ┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│  Client  │────▶│  APISIX  │────▶│  LLM Provider    │────▶│  Response    │
│          │     │          │     │  (OpenAI/Claude) │     │              │
└──────────┘     └────┬─────┘     └──────────────────┘     └──────┬───────┘
                      │                                           │
                      │         ┌─────────────────────┐           │
                      └────────▶│ llm-cost-tracker    │◀──────────┘
                                │ plugin              │
                                │                     │
                                │ 1. Capture headers  │
                                │ 2. Parse response   │
                                │ 3. Extract tokens   │
                                │ 4. Calculate cost   │
                                │ 5. Write to DB      │
                                └─────────────────────┘
```

#### Plugin Phases

| Phase | Action |
|-------|--------|
| **access** | Capture request metadata: agent headers, provider, model, timing start |
| **header_filter** | Detect streaming vs non-streaming response |
| **body_filter** | Accumulate response body chunks |
| **log** | Parse usage, calculate cost, write to TimescaleDB |

#### Required Headers for Attribution

Include these headers in your LLM requests for proper cost attribution:

```python
headers = {
    "X-Agent-Type": "kodosumi_flow",      # or "chat_agent", "etl_processor"
    "X-Agent-Name": "graphiti_processor",  # Specific agent identifier
    "X-Flow-Name": "data_ingestion",       # For Kodosumi flows
    "X-Session-ID": "session_12345",       # Track sessions
    "X-Project-ID": "political_monitoring_v2",
}
```

#### Default Header Injection

If no agent headers are provided, the plugin auto-injects defaults based on User-Agent:

```lua
-- For OpenAI SDK calls without headers:
agent_type = "kodosumi_flow"
agent_name = "graphiti_document_processor"  -- or "graphiti_embedder" for /embeddings
flow_name = "data_ingestion"
```

#### Plugin Configuration

```yaml
# In apisix.yaml routes:
plugins:
  llm-cost-tracker:
    enabled: true
    log_debug: true  # Set to false in production
    db_host: "timescaledb"
    db_port: 5432
    db_name: "llm_costs"
    db_user: "timescale"
    batch_size: 10
    flush_interval: 5.0
```

#### Model Pricing

**Location**: `apisix/plugins/llm-cost-tracker/model_pricing.lua`

Prices are per **1 million tokens**:

| Model | Input ($/1M) | Output ($/1M) |
|-------|--------------|---------------|
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| claude-opus-4-20250514 | $15.00 | $75.00 |
| claude-haiku-4-20250514 | $0.80 | $4.00 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| text-embedding-3-small | $0.02 | $0.00 |

**Cache Token Pricing** (Anthropic):
- Cache creation: 1.25x base input price
- Cache read: 0.10x base input price (90% discount!)

---

### SDK Cost Tracker

**Location**: `src/shared/sdk_cost_tracker.py`

The Claude Agent SDK bypasses APISIX (uses internal CLI), so costs must be tracked separately.

#### How It Works

```python
from src.shared.sdk_cost_tracker import sdk_cost_tracker, SDKCostRecord

# After agent session completes:
record = SDKCostRecord(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    agent_type="chat_agent",
    agent_name="PolicyTrackerSDKAgent",
    session_id="claude_abc123",
    prompt_tokens=1500,
    completion_tokens=500,
    total_tokens=2000,
    cost_usd=0.012,
    latency_ms=3500,
    cache_creation_tokens=0,
    cache_read_tokens=0,
    web_search_requests=0,
    web_fetch_requests=0,
)

await sdk_cost_tracker.record_cost(record)
```

#### Configuration

Environment variables (set in `config.yaml` or Ray Serve runtime_env):

```yaml
env_vars:
  SDK_COST_TRACKING_ENABLED: 'true'
  COST_ANALYTICS_URL: http://localhost:8090
```

#### Integration Points

1. **Chat Agent** (`src/claude_agent/agent_sdk.py`):
   - Records cost after each agent.run() call
   - Uses LangFuse for observability, SDK tracker for cost analytics

2. **Weekly Report Agent** (`src/flows/weekly_report_sdk/agent/report_agent_sdk.py`):
   - Records cost after report generation completes
   - Session ID passed from UI for consistent tracking

#### Extended Metadata

The SDK tracker stores cache tokens and web tool usage in the `request_headers` JSONB field:

```json
{
  "sdk_source": "claude_agent_sdk",
  "cache_creation_tokens": 1000,
  "cache_read_tokens": 5000,
  "non_cached_input_tokens": 500,
  "web_search_requests": 2,
  "web_fetch_requests": 5,
  "web_search_cost_usd": 0.02
}
```

---

## External API Tracking

**Status**: Fully integrated. All external API clients support APISIX gateway routing.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          External API Tracking                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼────────────────────────────────┐
        │                               │                                │
        ▼                               ▼                                ▼
┌────────────────────┐   ┌────────────────────┐   ┌────────────────────────┐
│  Exa Search        │   │  DPA Articles      │   │  Bundestag DIP         │
│  /exa/*            │   │  /dpa/*            │   │  /bundestag/*          │
├────────────────────┤   ├────────────────────┤   ├────────────────────────┤
│ Clients:           │   │ Clients:           │   │ Clients:               │
│ • ExaSearchClient  │   │ • DPANewsClient    │   │ • BundestagDIPClient   │
│   (MCP web_search) │   │   (MCP web_search) │   │   (MCP bundestag_dip)  │
│ • ExaDirectCollect │   │ • DPANewsCollector │   │ • BundestagAPIClient   │
│   (ETL DAGs)       │   │   (ETL DAGs)       │   │   (flow1b-bulk-auto)   │
└─────────┬──────────┘   └─────────┬──────────┘   └──────────┬─────────────┘
          │                        │                          │
          └────────────────────────┼──────────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────────┐
                         │  APISIX Gateway      │
                         │  (Port 9080)         │
                         │                      │
                         │  api-request-tracker │
                         │  Lua Plugin          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Cost Analytics      │
                         │  /api/ingest/        │
                         │  external-api        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  TimescaleDB         │
                         │  external_api_       │
                         │  requests            │
                         └─────────────────────┘
```

### APISIX Plugin

**Location**: `apisix/plugins/api-request-tracker.lua`

Tracks:
- Latency (ms)
- Status codes
- Request/response sizes
- Agent attribution
- No cost calculation (external APIs don't have token-based pricing)

### Client-Side APISIX Integration

Each external API client checks environment variables to decide whether to route through APISIX:

| Client | File | Env Var | APISIX Route |
|--------|------|---------|--------------|
| `ExaSearchClient` (MCP) | `src/mcp/web_search/exa_client.py` | `USE_APISIX_FOR_EXA` | `/exa/search`, `/exa/contents` |
| `ExaDirectCollector` (ETL) | `src/etl/collectors/exa_direct.py` | `USE_APISIX_FOR_EXA` | `/exa/search` |
| `DPANewsClient` (MCP) | `src/mcp/web_search/dpa_client.py` | `USE_APISIX_FOR_DPA` | `/dpa/articles/relevant` |
| `DPANewsCollector` (ETL) | `src/etl/collectors/dpa_news.py` | `USE_APISIX_FOR_DPA` | `/dpa/articles/relevant` |
| `BundestagDIPClient` (MCP) | `src/mcp/bundestag_dip/client.py` | `USE_APISIX_FOR_BUNDESTAG` | `/bundestag/{endpoint}` |
| `BundestagAPIClient` (Flow) | `src/flows/bundestag_common/api_client.py` | `USE_APISIX_FOR_BUNDESTAG` | `/bundestag/{endpoint}` |

All clients also use `APISIX_GATEWAY_URL` (default: `http://localhost:9080`).

**Note**: The `ExaNewsCollector` (`src/etl/collectors/exa_news.py`) uses the `exa_py` Python SDK which does not support custom base URLs, so it **cannot** route through APISIX. Use `exa_direct` collector instead (this is the default).

### How It Works (Client Pattern)

Each client follows the same pattern in `__init__`:

```python
# APISIX Gateway support
self.use_apisix = os.getenv("USE_APISIX_FOR_<API>", "false").lower() == "true"
self.apisix_url = os.getenv("APISIX_GATEWAY_URL", "http://localhost:9080")
```

And in the request method:

```python
if self.use_apisix:
    url = f"{self.apisix_url}/<api-prefix>/{endpoint}"
else:
    url = f"{self.API_BASE_URL}/{endpoint}"
```

### Environment Variables

Set these in `.env` to enable APISIX routing:

```bash
# Enable APISIX routing for external APIs
USE_APISIX_FOR_EXA=true
USE_APISIX_FOR_DPA=true
USE_APISIX_FOR_BUNDESTAG=true

# APISIX gateway URL (no /v1 suffix for external API routes)
APISIX_GATEWAY_URL=http://localhost:9080
```

### Docker Services Requiring These Env Vars

| Docker Service | APIs Routed | Env Vars Needed |
|----------------|-------------|-----------------|
| `bundestag-dip-mcp` | Bundestag | `USE_APISIX_FOR_BUNDESTAG`, `APISIX_GATEWAY_URL` |
| `web-search-mcp` | Exa, DPA | `USE_APISIX_FOR_EXA`, `USE_APISIX_FOR_DPA`, `APISIX_GATEWAY_URL` |
| `airflow-webserver` | Exa, DPA | `USE_APISIX_FOR_EXA`, `USE_APISIX_FOR_DPA`, `APISIX_GATEWAY_URL` |
| `airflow-scheduler` | Exa, DPA | `USE_APISIX_FOR_EXA`, `USE_APISIX_FOR_DPA`, `APISIX_GATEWAY_URL` |

Ray Serve applications (`claude-agent`, `weekly-report-sdk`, `flow1b-bulk-auto`) get these env vars from `config.yaml` runtime_env.

### APISIX Route Setup

External API routes are created via etcd (not in `apisix.yaml`). Run the setup script:

```bash
bash apisix/configure-external-api-routes.sh
```

This creates routes with the `api-request-tracker` plugin for:

```yaml
# Exa
POST /exa/search       → api.exa.ai/search
POST /exa/contents     → api.exa.ai/contents

# DPA
POST /dpa/articles/*   → article-retriever.iq.dpa-ai-hub.de/articles/*

# Bundestag
GET /bundestag/vorgang*         → search.dip.bundestag.de/api/v1/vorgang*
GET /bundestag/drucksache*      → search.dip.bundestag.de/api/v1/drucksache*
GET /bundestag/person*          → search.dip.bundestag.de/api/v1/person*
GET /bundestag/plenarprotokoll* → search.dip.bundestag.de/api/v1/plenarprotokoll*
GET /bundestag/aktivitaet*      → search.dip.bundestag.de/api/v1/aktivitaet*
```

---

## Database Schema

### TimescaleDB Connection

```bash
# Connect to database
docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs
```

### LLM Requests Table

**Table**: `llm_requests`

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Auto-increment ID |
| timestamp | TIMESTAMPTZ | Request timestamp (partition key) |
| provider | VARCHAR(50) | 'openai' or 'anthropic' |
| model | VARCHAR(100) | Model name |
| endpoint | VARCHAR(200) | API endpoint |
| agent_type | VARCHAR(50) | 'kodosumi_flow', 'chat_agent', etc. |
| agent_name | VARCHAR(100) | Specific agent identifier |
| flow_name | VARCHAR(100) | Kodosumi flow name |
| chat_agent_name | VARCHAR(100) | Chat agent name |
| session_id | VARCHAR(100) | Session identifier |
| trace_id | VARCHAR(100) | Distributed tracing ID |
| user_id | VARCHAR(100) | User identifier |
| project_id | VARCHAR(100) | Project identifier |
| prompt_tokens | INTEGER | Input tokens |
| completion_tokens | INTEGER | Output tokens |
| total_tokens | INTEGER | Total tokens |
| cost_usd | DECIMAL(12,8) | Cost in USD |
| latency_ms | INTEGER | Request latency |
| status_code | INTEGER | HTTP status code |
| error_message | TEXT | Error details |
| request_size_bytes | INTEGER | Request payload size |
| response_size_bytes | INTEGER | Response payload size |
| request_headers | JSONB | Extended metadata (cache tokens, etc.) |

### External API Requests Table

**Table**: `external_api_requests`

| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Auto-increment ID |
| timestamp | TIMESTAMPTZ | Request timestamp |
| api_name | VARCHAR(50) | 'exa-search', 'dpa-articles', etc. |
| endpoint | VARCHAR(200) | Full endpoint path |
| method | VARCHAR(10) | HTTP method |
| agent_type | VARCHAR(50) | Agent type |
| agent_name | VARCHAR(100) | Agent name |
| flow_name | VARCHAR(100) | Flow name |
| session_id | VARCHAR(100) | Session ID |
| latency_ms | INTEGER | Request latency |
| status_code | INTEGER | HTTP status code |
| request_size_bytes | INTEGER | Request size |
| response_size_bytes | INTEGER | Response size |
| api_metadata | JSONB | API-specific metadata |

---

## Grafana Dashboards

### LLM Cost Analytics Dashboard

**Location**: `grafana/dashboards/llm-costs.json`

Panels:
1. **Total Cost (Today)** - Sum of all LLM costs for current day
2. **Total Tokens (Today)** - Sum of all tokens consumed
3. **Request Count (Today)** - Number of LLM API calls
4. **Cost by Model (Pie Chart)** - Cost distribution by model
5. **Cost by Agent (Pie Chart)** - Cost distribution by agent
6. **Cost Over Time (Time Series)** - Hourly cost trend
7. **Session Details (Table)** - Detailed session breakdown

### External API Usage Dashboard

**Location**: `grafana/dashboards/external-api-usage.json`

Panels:
1. **Total Requests (Today)**
2. **Success Rate (Today)**
3. **Avg Latency (Today)**
4. **Errors (Today)**
5. **Requests by API (Time Series)**
6. **Latency by API (Time Series)**
7. **API Summary (Table)**

---

## Continuous Aggregates

TimescaleDB continuous aggregates provide pre-computed summaries for faster dashboard queries.

### Available Aggregates

| Aggregate | Bucket | Refresh Interval |
|-----------|--------|------------------|
| llm_costs_hourly | 1 hour | Every 5 minutes |
| llm_costs_daily | 1 day | Every 1 hour |
| external_api_hourly | 1 hour | Every 5 minutes |
| external_api_daily | 1 day | Every 10 minutes |

### Manual Refresh

If dashboards show stale data, manually refresh aggregates:

```bash
# SSH to production server
ssh polmo

# Refresh all aggregates for today
sudo docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "CALL refresh_continuous_aggregate('llm_costs_hourly', '2026-02-17 00:00:00', '2026-02-18 00:00:00');"

sudo docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "CALL refresh_continuous_aggregate('llm_costs_daily', '2026-02-17 00:00:00', '2026-02-18 00:00:00');"

sudo docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "CALL refresh_continuous_aggregate('external_api_hourly', '2026-02-17 00:00:00', '2026-02-18 00:00:00');"

sudo docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "CALL refresh_continuous_aggregate('external_api_daily', '2026-02-17 00:00:00', '2026-02-18 00:00:00');"
```

### Check Aggregate Status

```sql
-- List all continuous aggregates
SELECT view_name FROM timescaledb_information.continuous_aggregates;

-- Check refresh jobs
SELECT * FROM timescaledb_information.jobs
WHERE proc_name = 'policy_refresh_continuous_aggregate';
```

---

## Troubleshooting

### 1. SDK Costs Not Appearing in Dashboard

**Symptoms**: Chat agent or weekly report sessions missing from LLM Cost Analytics dashboard

**Check**:
```bash
# Verify environment variables are set
ssh polmo "grep -A5 'claude-agent' /root/agentic-solution-policiytracker/config.yaml"

# Should show:
# SDK_COST_TRACKING_ENABLED: 'true'
# COST_ANALYTICS_URL: http://localhost:8090
```

**Fix**: Add env vars to `config.yaml.template` (not just `config.yaml`):
```yaml
env_vars:
  SDK_COST_TRACKING_ENABLED: 'true'
  COST_ANALYTICS_URL: http://localhost:8090
```

### 2. Session ID Mismatch

**Symptoms**: UI shows different session ID than LangFuse/Dashboard

**Cause**: UI generates `report_id` but agent generates its own `session_id`

**Fix**: Pass `session_id` parameter to agent methods:
```python
# In reports.py
result = await agent.generate_report(
    week_start=week_start,
    week_end=week_end,
    session_id=report_id,  # Use UI's report_id
)
```

### 3. Dashboard Shows 0 for Today's Values

**Symptoms**: All "Today" stats show 0 even after making requests

**Cause**: Continuous aggregates not refreshed

**Fix**: Manually refresh aggregates (see [Manual Refresh](#manual-refresh))

### 4. External API Dashboard Empty

**Symptoms**: External API Usage dashboard shows all zeros

**Possible Causes**:

1. **APISIX routing not enabled**: Check that `USE_APISIX_FOR_EXA`, `USE_APISIX_FOR_DPA`, `USE_APISIX_FOR_BUNDESTAG` are set to `true` in the relevant services.

2. **APISIX routes not configured**: Run `bash apisix/configure-external-api-routes.sh` to create external API routes in etcd.

3. **Continuous aggregates not refreshing**: See [Dashboard Shows 0 for Today's Values](#3-dashboard-shows-0-for-todays-values).

4. **Wrong APISIX_GATEWAY_URL**: External API routes use `http://localhost:9080` (no `/v1` suffix). Check that `APISIX_GATEWAY_URL` is set correctly.

**Verification**:
```bash
# Check if requests are flowing through APISIX
docker logs policiytracker-apisix --tail 50 | grep -E "exa|dpa|bundestag"

# Check external_api_requests table
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT api_name, COUNT(*) FROM external_api_requests WHERE timestamp >= CURRENT_DATE GROUP BY api_name;"
```

### 5. Cost Analytics Service Not Running

**Check**:
```bash
ssh polmo "sudo docker ps | grep cost-analytics"
curl http://localhost:8090/health
```

**Fix**:
```bash
ssh polmo "cd /root && sudo docker-compose up -d cost-analytics"
```

### 6. TimescaleDB Connection Issues

**Check**:
```bash
ssh polmo "sudo docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c 'SELECT 1;'"
```

**Common Issues**:
- Wrong database name (use `llm_costs`, not `llm_analytics`)
- Wrong username (use `timescale`, not `postgres`)

---

## Quick Reference

### Endpoints

| Service | Port | Endpoint |
|---------|------|----------|
| APISIX Gateway | 9080 | LLM proxy routes |
| Cost Analytics | 8090 | `/api/ingest/costs`, `/api/ingest/external-api` |
| TimescaleDB | 5432 | PostgreSQL connection |
| Grafana | 3000 | Dashboards |

### Key Files

| File | Purpose |
|------|---------|
| `apisix/plugins/llm-cost-tracker.lua` | APISIX LLM cost tracking plugin |
| `apisix/plugins/api-request-tracker.lua` | APISIX external API tracking plugin |
| `apisix/plugins/llm-cost-tracker/model_pricing.lua` | Model pricing table |
| `src/shared/sdk_cost_tracker.py` | SDK cost tracking module |
| `apisix/analytics/routers/ingest.py` | Cost ingestion API |
| `apisix/init-scripts/01_init_cost_tracking.sql` | LLM schema |
| `apisix/init-scripts/02_init_external_api_tracking.sql` | External API schema |
| `grafana/dashboards/llm-costs.json` | LLM dashboard |
| `grafana/dashboards/external-api-usage.json` | External API dashboard |

### Common Queries

```sql
-- Today's costs by agent
SELECT agent_name, SUM(cost_usd) as cost, COUNT(*) as requests
FROM llm_requests
WHERE timestamp >= CURRENT_DATE
GROUP BY agent_name
ORDER BY cost DESC;

-- Recent sessions
SELECT session_id, agent_name, SUM(cost_usd), SUM(total_tokens)
FROM llm_requests
WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY session_id, agent_name
ORDER BY SUM(cost_usd) DESC
LIMIT 20;

-- Check specific session
SELECT * FROM llm_requests
WHERE session_id = 'report_abc123'
ORDER BY timestamp;
```
