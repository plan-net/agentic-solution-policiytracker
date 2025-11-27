# Political Monitoring Agent - Streamlined Task Runner

# Default recipe shows available commands
default:
    @just --list

# === Setup & Installation ===

# Initial setup for development environment
setup:
    @echo "🚀 Setting up development environment..."
    uv sync
    @if [ ! -f .env ]; then cp .env.template .env; echo "📝 Created .env from template"; fi
    @if [ ! -f config.yaml ]; then just sync-config; fi
    @mkdir -p data/input data/output data/context
    @echo "✅ Setup complete. Run 'just start' to launch services"

# Sync config.yaml from .env variables
sync-config:
    @echo "🔧 Syncing configuration..."
    uv run python scripts/sync_env_to_config.py

# === Service Management ===

# Start all services (Docker + Ray + Applications + Kodosumi)
start: services-up
    @echo "🚀 Starting Ray and deploying applications..."
    -uv run --active ray stop 2>/dev/null || true
    uv run --active ray start --head
    @sleep 2
    just deploy-all
    @echo "🚀 Starting Kodosumi admin panel..."
    -uv run --active koco stop 2>/dev/null || true
    nohup uv run koco start --register   > logs/kodosumi.log 2>&1 &
    @sleep 3
    @echo "✅ All services started!"
    @just status

# Stop all services
stop:
    @echo "🛑 Stopping all services..."
    -uv run --active koco stop 2>/dev/null || true
    -uv run --active serve shutdown --yes 2>/dev/null || true
    -uv run --active ray stop 2>/dev/null || true
    docker compose down
    @echo "✅ All services stopped"

# Restart all services
restart: stop start

# Show service status
status:
    @echo "📊 Service Status:"
    @echo "=================="
    @echo "🐳 Docker Services:"
    @docker compose ps
    @echo ""
    @echo "🌟 Ray Status:"
    @uv run --active ray status 2>/dev/null || echo "❌ Ray not running"
    @echo ""
    @echo "📦 Ray Applications:"
    @uv run --active serve status 2>/dev/null || echo "❌ No applications deployed"
    @echo ""
    @echo "🌐 Service URLs:"
    @echo "  🎛️  Kodosumi Admin: http://localhost:3370 (admin/admin)"
    @echo "  📊 Ray Dashboard:  http://localhost:8265"
    @echo "  💬 Open WebUI:     http://localhost:3000"
    @echo "  🗄️  Neo4j Browser:  http://localhost:7474 (neo4j/password123)"
    @echo "  🔍 Langfuse:       http://localhost:3001 (disabled, use 'just langfuse-up')"
    @echo "  ✈️  Airflow:        http://localhost:8080 (admin/admin)"
    @echo "  ☁️  Azurite:        http://localhost:10000 (blob storage)"
    @echo "  🤖 Graphiti MCP:   http://localhost:8000 (SSE endpoint)"
    @echo "  🚪 APISIX Gateway: http://localhost:9080 (LLM API Gateway)"
    @echo "  🎛️  APISIX Dashboard: http://localhost:9000 (admin/admin)"
    @echo "  📊 Cost Analytics: http://localhost:8090 (Cost tracking API)"
    @echo ""
    @echo "  📡 API Endpoints:"
    @echo "  🗨️  Chat API:       http://localhost:8001/v1/chat/completions"
    @echo "  📝 Data Ingestion: http://localhost:8001/data-ingestion"
    @echo "  🔄 ETL Health:     http://localhost:8080/health"
    @echo "  🌐 LLM Gateway:    http://localhost:9080/v1/* (via APISIX)"


# === Application Deployment ===

# Deploy all applications
deploy-all: sync-config
    @echo "📦 Deploying all applications..."
    uv run --active serve deploy config.yaml
    @echo "✅ All applications deployed"

