# APISIX Routing Architecture

**Last Updated**: February 2026
**Version**: 2.0.0

## Quick Start

| Task | Command |
|------|---------|
| **New Setup** | `bash scripts/setup_apisix_routes.sh` |
| **Sync to Production** | `bash scripts/sync_apisix_prod.sh` |
| **List Routes** | `docker exec policiytracker-etcd etcdctl get /apisix/routes --prefix --keys-only` |
| **Check Health** | `curl http://localhost:9092/v1/healthcheck` |

## Overview

This document describes the evolution of APISIX routing from a single catch-all route to a comprehensive, granular routing architecture with dedicated cost and request tracking.

## Architecture Evolution

### Before: Single Catch-All Route (Problematic)

```
┌─────────────────────────────────────────────────────────────┐
│                    APISIX Gateway                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Route: openai-route                                        │
│   URI: /*                                                    │
│   Priority: 0                                                │
│   ↓                                                          │
│   Upstream: openai-upstream (api.openai.com)                │
│                                                              │
│   PROBLEM: This catch-all route intercepted ALL requests!   │
│   - Anthropic calls → routed to OpenAI ❌                   │
│   - External APIs → routed to OpenAI ❌                     │
│   - No tracking for external APIs ❌                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### After: Granular Route Architecture (Current)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         APISIX Gateway (Port 9080)                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                    LLM Provider Routes                           │ │
│  │  (llm-cost-tracker plugin for token/cost tracking)              │ │
│  ├─────────────────────────────────────────────────────────────────┤ │
│  │                                                                   │ │
│  │  ┌─────────────────┐     ┌─────────────────┐                    │ │
│  │  │   Anthropic     │     │     OpenAI      │                    │ │
│  │  │  (Priority 10+) │     │   (Priority 5)  │                    │ │
│  │  ├─────────────────┤     ├─────────────────┤                    │ │
│  │  │ anthropic-v1v1  │     │ openai-chat     │                    │ │
│  │  │ /v1/v1/messages*│     │ /v1/chat/comp.. │                    │ │
│  │  │ (P:15)          │     │                 │                    │ │
│  │  │                 │     │ openai-embed..  │                    │ │
│  │  │ anthropic-all   │     │ /v1/embeddings  │                    │ │
│  │  │ /v1/messages*   │     │                 │                    │ │
│  │  │ (P:10)          │     │ openai-models   │                    │ │
│  │  │                 │     │ /v1/models*     │                    │ │
│  │  │                 │     │                 │                    │ │
│  │  │                 │     │ openai-resp..   │                    │ │
│  │  │                 │     │ /v1/responses*  │                    │ │
│  │  └────────┬────────┘     └────────┬────────┘                    │ │
│  │           │                       │                              │ │
│  │           ▼                       ▼                              │ │
│  │   anthropic-upstream       openai-upstream                       │ │
│  │   api.anthropic.com        api.openai.com                        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                  External API Routes                             │ │
│  │  (api-request-tracker plugin for request metrics)               │ │
│  ├─────────────────────────────────────────────────────────────────┤ │
│  │                                                                   │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────────┐ │ │
│  │  │  EXA AI    │  │    DPA     │  │       Bundestag DIP        │ │ │
│  │  │ (Web/News) │  │   (News)   │  │   (German Parliament)      │ │ │
│  │  ├────────────┤  ├────────────┤  ├────────────────────────────┤ │ │
│  │  │ exa-search │  │ dpa-       │  │ bundestag-vorgang          │ │ │
│  │  │ /exa/search│  │ articles   │  │ /bundestag/vorgang*        │ │ │
│  │  │            │  │ /dpa/      │  │                            │ │ │
│  │  │ exa-       │  │ articles/* │  │ bundestag-drucksache       │ │ │
│  │  │ contents   │  │            │  │ /bundestag/drucksache*     │ │ │
│  │  │ /exa/      │  │            │  │                            │ │ │
│  │  │ contents   │  │            │  │ bundestag-aktivitaet       │ │ │
│  │  │            │  │            │  │ /bundestag/aktivitaet*     │ │ │
│  │  │            │  │            │  │                            │ │ │
│  │  │            │  │            │  │ bundestag-person           │ │ │
│  │  │            │  │            │  │ /bundestag/person*         │ │ │
│  │  │            │  │            │  │                            │ │ │
│  │  │            │  │            │  │ bundestag-plenarprotokoll  │ │ │
│  │  │            │  │            │  │ /bundestag/plenarprotokoll*│ │ │
│  │  └─────┬──────┘  └─────┬──────┘  └────────────┬───────────────┘ │ │
│  │        │               │                      │                  │ │
│  │        ▼               ▼                      ▼                  │ │
│  │  exa-upstream    dpa-upstream         bundestag-upstream         │ │
│  │  api.exa.ai      article-retriever    search.dip.bundestag.de   │ │
│  │                  .iq.dpa-ai-hub.de                               │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Cost Analytics Service (Port 8090)                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  POST /api/ingest/costs          ← LLM cost records                  │
│  POST /api/ingest/external-api   ← External API metrics              │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    TimescaleDB (Port 5433)                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  llm_requests table          ← Token counts, costs, cache metrics    │
│  external_api_requests table ← Latency, status, request counts       │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Current Route Configuration

### LLM Provider Routes

| Route ID | URI Pattern | Methods | Priority | Upstream | Plugin |
|----------|-------------|---------|----------|----------|--------|
| `anthropic-v1v1` | `/v1/v1/messages*` | GET, POST | 15 | anthropic-upstream | llm-cost-tracker |
| `anthropic-all` | `/v1/messages*` | GET, POST | 10 | anthropic-upstream | llm-cost-tracker |
| `openai-chat` | `/v1/chat/completions` | POST | 5 | openai-upstream | llm-cost-tracker |
| `openai-embeddings` | `/v1/embeddings` | POST | 5 | openai-upstream | llm-cost-tracker |
| `openai-models` | `/v1/models*` | GET | 5 | openai-upstream | llm-cost-tracker |
| `openai-responses` | `/v1/responses*` | GET, POST | 5 | openai-upstream | llm-cost-tracker |

**Priority Explanation**:
- Anthropic routes have higher priority (10, 15) to ensure `/v1/messages` is routed to Anthropic, not OpenAI
- The `/v1/v1/messages*` route (priority 15) handles double-prefixed paths from some clients

### External API Routes

| Route ID | URI Pattern | Methods | Priority | Upstream | Plugin |
|----------|-------------|---------|----------|----------|--------|
| `exa-search` | `/exa/search` | POST | 5 | exa-upstream | api-request-tracker |
| `exa-contents` | `/exa/contents` | POST | 5 | exa-upstream | api-request-tracker |
| `dpa-articles` | `/dpa/articles/*` | POST | 5 | dpa-upstream | api-request-tracker |
| `bundestag-vorgang` | `/bundestag/vorgang*` | GET | 5 | bundestag-upstream | api-request-tracker |
| `bundestag-drucksache` | `/bundestag/drucksache*` | GET | 5 | bundestag-upstream | api-request-tracker |
| `bundestag-aktivitaet` | `/bundestag/aktivitaet*` | GET | 5 | bundestag-upstream | api-request-tracker |
| `bundestag-person` | `/bundestag/person*` | GET | 5 | bundestag-upstream | api-request-tracker |
| `bundestag-plenarprotokoll` | `/bundestag/plenarprotokoll*` | GET | 5 | bundestag-upstream | api-request-tracker |

---

## Upstreams Configuration

| Upstream ID | Target Host | Port | Scheme | Timeout (read) | Description |
|-------------|-------------|------|--------|----------------|-------------|
| `anthropic-upstream` | api.anthropic.com | 443 | HTTPS | 300s | Claude API |
| `openai-upstream` | api.openai.com | 443 | HTTPS | 60s | GPT API |
| `exa-upstream` | api.exa.ai | 443 | HTTPS | 60s | Web/News Search |
| `dpa-upstream` | article-retriever.iq.dpa-ai-hub.de | 443 | HTTPS | 180s | German Press Agency |
| `bundestag-upstream` | search.dip.bundestag.de | 443 | HTTPS | 60s | German Parliament API |

---

## Custom Plugins

### 1. llm-cost-tracker (LLM Routes)

**Purpose**: Track token usage and calculate costs for LLM API calls.

**Location**: `apisix/plugins/llm-cost-tracker.lua` + `apisix/plugins/llm-cost-tracker/`

**Features**:
- Token counting (prompt, completion, total)
- Cache token tracking (Anthropic prompt caching)
  - `cache_creation_input_tokens` - New cache entries (1.25x price)
  - `cache_read_input_tokens` - Cache hits (0.10x price = 90% discount!)
- Cost calculation with model-specific pricing
- Async batch writes to TimescaleDB
- Agent-level tracking via headers

**Tracked Fields**:
```lua
{
  provider,           -- "anthropic" | "openai"
  model,              -- "claude-sonnet-4-20250514", "gpt-4o", etc.
  prompt_tokens,      -- Non-cached input tokens
  completion_tokens,  -- Output tokens
  total_tokens,       -- All tokens combined
  cache_creation_tokens,  -- Cache write tokens
  cache_read_tokens,      -- Cache read tokens
  cost_usd,           -- Calculated cost
  agent_name,         -- From X-Agent-Name header
  session_id,         -- From X-Session-ID header
  latency_ms,
  status_code,
}
```

### 2. api-request-tracker (External API Routes)

**Purpose**: Track request metrics for external (non-LLM) API calls.

**Location**: `apisix/plugins/api-request-tracker.lua`

**Features**:
- Request/response size tracking
- Latency measurement
- Status code tracking
- Agent correlation via headers
- Async batch writes to TimescaleDB

**Tracked Fields**:
```lua
{
  api_name,           -- "exa-search", "dpa-articles", etc.
  endpoint,           -- Request URI
  method,             -- HTTP method
  latency_ms,
  status_code,
  request_size_bytes,
  response_size_bytes,
  agent_name,         -- From X-Agent-Name header
  session_id,         -- From X-Session-ID header
}
```

---

## Data Storage

### llm_requests Table (LLM Costs)

```sql
CREATE TABLE llm_requests (
    timestamp TIMESTAMPTZ NOT NULL,
    provider VARCHAR(50),
    model VARCHAR(100),
    endpoint VARCHAR(200),

    -- Agent tracking
    agent_type VARCHAR(50),
    agent_name VARCHAR(100),
    flow_name VARCHAR(100),
    session_id VARCHAR(100),

    -- Token usage
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd DECIMAL(12, 8),

    -- Performance
    latency_ms INTEGER,
    status_code INTEGER,

    -- Cache metadata (JSONB)
    request_headers JSONB  -- Contains cache_creation_tokens, cache_read_tokens
);
```

### external_api_requests Table (External APIs)

```sql
CREATE TABLE external_api_requests (
    timestamp TIMESTAMPTZ NOT NULL,
    api_name VARCHAR(50),
    endpoint VARCHAR(200),
    method VARCHAR(10),

    -- Agent tracking
    agent_type VARCHAR(50),
    agent_name VARCHAR(100),
    flow_name VARCHAR(100),
    session_id VARCHAR(100),

    -- Performance
    latency_ms INTEGER,
    status_code INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,

    -- Metadata
    request_headers JSONB,
    api_metadata JSONB
);
```

---

## Route Priority Rules

APISIX uses numeric priority where **higher numbers = higher priority**.

```
Priority 15: anthropic-v1v1 (/v1/v1/messages*)  ← Most specific, wins first
Priority 10: anthropic-all (/v1/messages*)     ← Catches standard Anthropic paths
Priority 5:  All other routes                   ← Default priority
Priority 0:  NEVER use /* catch-all            ← This breaks everything!
```

**Why Priority Matters**:
1. `/v1/messages` must route to Anthropic, not OpenAI
2. `/v1/chat/completions` must route to OpenAI
3. Without priorities, the first matching route wins (unpredictable)

---

## URL Rewriting

### Bundestag Routes (regex_uri)

The Bundestag DIP API expects paths like `/api/v1/vorgang`, but we expose `/bundestag/vorgang`:

```json
{
  "proxy-rewrite": {
    "regex_uri": ["^/bundestag(/vorgang.*)$", "/api/v1$1"]
  }
}
```

| Incoming Request | Rewritten To |
|------------------|--------------|
| `/bundestag/vorgang?apikey=xxx` | `/api/v1/vorgang?apikey=xxx` |
| `/bundestag/drucksache/123` | `/api/v1/drucksache/123` |

### EXA Routes (uri)

Simple path rewriting:

```json
{
  "proxy-rewrite": {
    "uri": "/search"
  }
}
```

| Incoming Request | Rewritten To |
|------------------|--------------|
| `/exa/search` | `/search` |
| `/exa/contents` | `/contents` |

---

## Rate Limiting

All routes include rate limiting to protect upstream APIs:

| API | Rate (req/sec) | Burst |
|-----|----------------|-------|
| EXA | 10 | 5 |
| DPA | 5 | 2 |
| Bundestag | 5 | 3 |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `apisix/config-2.15.yaml` | Main APISIX config (plugins, etcd connection) |
| `apisix/apisix.yaml` | Static route definitions (backup) |
| `apisix/plugins/llm-cost-tracker.lua` | LLM cost tracking plugin |
| `apisix/plugins/llm-cost-tracker/model_pricing.lua` | Model pricing table |
| `apisix/plugins/llm-cost-tracker/response_parser.lua` | Token extraction |
| `apisix/plugins/llm-cost-tracker/db_writer.lua` | Async DB writes |
| `apisix/plugins/api-request-tracker.lua` | External API tracking plugin |
| `scripts/setup_apisix_routes.sh` | Route setup script |
| `scripts/sync_apisix_prod.sh` | Production sync script |

---

## Health Checks

### APISIX Container
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9092/v1/healthcheck"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Note**: Uses Control API port 9092, not gateway port 9080.

### APISIX Dashboard
```yaml
healthcheck:
  test: ["CMD-SHELL", "pgrep manager-api || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## Verification Commands

### List All Routes
```bash
docker exec policiytracker-etcd etcdctl get /apisix/routes --prefix --keys-only
```

### View Route Details
```bash
docker exec policiytracker-etcd etcdctl get /apisix/routes/exa-search
```

### Test Route (EXA)
```bash
curl -X POST http://localhost:9080/exa/search \
  -H "x-api-key: $EXA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "German politics", "numResults": 5}'
```

### Check Cost Data
```bash
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT provider, model, cost_usd FROM llm_requests ORDER BY timestamp DESC LIMIT 5;"
```

### Check External API Data
```bash
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT api_name, endpoint, latency_ms FROM external_api_requests ORDER BY timestamp DESC LIMIT 5;"
```

---

## Initial Setup (New Installation)

### Prerequisites

1. **Docker services running**:
   ```bash
   docker compose up -d etcd timescaledb apisix cost-analytics
   ```

2. **Wait for services to be healthy**:
   ```bash
   docker compose ps  # All should show "healthy"
   ```

### Step 1: Run Route Setup Script

The `scripts/setup_apisix_routes.sh` script creates all routes and upstreams via etcd:

```bash
# From the project root directory
cd agentic-solution-policiytracker

# Run the setup script (requires sudo for docker exec)
bash scripts/setup_apisix_routes.sh
```

**What the script creates**:

| Type | Name | Description |
|------|------|-------------|
| **Upstreams** | | |
| | anthropic-upstream | api.anthropic.com:443 |
| | openai-upstream | api.openai.com:443 |
| | exa-upstream | api.exa.ai:443 |
| | dpa-upstream | article-retriever.iq.dpa-ai-hub.de:443 |
| | bundestag-upstream | search.dip.bundestag.de:443 |
| **LLM Routes** | | |
| | anthropic-all | `/v1/messages*` → Anthropic |
| | openai-chat | `/v1/chat/completions` → OpenAI |
| | openai-embeddings | `/v1/embeddings` → OpenAI |
| | openai-models | `/v1/models*` → OpenAI |
| | openai-responses | `/v1/responses*` → OpenAI |
| **External API Routes** | | |
| | exa-search | `/exa/search` → EXA AI |
| | exa-contents | `/exa/contents` → EXA AI |
| | dpa-articles | `/dpa/articles/relevant` → DPA News |
| | bundestag-vorgang | `/bundestag/vorgang*` → Bundestag DIP |
| | bundestag-drucksache | `/bundestag/drucksache*` → Bundestag DIP |

### Step 2: Verify Routes Created

```bash
# List all routes
docker exec policiytracker-etcd etcdctl get /apisix/routes --prefix --keys-only

# Expected output:
# /apisix/routes/anthropic-all
# /apisix/routes/bundestag-drucksache
# /apisix/routes/bundestag-vorgang
# /apisix/routes/dpa-articles
# /apisix/routes/exa-contents
# /apisix/routes/exa-search
# /apisix/routes/openai-chat
# /apisix/routes/openai-embeddings
# /apisix/routes/openai-models
# /apisix/routes/openai-responses
```

### Step 3: Test a Route

```bash
# Test OpenAI route (needs API key)
curl -X POST http://localhost:9080/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Agent-Name: test-agent" \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'

# Test EXA route (needs API key)
curl -X POST http://localhost:9080/exa/search \
  -H "x-api-key: $EXA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "numResults": 1}'
```

### Step 4: Verify Cost Tracking

```bash
# Check if requests are being tracked
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT timestamp, provider, model, cost_usd FROM llm_requests ORDER BY timestamp DESC LIMIT 5;"

# Check external API tracking
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT timestamp, api_name, latency_ms FROM external_api_requests ORDER BY timestamp DESC LIMIT 5;"
```

---

## Production Sync

### Sync Routes to Production Server

Use `scripts/sync_apisix_prod.sh` to sync routes from local etcd to production:

```bash
# This script reads routes from local etcd and creates them on production
bash scripts/sync_apisix_prod.sh
```

**What it does**:
1. Exports all routes and upstreams from local etcd
2. SSHs to production server (`polmo` alias)
3. Creates/updates routes in production etcd
4. Verifies the sync completed successfully

### Manual Route Creation (Production)

If you need to create a single route on production:

```bash
ssh polmo 'sudo docker exec policiytracker-etcd etcdctl put /apisix/routes/my-route '"'"'{
  "id": "my-route",
  "uri": "/my/endpoint",
  "methods": ["GET", "POST"],
  "priority": 5,
  "status": 1,
  "plugins": {
    "proxy-rewrite": {
      "host": "api.example.com",
      "scheme": "https"
    }
  },
  "upstream_id": "my-upstream"
}'"'"''
```

---

## Migration Notes

### From Catch-All to Granular Routes

1. **Deleted**: `openai-route` with `/*` URI (blocked all other routes)
2. **Created**: Individual routes per endpoint with appropriate priorities
3. **Added**: External API routes with `api-request-tracker` plugin
4. **Added**: Cache token tracking for Anthropic prompt caching

### Docker Compose Changes

Added plugin volume mounts:
```yaml
volumes:
  - ./apisix/plugins/llm-cost-tracker.lua:/usr/local/apisix/apisix/plugins/llm-cost-tracker.lua:ro
  - ./apisix/plugins/llm-cost-tracker:/usr/local/apisix/apisix/plugins/llm-cost-tracker:ro
  - ./apisix/plugins/api-request-tracker.lua:/usr/local/apisix/apisix/plugins/api-request-tracker.lua:ro
```

Updated health check:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9092/v1/healthcheck"]
```

---

## Troubleshooting

### Route Not Working

1. Check if route exists:
   ```bash
   docker exec policiytracker-etcd etcdctl get /apisix/routes/<route-id>
   ```

2. Check priority conflicts:
   ```bash
   docker exec policiytracker-etcd etcdctl get /apisix/routes --prefix | grep -A5 "priority"
   ```

3. Check APISIX logs:
   ```bash
   docker logs policiytracker-apisix --tail 100
   ```

### Plugin Not Loaded

1. Verify plugin is mounted:
   ```bash
   docker exec policiytracker-apisix ls -la /usr/local/apisix/apisix/plugins/ | grep -E "(llm-cost|api-request)"
   ```

2. Check plugin is in config:
   ```bash
   docker exec policiytracker-apisix cat /usr/local/apisix/conf/config.yaml | grep -A20 "plugins:"
   ```

### No Data in TimescaleDB

1. Check cost-analytics service:
   ```bash
   curl http://localhost:8090/health
   ```

2. Test connectivity from APISIX:
   ```bash
   docker exec policiytracker-apisix wget -q -O - http://cost-analytics:8000/health
   ```

3. Check ingest endpoint:
   ```bash
   curl -X POST http://localhost:8090/api/ingest/costs \
     -H "Content-Type: application/json" \
     -d '{"records": [{"provider": "test", "model": "test", "cost_usd": 0.001}]}'
   ```
