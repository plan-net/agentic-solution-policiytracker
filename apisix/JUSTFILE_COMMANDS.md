# APISIX Justfile Commands Quick Reference

All commands use the `just` task runner. Run `just --list` to see all available commands.

## 🚀 Quick Start

```bash
# 1. Start APISIX services
just apisix-up

# 2. Check status
just apisix-status

# 3. Test routing (requires API keys in .env)
just apisix-test-openai

# 4. View costs
just apisix-costs-today
```

## 📦 Service Management

### Start/Stop Services

```bash
# Start APISIX gateway services
just apisix-up
# Starts: etcd, apisix, apisix-dashboard, timescaledb, cost-analytics

# Stop APISIX services
just apisix-down

# Restart APISIX
just apisix-restart

# Check service status
just apisix-status

# View APISIX logs
just apisix-logs
```

### Access Dashboards

```bash
# Open APISIX Dashboard in browser
just apisix-ui
# Opens http://localhost:9000 (admin/admin)

# APISIX Gateway endpoint
open http://localhost:9080

# Cost Analytics API
open http://localhost:8090
```

## 🧪 Testing

### Test LLM Provider Routing

```bash
# Test OpenAI routing through APISIX
just apisix-test-openai
# Sends test request to OpenAI via gateway
# Requires OPENAI_API_KEY in .env

# Test Anthropic routing through APISIX
just apisix-test-anthropic
# Sends test request to Anthropic via gateway
# Requires ANTHROPIC_API_KEY in .env
```

### Manual Testing

```bash
# Test with your own prompts
curl -X POST http://localhost:9080/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "X-Agent-Type: manual-test" \
  -H "X-Agent-Name: my-test-agent" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello, world!"}]
  }'
```

## 💰 Cost Tracking

### View Costs

```bash
# Today's costs by agent
just apisix-costs-today
# Shows: agent_type, agent_name, requests, cost

# Last 7 days costs
just apisix-costs-week
# Shows top 20 agents by cost

# Recent requests (last 10)
just apisix-requests-recent
# Shows: timestamp, provider, agent, model, tokens, cost, latency
```

### Query Analytics API

```bash
# Query different cost metrics
just apisix-analytics by-agent-type
just apisix-analytics by-flow
just apisix-analytics by-chat-agent

# Available endpoints:
# - by-agent-type: Cost by agent type (kodosumi_flow, chat_agent, etc.)
# - by-flow: Cost by Kodosumi flow (data_ingestion, etc.)
# - by-chat-agent: Cost by chat agent (query_understanding, etc.)
# - flow-efficiency: Efficiency metrics per flow
```

### Direct Database Access

```bash
# Connect to TimescaleDB for custom queries
just apisix-db
# Opens psql shell in TimescaleDB container

# Example queries in psql:
# SELECT * FROM llm_requests LIMIT 10;
# SELECT * FROM today_costs_by_agent;
# SELECT * FROM llm_costs_hourly ORDER BY bucket DESC LIMIT 24;
```

## 🛠️ Utilities

### Database Management

```bash
# Clear all cost data (WARNING: Destructive!)
just apisix-clear-costs
# Requires confirmation

# View database schema
just apisix-db
# Then in psql: \dt (list tables), \d llm_requests (describe table)
```

### Setup Help

```bash
# Show setup instructions
just apisix-setup
# Displays step-by-step setup guide
```

## 📊 Integration with Main Commands

APISIX services are included in main commands:

```bash
# Start all services (includes APISIX)
just start

# Stop all services (includes APISIX)
just stop

# View all service status (includes APISIX)
just status

# View all service logs
just logs apisix
```

## 🔍 Monitoring & Debugging

### Check Service Health

```bash
# Check if APISIX is responding
curl http://localhost:9080/apisix/status

# Check etcd health
docker exec policiytracker-etcd etcdctl endpoint health

# Check TimescaleDB health
docker exec policiytracker-timescaledb pg_isready -U timescale

# Check cost analytics API
curl http://localhost:8090/health
```

### View Logs

```bash
# APISIX logs
just apisix-logs

# All APISIX-related container logs
docker compose logs -f apisix etcd timescaledb cost-analytics

# Specific container logs
docker logs policiytracker-apisix
docker logs policiytracker-timescaledb
```

### Troubleshooting

```bash
# Check Docker container status
docker compose ps

# Restart specific service
docker compose restart apisix

# Check etcd data
docker exec policiytracker-etcd etcdctl get --prefix /apisix

# Verify database tables
just apisix-db
# Then: \dt
```

## 📈 Example Workflow

### Daily Development

```bash
# 1. Start services
just start  # or just apisix-up for APISIX only

# 2. Make code changes to agents

# 3. Test routing
just apisix-test-openai

# 4. Check costs
just apisix-costs-today

# 5. View analytics
just apisix-analytics by-agent-type

# 6. Stop when done
just stop
```

### Cost Analysis

```bash
# 1. View recent activity
just apisix-requests-recent

# 2. Check weekly costs
just apisix-costs-week

# 3. Query specific metrics
just apisix-analytics by-flow

# 4. Deep dive with SQL
just apisix-db
# Run custom queries...

# 5. Export data
docker exec policiytracker-timescaledb psql -U timescale -d llm_costs \
  -c "COPY (SELECT * FROM llm_requests WHERE timestamp >= CURRENT_DATE) TO STDOUT CSV HEADER" \
  > costs_today.csv
```

## 🎯 Tips & Best Practices

1. **Always check status first**: Run `just apisix-status` before testing
2. **Use test commands**: `just apisix-test-openai` validates routing before integration
3. **Monitor costs regularly**: Run `just apisix-costs-today` daily
4. **Use analytics API**: More efficient than direct SQL for common queries
5. **Keep logs handy**: Run `just apisix-logs` in separate terminal during development

## 🔗 Related Documentation

- **Main Documentation**: `apisix/README.md`
- **Configuration**: `apisix/config.yaml`, `apisix/apisix.yaml`
- **Database Schema**: `apisix/init-scripts/01_init_cost_tracking.sql`
- **Full Command List**: Run `just --list`

## 🆘 Getting Help

```bash
# List all available commands
just --list

# Show APISIX setup instructions
just apisix-setup

# View main status with all URLs
just status
```