# Deploy only data ingestion flow
deploy-data:
    @echo "📦 Deploying data ingestion..."
    just sync-config
    uv run --active serve deploy config.yaml --app flow1-data-ingestion
    @echo "✅ Data ingestion deployed"

# Deploy only bulk auto-delta flow
deploy-bulk-auto:
    @echo "📦 Deploying bulk auto-delta flow..."
    just sync-config
    uv run --active serve deploy config.yaml --app flow1b-bulk-auto
    @echo "✅ Bulk auto-delta flow deployed"

# Deploy only ad-hoc flow
deploy-adhoc:
    @echo "📦 Deploying ad-hoc processing flow..."
    just sync-config
    uv run --active serve deploy config.yaml --app flow1c-adhoc
    @echo "✅ Ad-hoc processing flow deployed"

# Deploy only raw document converter flow
deploy-raw-converter:
    @echo "📦 Deploying raw document converter + Graphiti flow..."
    just sync-config
    uv run --active serve deploy config.yaml --app flow1d-raw-converter
    @echo "✅ Raw document converter flow deployed"

# Deploy only chat server
deploy-chat:
    @echo "📦 Deploying chat server..."
    just sync-config
    uv run --active serve deploy config.yaml --app chat-server
    @echo "✅ Chat server deployed"

# Deploy Bundestag ingestion flow (Flow 5)
deploy-bundestag:
    @echo "📦 Deploying Bundestag ingestion flow..."
    just sync-config
    uv run --active serve deploy config.yaml
    @echo "✅ Bundestag ingestion flow deployed (part of full deployment)"

# Quick redeploy (for development)
redeploy: sync-config
    @echo "🔄 Quick redeployment..."
    -uv run --active serve shutdown --yes 2>/dev/null || true
    uv run --active serve deploy config.yaml
    @echo "✅ Applications redeployed"

# === Docker Services ===

# Start Docker services only (excluding Langfuse)
services-up:
    @echo "🐳 Starting Docker services (excluding Langfuse)..."
    docker compose up -d --scale langfuse-server=0
    @echo "✅ Docker services started (Langfuse disabled)"

# Stop Docker services
services-down:
    docker compose down

# Start Langfuse observability service (optional)
langfuse-up:
    @echo "🔭 Starting Langfuse observability..."
    docker compose up -d langfuse-server
    @echo "✅ Langfuse started at http://localhost:3001"

# Stop Langfuse service
langfuse-down:
    @echo "🛑 Stopping Langfuse..."
    docker compose stop langfuse-server
    @echo "✅ Langfuse stopped"

# View service logs
logs service="":
    @if [ "{{service}}" = "" ]; then \
        docker compose logs -f; \
    else \
        docker compose logs -f {{service}}; \
    fi

# === Data & Analysis ===

# Import sample data to Azurite
import-data:
    @echo "📤 Importing sample data..."
    uv run python scripts/import_data_to_azurite.py

# Build communities from knowledge graph
build-communities:
    @echo "🏘️ Building communities from graph..."
    uv run python scripts/build_communities.py

# Upload prompts to Langfuse
upload-prompts:
    @echo "📤 Uploading prompts to Langfuse..."
    uv run python scripts/upload_prompts_to_langfuse.py

# Test ETL pipeline
test-etl:
    @echo "🧪 Testing ETL pipeline..."
    uv run python scripts/test_policy_collection.py

# Check ETL initialization status
etl-status:
    @echo "📊 ETL Initialization Status:"
    uv run python scripts/etl_init_manager.py status

# Load Bundestag Wahlperiode reference data into Neo4j
load-wahlperioden:
    @echo "📅 Loading Bundestag Wahlperioden to Neo4j..."
    uv run python src/flows/bundestag_wahlperiode/load_wahlperioden.py

# Load Bundestag Fraktion reference data into Neo4j
load-fraktionen:
    @echo "🏛️  Loading Bundestag Fraktionen to Neo4j..."
    uv run python src/flows/bundestag_fraktion/load_fraktionen.py

