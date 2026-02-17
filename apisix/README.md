# Apache APISIX API Gateway - LLMOps Implementation

**Version**: 2.0.0
**Last Updated**: February 2026

## Overview

This directory contains the Apache APISIX API gateway configuration for centralizing LLM provider access and external API routing with comprehensive agent-level cost and request tracking.

## Documentation

| Document | Description |
|----------|-------------|
| **[ROUTING_ARCHITECTURE.md](./ROUTING_ARCHITECTURE.md)** | Complete routing architecture, route tables, plugin details, migration notes |
| **[JUSTFILE_COMMANDS.md](./JUSTFILE_COMMANDS.md)** | Available justfile commands for APISIX management |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              APISIX Gateway                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LLM Routes (llm-cost-tracker)      External API Routes (api-request)  │
│  ├─ Anthropic (/v1/messages*)       ├─ EXA (/exa/*)                    │
│  └─ OpenAI (/v1/chat/*, etc.)       ├─ DPA (/dpa/*)                    │
│                                      └─ Bundestag (/bundestag/*)        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Cost Analytics Service                         │
│                                                                         │
│  POST /api/ingest/costs        POST /api/ingest/external-api           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              TimescaleDB                                │
│                                                                         │
│  llm_requests (tokens, costs)    external_api_requests (latency, etc.) │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. APISIX Gateway (`docker-compose.yml`)
- **Port 9080**: HTTP Gateway (main entry point)
- **Port 9443**: HTTPS Gateway
- **Port 9180**: Admin API

### 2. APISIX Dashboard (`docker-compose.yml`)
- **Port 9000**: Management UI
- **Default Login**: admin/admin (change in production!)

### 3. etcd (`docker-compose.yml`)
- Configuration storage for APISIX
- Ports: 2379, 2380

### 4. TimescaleDB (`docker-compose.yml`)
- **Port 5433**: PostgreSQL + TimescaleDB
- Time-series database for cost tracking
- Automatic aggregation with continuous aggregates

### 5. Cost Analytics API (`docker-compose.yml`)
- **Port 8090**: FastAPI analytics service
- Real-time cost queries and reporting

## Configuration Files

### `config.yaml`
Main APISIX configuration:
- Node listening (port 9080)
- etcd connection
- Admin API settings
- Plugin configuration

### `apisix.yaml`
Routes and upstreams:
- OpenAI routes (`/v1/chat/completions`, `/v1/embeddings`)
- Anthropic routes (`/v1/messages`)
- Upstream definitions with retries and timeouts

### `dashboard_conf/conf.yaml`
APISIX Dashboard settings

### `init-scripts/01_init_cost_tracking.sql`
TimescaleDB schema:
- `llm_requests` table with agent tracking
- Continuous aggregates (hourly, daily)
- Indexes for fast queries
- Retention policies

## Quick Start

### 1. Start Services

```bash
# Start all services including APISIX
docker compose up -d

# Check APISIX health
curl http://localhost:9080/apisix/status

# Check dashboard
open http://localhost:9000
```

### 2. Verify Routes

```bash
# Test OpenAI route (will need API key in header)
curl -X POST http://localhost:9080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_OPENAI_KEY" \
  -H "X-Agent-Type: test" \
  -H "X-Agent-Name: manual-test" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}]}'
```

### 3. Check Cost Tracking

```bash
# View today's costs
docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT * FROM today_costs_by_agent;"

# Access analytics API
curl http://localhost:8090/api/costs/by-agent-type?days=1
```

## Agent-Level Cost Tracking

### Required Headers

All requests to LLM providers **must** include these headers for proper tracking:

```
X-Agent-Type: kodosumi_flow | chat_agent | etl_processor
X-Agent-Name: <specific-agent-name>
X-Flow-Name: <flow-name>               # For Kodosumi flows
X-Chat-Agent-Name: <chat-agent>        # For chat agents
X-Session-ID: <session-id>             # Track conversations/sessions
X-Trace-ID: <trace-id>                 # Optional distributed tracing
X-Project-ID: political_monitoring_v2  # Optional project identifier
```

### Example: Kodosumi Flow

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:9080/v1",
    default_headers={
        "X-Agent-Type": "kodosumi_flow",
        "X-Agent-Name": "data_ingestion_processor",
        "X-Flow-Name": "data_ingestion",
        "X-Session-ID": session_id,
        "X-Project-ID": "political_monitoring_v2"
    }
)
```

### Example: Chat Agent

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:9080/v1",
    default_headers={
        "X-Agent-Type": "chat_agent",
        "X-Chat-Agent-Name": "query_understanding",
        "X-Session-ID": conversation_id
    }
)
```

## Cost Analytics Endpoints

### Analytics API (Port 8090)

```bash
# Overall costs by agent type
GET /api/costs/by-agent-type?days=7

# Costs by Kodosumi flow
GET /api/costs/by-flow?days=7

# Costs by chat agent
GET /api/costs/by-chat-agent?days=7

# Flow efficiency metrics
GET /api/costs/flow-efficiency?flow_name=data_ingestion

# Session-specific costs
GET /api/costs/agent-sessions/{session_id}

# Agent leaderboard
GET /api/costs/agent-leaderboard?metric=cost&days=7

# Compare agents
GET /api/costs/comparison?agent_names[]=agent1&agent_names[]=agent2
```

## Database Schema

### Main Table: `llm_requests`

```sql
-- Core fields
timestamp        -- Request timestamp
provider         -- 'openai' or 'anthropic'
model            -- Model name
endpoint         -- API endpoint

-- Agent tracking
agent_type       -- Type of agent
agent_name       -- Specific agent
flow_name        -- Kodosumi flow name
chat_agent_name  -- Chat agent name
session_id       -- Session identifier
trace_id         -- Trace ID

-- Cost data
prompt_tokens
completion_tokens
total_tokens
cost_usd         -- Calculated cost

-- Performance
latency_ms
status_code
error_message
```

### Views

- `today_costs_by_agent` - Current day summary
- `llm_costs_hourly` - Hourly aggregates
- `llm_costs_daily` - Daily aggregates

## Monitoring

### APISIX Dashboard
- Access: http://localhost:9000
- Monitor routes, upstreams, plugins
- View real-time traffic

### Cost Analytics
- Access: http://localhost:8090
- Query cost data via REST API
- Build custom dashboards

### TimescaleDB Direct
```bash
# Connect to database
docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs

# Check recent requests
SELECT timestamp, provider, agent_name, total_tokens, cost_usd
FROM llm_requests
ORDER BY timestamp DESC
LIMIT 10;

# Agent leaderboard (today)
SELECT agent_name, COUNT(*), SUM(cost_usd) as cost
FROM llm_requests
WHERE timestamp >= CURRENT_DATE
GROUP BY agent_name
ORDER BY cost DESC;
```

## Configuration Management

### Environment Variables

Add to `.env`:

```bash
# APISIX Gateway
APISIX_ADMIN_KEY=edd1c9f034335f136f87ad84b625c8f1

# TimescaleDB
TIMESCALEDB_PASSWORD=timescale_secure_password

# LLM Provider Keys (will be moved to Infisical in Week 3)
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

### Update Application Code

Replace direct LLM provider URLs:

```python
# OLD
client = AsyncOpenAI(base_url="https://api.openai.com/v1")

# NEW
client = AsyncOpenAI(
    base_url="http://localhost:9080/v1",
    default_headers={
        "X-Agent-Type": "kodosumi_flow",
        "X-Agent-Name": "my_agent"
    }
)
```

## Development Workflow

### 1. Make Configuration Changes

```bash
# Edit config files
vi apisix/config.yaml
vi apisix/apisix.yaml

# Restart APISIX
docker compose restart apisix
```

### 2. Test Routes

```bash
# Check route is working
curl -v http://localhost:9080/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -X POST -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"test"}]}'
```

### 3. Monitor Costs

```bash
# Check if request was tracked
docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT * FROM llm_requests ORDER BY timestamp DESC LIMIT 5;"
```

## Troubleshooting

### APISIX not starting
```bash
# Check logs
docker logs policiytracker-apisix

# Verify etcd is running
docker ps | grep etcd

# Test etcd connection
docker exec policiytracker-etcd etcdctl endpoint health
```

### Routes not working
```bash
# Check APISIX admin API
curl http://localhost:9180/apisix/admin/routes \
  -H 'X-API-KEY: edd1c9f034335f136f87ad84b625c8f1'

# Check upstream health
curl http://localhost:9180/apisix/admin/upstreams \
  -H 'X-API-KEY: edd1c9f034335f136f87ad84b625c8f1'
```

### Cost tracking not working
```bash
# Check TimescaleDB is running
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c "SELECT version();"

# Check for recent inserts
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs -c \
  "SELECT COUNT(*) FROM llm_requests WHERE timestamp > NOW() - INTERVAL '5 minutes';"

# Check analytics API
curl http://localhost:8090/health
```

## Next Steps

### Week 2: Complete Cost Tracking
- [ ] Implement custom Lua cost-tracker plugin
- [ ] Build comprehensive analytics dashboard
- [ ] Set up budget alerts

### Week 3: Key Management
- [ ] Deploy Infisical for secrets management
- [ ] Migrate API keys from .env to Infisical
- [ ] Implement dynamic key injection in APISIX

## Resources

- [Apache APISIX Docs](https://apisix.apache.org/docs/apisix/getting-started/)
- [TimescaleDB Docs](https://docs.timescale.com/)
- [APISIX Plugin Development](https://apisix.apache.org/docs/apisix/plugin-develop/)

## Support

For issues or questions:
1. Check logs: `docker logs policiytracker-apisix`
2. Review APISIX dashboard: http://localhost:9000
3. Query cost database directly
4. Check this README for common solutions