# Reset specific ETL collector
etl-reset collector:
    @echo "🔄 Resetting ETL collector: {{collector}}"
    uv run python scripts/etl_init_manager.py reset {{collector}}

# Reset all ETL collectors
etl-reset-all:
    @echo "🔄 Resetting ALL ETL collectors..."
    uv run python scripts/etl_init_manager.py reset-all

# === BundestagPerson Manager (CRUD System) ===

# Run complete BundestagPerson Manager demo
demo-crud:
    @echo "🎯 Running BundestagPerson Manager demo..."
    uv run python scripts/demo_bundestag_person_manager.py

# Sync all BundestagPerson records (with mock DIP API)
sync-persons:
    @echo "🔄 Syncing BundestagPerson records..."
    uv run python -c "import asyncio; from src.skills.bundestag_person_manager import BundestagPersonManager; import json; result = asyncio.run(BundestagPersonManager(use_mock_dip=True).sync_all_persons()); print('\n✅ Sync Complete:'); print(json.dumps(result.to_dict(), indent=2))"

# Check BundestagPerson sync status
check-sync:
    @echo "📊 Checking sync status..."
    uv run python -c "import asyncio; from src.skills.bundestag_person_manager import BundestagPersonManager; import json; m = BundestagPersonManager(use_mock_dip=True); status = asyncio.run(m.check_sync_status()); print('\n📊 Sync Status:'); print(json.dumps(status, indent=2)); m.close()"

# Dry run sync (preview changes without applying)
sync-persons-dry:
    @echo "👀 Performing dry run..."
    uv run python -c "import asyncio; from src.skills.bundestag_person_manager import BundestagPersonManager; import json; result = asyncio.run(BundestagPersonManager(use_mock_dip=True).sync_all_persons(dry_run=True)); print('\n📊 Dry Run Results:'); print(json.dumps(result.to_dict(), indent=2))"

# Check MCP server health
crud-health:
    @echo "🏥 Checking CRUD system health..."
    @curl -s http://localhost:8002/health | python -m json.tool || echo "❌ MCP server not accessible"

# === BundestagVorgang Manager (CRUD System) ===

# Run complete BundestagVorgang Manager demo
demo-vorgang:
    @echo "🎯 Running BundestagVorgang Manager demo..."
    uv run python scripts/demo_bundestag_vorgang_manager.py

# Sync all Vorgang records (with real DIP API)
# Usage: just sync-vorgaenge 21 1000
sync-vorgaenge wahlperiode="21" max_items="1000":
    @echo "🔄 Syncing Vorgang records (Wahlperiode {{wahlperiode}}, max {{max_items}} items)..."
    uv run python -c "from dotenv import load_dotenv; load_dotenv(); import asyncio; from src.skills.bundestag_vorgang_manager import BundestagVorgangManager; import json; result = asyncio.run(BundestagVorgangManager(use_mock_dip=False).sync_all_vorgaenge(limit=int('{{max_items}}'), wahlperiode='{{wahlperiode}}')); print('\n✅ Sync Complete:'); print(json.dumps(result.to_dict(), indent=2))"

# Check Vorgang sync status (with real DIP API)
check-vorgang-sync:
    @echo "📊 Checking Vorgang sync status (Real DIP API)..."
    uv run python -c "from dotenv import load_dotenv; load_dotenv(); import asyncio; from src.skills.bundestag_vorgang_manager import BundestagVorgangManager; import json; m = BundestagVorgangManager(use_mock_dip=False); status = asyncio.run(m.check_sync_status()); print('\n📊 Vorgang Sync Status:'); print(json.dumps(status, indent=2)); m.close()"

# Dry run Vorgang sync (preview changes without applying, with real DIP API)
# Usage: just sync-vorgaenge-dry 21 1000
sync-vorgaenge-dry wahlperiode="21" max_items="1000":
    @echo "👀 Performing Vorgang dry run (Wahlperiode {{wahlperiode}}, max {{max_items}} items)..."
    uv run python -c "from dotenv import load_dotenv; load_dotenv(); import asyncio; from src.skills.bundestag_vorgang_manager import BundestagVorgangManager; import json; result = asyncio.run(BundestagVorgangManager(use_mock_dip=False).sync_all_vorgaenge(limit=int('{{max_items}}'), wahlperiode='{{wahlperiode}}', dry_run=True)); print('\n📊 Dry Run Results:'); print(json.dumps(result.to_dict(), indent=2))"

# === BundestagDrucksache Manager (CRUD System) ===

# Run complete BundestagDrucksache Manager demo
demo-drucksache:
    @echo "🎯 Running BundestagDrucksache Manager demo..."
    uv run python scripts/demo_bundestag_drucksache_manager.py

# Sync all Drucksache records (with mock DIP API)
sync-drucksachen:
    @echo "🔄 Syncing Drucksache records..."
    uv run python -c "import asyncio; from src.skills.bundestag_drucksache_manager import BundestagDrucksacheManager; import json; result = asyncio.run(BundestagDrucksacheManager(use_mock_dip=True).sync_all_drucksachen()); print('\n✅ Sync Complete:'); print(json.dumps(result.to_dict(), indent=2))"

# Check Drucksache sync status
check-drucksache-sync:
    @echo "📊 Checking Drucksache sync status..."
    uv run python -c "import asyncio; from src.skills.bundestag_drucksache_manager import BundestagDrucksacheManager; import json; m = BundestagDrucksacheManager(use_mock_dip=True); status = asyncio.run(m.check_sync_status()); print('\n📊 Drucksache Sync Status:'); print(json.dumps(status, indent=2)); m.close()"

# Dry run Drucksache sync (preview changes without applying)
sync-drucksachen-dry:
    @echo "👀 Performing Drucksache dry run..."
    uv run python -c "import asyncio; from src.skills.bundestag_drucksache_manager import BundestagDrucksacheManager; import json; result = asyncio.run(BundestagDrucksacheManager(use_mock_dip=True).sync_all_drucksachen(dry_run=True)); print('\n📊 Dry Run Results:'); print(json.dumps(result.to_dict(), indent=2))"

# Aktivitaet Manager commands
demo-aktivitaet:
    @echo "🎯 Running BundestagAktivitaet Manager demo..."
    uv run python scripts/demo_bundestag_aktivitaet_manager.py

# Sync all Aktivitaeten from DIP API to Neo4j
sync-aktivitaeten:
    @echo "🔄 Syncing Aktivitaet records..."
    uv run python -c "import asyncio; from src.skills.bundestag_aktivitaet_manager import BundestagAktivitaetManager; import json; result = asyncio.run(BundestagAktivitaetManager(use_mock_dip=True).sync_all_aktivitaeten()); print('\n✅ Sync Complete:'); print(json.dumps(result.to_dict(), indent=2))"

# Check Aktivitaet sync status
check-aktivitaet-sync:
    @echo "📊 Checking Aktivitaet sync status..."
    uv run python -c "import asyncio; from src.skills.bundestag_aktivitaet_manager import BundestagAktivitaetManager; import json; m = BundestagAktivitaetManager(use_mock_dip=True); status = asyncio.run(m.check_sync_status()); print('\n📊 Aktivitaet Sync Status:'); print(json.dumps(status, indent=2)); m.close()"

# Dry run - preview Aktivitaet sync changes without applying
sync-aktivitaeten-dry:
    @echo "👀 Performing Aktivitaet dry run..."
    uv run python -c "import asyncio; from src.skills.bundestag_aktivitaet_manager import BundestagAktivitaetManager; import json; result = asyncio.run(BundestagAktivitaetManager(use_mock_dip=True).sync_all_aktivitaeten(dry_run=True)); print('\n📊 Dry Run Results:'); print(json.dumps(result.to_dict(), indent=2))"

# Plenarprotokoll Manager commands
demo-plenarprotokoll:
    @echo "🎯 Running BundestagPlenarprotokoll Manager demo..."
    uv run python scripts/demo_bundestag_plenarprotokoll_manager.py

# Sync all Plenarprotokolle from DIP API to Neo4j
sync-plenarprotokolle:
    @echo "🔄 Syncing Plenarprotokoll records..."
    uv run python -c "import asyncio; from src.skills.bundestag_plenarprotokoll_manager import BundestagPlenarprotokollManager; import json; result = asyncio.run(BundestagPlenarprotokollManager(use_mock_dip=True).sync_all_plenarprotokolle()); print('\n✅ Sync Complete:'); print(json.dumps(result.to_dict(), indent=2))"

# Check Plenarprotokoll sync status
check-plenarprotokoll-sync:
    @echo "📊 Checking Plenarprotokoll sync status..."
    uv run python -c "import asyncio; from src.skills.bundestag_plenarprotokoll_manager import BundestagPlenarprotokollManager; import json; m = BundestagPlenarprotokollManager(use_mock_dip=True); status = asyncio.run(m.check_sync_status()); print('\n📊 Plenarprotokoll Sync Status:'); print(json.dumps(status, indent=2)); m.close()"

# Dry run - preview Plenarprotokoll sync changes without applying
sync-plenarprotokolle-dry:
    @echo "👀 Performing Plenarprotokoll dry run..."
    uv run python -c "import asyncio; from src.skills.bundestag_plenarprotokoll_manager import BundestagPlenarprotokollManager; import json; result = asyncio.run(BundestagPlenarprotokollManager(use_mock_dip=True).sync_all_plenarprotokolle(dry_run=True)); print('\n📊 Dry Run Results:'); print(json.dumps(result.to_dict(), indent=2))"

# === Development ===

# Run tests
test:
    uv run pytest -v

# Format and lint code
format:
    uv run ruff format src tests
    uv run ruff check src tests --fix

# Type check
typecheck:
    uv run mypy src

# Watch Ray logs
ray-logs:
    uv run --active ray logs cluster dashboard_ServeHead.out --tail 100 -f


# === Database Management ===

# Clear Neo4j database
neo4j-clear:
    @echo "⚠️  This will delete ALL graph data!"
    @read -p "Continue? (y/N) " -n 1 -r; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        echo ""; \
        docker compose exec neo4j cypher-shell -u neo4j -p password123 "MATCH (n) DETACH DELETE n;"; \
        echo "✅ Neo4j cleared"; \
    fi

# === Cleanup ===

# Clean temporary files
clean:
    @echo "🧹 Cleaning up..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    rm -rf htmlcov .coverage/* 2>/dev/null || true

# Full cleanup (including Docker volumes)
clean-all: stop clean
    docker system prune -f
    @echo "✅ Full cleanup complete"


# === APISIX API Gateway Management ===

# Start APISIX gateway services
apisix-up:
    @echo "🚪 Starting APISIX gateway services..."
    docker compose up -d etcd apisix apisix-dashboard timescaledb
    @echo "⏳ Waiting for services to be healthy..."
    @sleep 10
    @just apisix-status

# Stop APISIX services
apisix-down:
    @echo "🛑 Stopping APISIX services..."
    docker compose stop timescaledb apisix-dashboard apisix etcd

# Restart APISIX services
apisix-restart:
    @echo "🔄 Restarting APISIX services..."
    docker compose restart apisix

# View APISIX logs
apisix-logs:
    docker compose logs -f apisix

# Check APISIX service status
apisix-status:
    @echo "📊 APISIX Service Status:"
    @docker compose ps apisix etcd apisix-dashboard timescaledb
    @echo ""
    @echo "🌐 APISIX Gateway: http://localhost:9080"
    @echo "🎛️  APISIX Dashboard: http://localhost:9000 (admin/admin)"
    @echo ""
    @echo "Testing gateway health..."
    @curl -s http://localhost:9080/apisix/status || echo "❌ APISIX not responding"

# Open APISIX Dashboard in browser
apisix-ui:
    @echo "🌐 Opening APISIX Dashboard..."
    open http://localhost:9000 || xdg-open http://localhost:9000 || echo "Please visit: http://localhost:9000 (admin/admin)"

# Test APISIX routing to OpenAI
apisix-test-openai:
    @echo "🧪 Testing APISIX → OpenAI routing..."
    @echo "Note: Requires OPENAI_API_KEY in .env"
    @if [ -z "$$OPENAI_API_KEY" ]; then \
        echo "❌ OPENAI_API_KEY not set in environment"; \
        exit 1; \
    fi
    curl -X POST http://localhost:9080/v1/chat/completions \
      -H "Authorization: Bearer $$OPENAI_API_KEY" \
      -H "X-Agent-Type: test" \
      -H "X-Agent-Name: justfile-test" \
      -H "Content-Type: application/json" \
      -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Say hello"}],"max_tokens":10}'

# Test APISIX routing to Anthropic
apisix-test-anthropic:
    @echo "🧪 Testing APISIX → Anthropic routing..."
    @echo "Note: Requires ANTHROPIC_API_KEY in .env"
    @if [ -z "$$ANTHROPIC_API_KEY" ]; then \
        echo "❌ ANTHROPIC_API_KEY not set in environment"; \
        exit 1; \
    fi
    curl -X POST http://localhost:9080/v1/messages \
      -H "x-api-key: $$ANTHROPIC_API_KEY" \
      -H "anthropic-version: 2023-06-01" \
      -H "X-Agent-Type: test" \
      -H "X-Agent-Name: justfile-test" \
      -H "Content-Type: application/json" \
      -d '{"model":"claude-3-haiku-20240307","messages":[{"role":"user","content":"Say hello"}],"max_tokens":10}'

# View cost tracking data (today)
apisix-costs-today:
    @echo "💰 Today's LLM Costs by Agent:"
    docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c \
      "SELECT agent_type, agent_name, COUNT(*) as requests, SUM(cost_usd) as cost FROM llm_requests WHERE timestamp >= CURRENT_DATE GROUP BY agent_type, agent_name ORDER BY cost DESC;"

# View cost tracking data (last 7 days)
apisix-costs-week:
    @echo "💰 Last 7 Days LLM Costs by Agent:"
    docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c \
      "SELECT agent_type, agent_name, COUNT(*) as requests, SUM(cost_usd) as cost FROM llm_requests WHERE timestamp > NOW() - INTERVAL '7 days' GROUP BY agent_type, agent_name ORDER BY cost DESC LIMIT 20;"

# View recent LLM requests
apisix-requests-recent:
    @echo "📜 Recent LLM Requests (last 10):"
    docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c \
      "SELECT timestamp, provider, agent_name, model, total_tokens, cost_usd, latency_ms FROM llm_requests ORDER BY timestamp DESC LIMIT 10;"

# Query cost analytics API
apisix-analytics query="by-agent-type":
    @echo "📊 Querying cost analytics: {{query}}"
    curl -s "http://localhost:8090/api/costs/{{query}}?days=7" | python3 -m json.tool

# Connect to TimescaleDB for custom queries
apisix-db:
    @echo "🗄️  Connecting to TimescaleDB..."
    docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs

# Clear cost tracking data (WARNING: Destructive)
apisix-clear-costs:
    @echo "⚠️  This will delete ALL cost tracking data!"
    @read -p "Continue? (y/N) " -n 1 -r; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        echo ""; \
        docker exec -it policiytracker-timescaledb psql -U timescale -d llm_costs -c "TRUNCATE llm_requests;"; \
        echo "✅ Cost data cleared"; \
    fi

# APISIX setup instructions
apisix-setup:
    @echo "📝 APISIX Setup Instructions:"
    @echo ""
    @echo "1. Start services: just apisix-up"
    @echo "2. Access Dashboard at http://localhost:9000 (admin/admin)"
    @echo "3. Test routing: just apisix-test-openai"
    @echo "4. View costs: just apisix-costs-today"
    @echo "5. Analytics API: http://localhost:8090"
    @echo ""
    @echo "For detailed documentation, see: apisix/README.md"

# === LangWatch Observability ===

# Start LangWatch services
langwatch-up:
    @echo "🔭 Starting LangWatch services..."
    docker compose up -d langwatch-postgres langwatch-clickhouse langwatch-elasticsearch langwatch-server
    @echo "⏳ Waiting for services to be healthy..."
    @sleep 15
    @just langwatch-status

# Stop LangWatch services
langwatch-down:
    @echo "🛑 Stopping LangWatch services..."
    docker compose stop langwatch-server langwatch-elasticsearch langwatch-clickhouse langwatch-postgres

# View LangWatch logs
langwatch-logs:
    docker compose logs -f langwatch-server

# Check LangWatch service status
langwatch-status:
    @echo "📊 LangWatch Service Status:"
    @docker compose ps langwatch-server langwatch-postgres langwatch-clickhouse langwatch-elasticsearch
    @echo ""
    @echo "🌐 LangWatch UI: http://localhost:5560"

# Open LangWatch UI in browser
langwatch-ui:
    @echo "🌐 Opening LangWatch UI..."
    open http://localhost:5560 || xdg-open http://localhost:5560 || echo "Please visit: http://localhost:5560"

# Setup instructions for LangWatch
langwatch-setup:
    @echo "📝 LangWatch Setup Instructions:"
    @echo ""
    @echo "1. Start services: just langwatch-up"
    @echo "2. Access LangWatch UI at http://localhost:5560"
    @echo "3. Create account and project"
    @echo "4. Go to Settings → API Keys"
    @echo "5. Generate new API key"
    @echo "6. Add to .env: LANGWATCH_API_KEY=<your-key>"
    @echo "7. Set ENABLE_LANGWATCH=true in .env"
    @echo "8. Restart services: just restart"

# Test LangWatch integration
test-langwatch:
    @echo "🧪 Testing LangWatch integration..."
    uv run pytest tests/integration/test_langwatch_integration.py -v

# === Quick Access Commands ===

# Quick development cycle
dev: start
    @echo "💡 Development environment ready!"
    @echo "🔄 Use 'just redeploy' after code changes"

# Test chat API
test-chat:
    @echo "🧪 Testing chat API..."
    curl -X POST http://localhost:8001/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model": "political-monitoring-agent", "messages": [{"role": "user", "content": "What is the EU AI Act?"}]}'

# Test data ingestion
test-ingestion:
    @echo "🧪 Testing data ingestion..."
    curl http://localhost:8001/data-ingestion/health

# Check Bundestag flow health
bundestag-status:
    @echo "📊 Bundestag Ingestion Flow Status"
    @echo "=================================="
    @echo ""
    @echo "Checking Ray deployment..."
    @uv run --active serve status | grep -A 5 "flow5-bundestag-ingestion" || echo "❌ Flow not deployed"
    @echo ""
    @echo "Testing health endpoint..."
    @curl -s http://localhost:8001/bundestag-ingestion/health || echo "❌ Health endpoint not responding"
    @echo ""
    @echo ""
    @echo "Flow Information:"
    @echo "  Endpoint:       http://localhost:8001/bundestag-ingestion"
    @echo "  Kodosumi Admin: http://localhost:3370"
    @echo "  API Base:       https://search.dip.bundestag.de/api/v1/"
    @echo ""
    @echo "To deploy flow: just deploy-bundestag"
    @echo "To view logs:   just ray-logs"