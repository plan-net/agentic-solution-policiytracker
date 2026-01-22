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
    @echo "  🔍 LangFuse:       http://localhost:3001 (use 'just langfuse-up' to enable)"
    @echo "  ✈️  Airflow:        http://localhost:8080 (admin/admin)"
    @echo "  ☁️  Azurite:        http://localhost:10000 (blob storage)"
    @echo "  🤖 Graphiti MCP:   http://localhost:8000 (SSE endpoint)"
    @echo "  🚪 APISIX Gateway: http://localhost:9080 (LLM API Gateway)"
    @echo "  🎛️  APISIX Dashboard: http://localhost:9000 (admin/admin)"
    @echo "  📊 Cost Analytics: http://localhost:8090 (Cost tracking API)"
    @echo "  📈 Grafana:        http://localhost:3002 (admin/admin123)"
    @echo ""
    @echo "  📡 API Endpoints:"
    @echo "  🗨️  Chat API:       http://localhost:8001/v1/chat/completions"
    @echo "  🤖 Claude Agent:   http://localhost:8001/claude-agent/v1/chat/completions"
    @echo "  📊 Graph Viz:      http://localhost:8001/graph-viz/api/graph/chat-context"
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

# Start Docker services only (excluding LangFuse)
services-up:
    @echo "🐳 Starting Docker services (excluding LangFuse observability)..."
    docker compose up -d --scale langfuse-clickhouse=0 --scale langfuse-redis=0 --scale langfuse-minio=0 --scale langfuse-worker=0 --scale langfuse-web=0
    @echo "✅ Docker services started (LangFuse disabled, use 'just langfuse-up' to enable)"

# Stop Docker services
services-down:
    docker compose down

# Start LangFuse v3 observability stack (recommended)
langfuse-up:
    @echo "🔭 Starting LangFuse v3 observability stack..."
    docker compose up -d postgres langfuse-clickhouse langfuse-redis langfuse-minio langfuse-worker langfuse-web
    @echo "⏳ Waiting for services to be healthy (~30-60 seconds)..."
    @sleep 30
    @just langfuse-status
    @echo ""
    @echo "📝 Next steps:"
    @echo "  1. Visit http://localhost:3001"
    @echo "  2. Create account and organization"
    @echo "  3. Go to Settings → API Keys"
    @echo "  4. Copy keys to .env (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)"
    @echo "  5. Set OBSERVABILITY_PROVIDER=langfuse in .env"

# Stop LangFuse services
langfuse-down:
    @echo "🛑 Stopping LangFuse services..."
    docker compose stop langfuse-web langfuse-worker langfuse-minio langfuse-redis langfuse-clickhouse
    @echo "✅ LangFuse stopped"

# Restart LangFuse services
langfuse-restart:
    @echo "🔄 Restarting LangFuse services..."
    docker compose restart langfuse-web langfuse-worker
    @echo "✅ LangFuse restarted"

# View LangFuse logs (all services or specific)
langfuse-logs service="langfuse-web":
    @echo "📜 Viewing LangFuse logs for {{service}}..."
    docker compose logs -f {{service}}

# Check LangFuse service status
langfuse-status:
    @echo "📊 LangFuse v3 Service Status:"
    @echo "=============================="
    @docker compose ps langfuse-web langfuse-worker langfuse-clickhouse langfuse-redis langfuse-minio postgres 2>/dev/null || echo "Services not running"
    @echo ""
    @echo "🌐 LangFuse UI: http://localhost:3001"
    @echo ""
    @echo "Testing LangFuse health..."
    @curl -s http://localhost:3001/api/public/health 2>/dev/null | python3 -m json.tool || echo "❌ LangFuse not responding (may still be starting)"

# Open LangFuse UI in browser
langfuse-ui:
    @echo "🌐 Opening LangFuse UI..."
    open http://localhost:3001 || xdg-open http://localhost:3001 || echo "Please visit: http://localhost:3001"

# Setup instructions for LangFuse v3
langfuse-setup:
    @echo "📝 LangFuse v3 Setup Instructions:"
    @echo ""
    @echo "1. Start LangFuse stack:"
    @echo "   just langfuse-up"
    @echo ""
    @echo "2. Wait for services to be healthy (~60 seconds)"
    @echo ""
    @echo "3. Access LangFuse UI:"
    @echo "   http://localhost:3001"
    @echo ""
    @echo "4. Create account and organization"
    @echo ""
    @echo "5. Get API keys:"
    @echo "   Settings → API Keys → Create new API key"
    @echo ""
    @echo "6. Update .env file:"
    @echo "   OBSERVABILITY_PROVIDER=langfuse"
    @echo "   LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx"
    @echo "   LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx"
    @echo "   LANGFUSE_HOST=http://localhost:3001"
    @echo ""
    @echo "7. (Optional) Upload prompts to LangFuse:"
    @echo "   just upload-prompts"
    @echo ""
    @echo "8. Restart services to apply:"
    @echo "   just restart"
    @echo ""
    @echo "For more details, see: .claude/plans/parallel-wibbling-shell.md"

# View LangFuse MinIO console (blob storage)
langfuse-minio:
    @echo "🌐 Opening MinIO Console..."
    @echo "Login: langfuse / langfuse_minio_password"
    open http://localhost:9093 || xdg-open http://localhost:9093 || echo "Please visit: http://localhost:9093"

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

# Test LangFuse tracing
test-langfuse:
    @echo "🧪 Testing LangFuse tracing..."
    uv run python scripts/test_langfuse_trace.py

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

# === Claude Agent (PolicyTracker) ===

# Deploy Claude Agent only
deploy-claude-agent:
    @echo "📦 Deploying Claude Agent..."
    just sync-config
    uv run --active serve deploy config.yaml --app claude-agent
    @echo "✅ Claude Agent deployed at http://localhost:8001/claude-agent"

# Test Claude Agent health
claude-agent-health:
    @echo "🏥 Checking Claude Agent health..."
    @curl -s http://localhost:8001/claude-agent/health | python -m json.tool || echo "❌ Claude Agent not accessible"

# Test Claude Agent chat (non-streaming)
test-claude-agent:
    @echo "🧪 Testing Claude Agent chat API..."
    curl -X POST http://localhost:8001/claude-agent/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model": "claude-policytracker", "messages": [{"role": "user", "content": "What is the EU AI Act?"}]}'

# Test Claude Agent chat (streaming)
test-claude-agent-stream:
    @echo "🧪 Testing Claude Agent streaming chat API..."
    curl -X POST http://localhost:8001/claude-agent/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model": "claude-policytracker", "messages": [{"role": "user", "content": "What is the EU AI Act?"}], "stream": true}'

# Test Claude Agent with custom session ID
test-claude-session session_id="test-session-001":
    @echo "🧪 Testing Claude Agent with session ID: {{session_id}}"
    curl -X POST http://localhost:8001/claude-agent/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model": "claude-policytracker", "messages": [{"role": "user", "content": "Tell me about GDPR"}], "session_id": "{{session_id}}"}'

# Get graph context for a session (use with graph-viz server)
get-session-graph session_id:
    @echo "📊 Getting graph context for session: {{session_id}}"
    curl -X POST http://localhost:8001/graph-viz/api/graph/chat-context \
      -H "Content-Type: application/json" \
      -d '{"session_id": "{{session_id}}"}'

# List Claude Agent models
claude-agent-models:
    @echo "📋 Listing Claude Agent models..."
    @curl -s http://localhost:8001/claude-agent/v1/models | python -m json.tool || echo "❌ Claude Agent not accessible"

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
    docker compose up -d etcd apisix apisix-dashboard timescaledb cost-analytics
    @echo "⏳ Waiting for services to be healthy..."
    @sleep 10
    @just apisix-status

# Stop APISIX services
apisix-down:
    @echo "🛑 Stopping APISIX services..."
    docker compose stop cost-analytics timescaledb apisix-dashboard apisix etcd

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

# === Grafana Cost Dashboard ===

# Start Grafana dashboard
grafana-up:
    @echo "📊 Starting Grafana dashboard..."
    docker compose up -d grafana
    @echo "⏳ Waiting for Grafana to be healthy..."
    @sleep 10
    @just grafana-status

# Stop Grafana service
grafana-down:
    @echo "🛑 Stopping Grafana..."
    docker compose stop grafana

# View Grafana logs
grafana-logs:
    docker compose logs -f grafana

# Check Grafana service status
grafana-status:
    @echo "📊 Grafana Service Status:"
    @docker compose ps grafana
    @echo ""
    @echo "🌐 Grafana Dashboard: http://localhost:3002"
    @echo "🔐 Login: admin / admin123"
    @echo ""
    @echo "Testing Grafana health..."
    @curl -s http://localhost:3002/api/health | python3 -m json.tool || echo "❌ Grafana not responding"

# Open Grafana dashboard in browser
grafana-ui:
    @echo "🌐 Opening Grafana Dashboard..."
    open http://localhost:3002 || xdg-open http://localhost:3002 || echo "Please visit: http://localhost:3002 (admin/admin123)"

# === LangWatch Observability (DEPRECATED - Use LangFuse instead) ===
# NOTE: LangWatch is being replaced by LangFuse v3.
# Use 'just langfuse-up' for the recommended observability stack.
# LangWatch commands kept for backward compatibility during migration.

# Start LangWatch services (DEPRECATED)
langwatch-up:
    @echo "⚠️  WARNING: LangWatch is deprecated. Consider using LangFuse instead: just langfuse-up"
    @echo ""
    @echo "🔭 Starting LangWatch services..."
    docker compose up -d langwatch-postgres langwatch-clickhouse langwatch-elasticsearch langwatch-server
    @echo "⏳ Waiting for services to be healthy..."
    @sleep 15
    @just langwatch-status

# Stop LangWatch services (DEPRECATED)
langwatch-down:
    @echo "🛑 Stopping LangWatch services..."
    docker compose stop langwatch-server langwatch-elasticsearch langwatch-clickhouse langwatch-postgres

# View LangWatch logs (DEPRECATED)
langwatch-logs:
    docker compose logs -f langwatch-server

# Check LangWatch service status (DEPRECATED)
langwatch-status:
    @echo "📊 LangWatch Service Status (DEPRECATED - use 'just langfuse-status'):"
    @docker compose ps langwatch-server langwatch-postgres langwatch-clickhouse langwatch-elasticsearch 2>/dev/null || echo "LangWatch services not defined in docker-compose.yml"
    @echo ""
    @echo "🌐 LangWatch UI: http://localhost:5560"

# Open LangWatch UI in browser (DEPRECATED)
langwatch-ui:
    @echo "⚠️  LangWatch is deprecated. Consider LangFuse: just langfuse-ui"
    open http://localhost:5560 || xdg-open http://localhost:5560 || echo "Please visit: http://localhost:5560"

# Setup instructions for LangWatch (DEPRECATED)
langwatch-setup:
    @echo "⚠️  LangWatch is DEPRECATED. Use LangFuse instead:"
    @echo "   just langfuse-setup"
    @echo ""
    @echo "📝 Legacy LangWatch Setup Instructions:"
    @echo ""
    @echo "1. Start services: just langwatch-up"
    @echo "2. Access LangWatch UI at http://localhost:5560"
    @echo "3. Create account and project"
    @echo "4. Go to Settings → API Keys"
    @echo "5. Generate new API key"
    @echo "6. Add to .env: LANGWATCH_API_KEY=<your-key>"
    @echo "7. Set OBSERVABILITY_PROVIDER=langwatch in .env"
    @echo "8. Restart services: just restart"

# Test LangWatch integration (DEPRECATED)
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

# === Embedding Migration ===

# Fix embedding dimension mismatch (1024 -> 1536)
fix-embeddings mode="dry-run":
    @echo "🔧 Fixing embedding dimensions (1024 -> 1536)..."
    @if [ "{{mode}}" = "execute" ]; then \
        uv run python scripts/fix_embedding_dimensions.py --execute; \
    elif [ "{{mode}}" = "verify" ]; then \
        uv run python scripts/fix_embedding_dimensions.py --verify; \
    elif [ "{{mode}}" = "resume" ]; then \
        uv run python scripts/fix_embedding_dimensions.py --execute --resume; \
    else \
        uv run python scripts/fix_embedding_dimensions.py; \
    fi

# Check embedding dimension status
check-embeddings:
    @echo "📊 Checking entity embedding dimensions..."
    uv run python scripts/fix_embedding_dimensions.py --verify

# === Episode Embedding (Semantic Search) ===

# Backfill episode embeddings for semantic search (dry-run)
backfill-episodes-dry:
    @echo "👀 Performing episode embedding dry run..."
    uv run python scripts/backfill_episode_embeddings.py --dry-run

# Backfill episode embeddings for semantic search
backfill-episodes batch_size="50":
    @echo "🔄 Backfilling episode embeddings (batch size: {{batch_size}})..."
    uv run python scripts/backfill_episode_embeddings.py --batch-size {{batch_size}}

# Backfill limited number of episodes (for testing)
backfill-episodes-test count="100":
    @echo "🧪 Backfilling {{count}} episodes for testing..."
    uv run python scripts/backfill_episode_embeddings.py --max-episodes {{count}}

# Check episode embedding coverage statistics
check-episode-embeddings:
    @echo "📊 Checking episode embedding coverage..."
    uv run python -c "import asyncio; from src.graphrag.episode_embedding_manager import EpisodeEmbeddingManager; m = EpisodeEmbeddingManager(); stats = asyncio.run(m.get_embedding_stats()); print('Episode Embedding Stats:'); print(f'  Total episodes: {stats[\"total_episodes\"]:,}'); print(f'  With embeddings: {stats[\"episodes_with_embeddings\"]:,}'); print(f'  Without embeddings: {stats[\"episodes_without_embeddings\"]:,}'); print(f'  Coverage: {stats[\"coverage_percentage\"]:.1f}%'); asyncio.run(m.close())"

# Initialize episodic search indexes (run after database setup)
init-episode-indexes:
    @echo "📊 Creating episodic search indexes..."
    uv run python scripts/init_graphiti_v3_database.py
    @echo "✅ Indexes created. Run 'just backfill-episodes' to generate embeddings."

# === Hybrid Search Vector Indexes ===

# Check hybrid search vector index status
hybrid-search-status:
    @echo "📊 Checking hybrid search vector index status..."
    uv run python scripts/add_hybrid_search_indexes.py --status

# Create hybrid search vector indexes (dry-run)
hybrid-search-dry:
    @echo "👀 Performing hybrid search index dry run..."
    uv run python scripts/add_hybrid_search_indexes.py --dry-run

# Create hybrid search vector indexes
hybrid-search-create:
    @echo "🔧 Creating hybrid search vector indexes..."
    uv run python scripts/add_hybrid_search_indexes.py
    @echo "✅ Hybrid search indexes created. Check status with 'just hybrid-search-status'"

# Remove hybrid search vector indexes (rollback)
hybrid-search-rollback:
    @echo "🔄 Removing hybrid search vector indexes..."
    uv run python scripts/add_hybrid_search_indexes.py --rollback

# === Phase 2 Entity Deduplication Indexes ===

# Check Phase 2 index status
phase2-index-status:
    @echo "📊 Checking Phase 2 index status..."
    uv run python scripts/add_phase2_indexes.py --status

# Create Phase 2 indexes (dry-run)
phase2-index-dry:
    @echo "👀 Performing Phase 2 index dry run..."
    uv run python scripts/add_phase2_indexes.py --dry-run

# Create Phase 2 indexes for entity deduplication
phase2-index-create:
    @echo "🔧 Creating Phase 2 indexes..."
    uv run python scripts/add_phase2_indexes.py
    @echo "✅ Phase 2 indexes created. Check status with 'just phase2-index-status'"

# Remove Phase 2 indexes (rollback)
phase2-index-rollback:
    @echo "🔄 Removing Phase 2 indexes..."
    uv run python scripts/add_phase2_indexes.py --rollback

# === Multilingual Embedding Migration (ada-002) ===

# Calculate exact re-embedding cost for the graph
calculate-reembedding-cost:
    @echo "💰 Calculating re-embedding cost..."
    uv run python calculate_reembedding_cost.py

# Re-embed entities only with ada-002 (Phase 1a)
reembed-entities:
    @echo "🔄 Re-embedding entities with ada-002..."
    uv run python scripts/re_embed_with_ada002.py --entities

# Re-embed relationships only with ada-002 (Phase 1b)
reembed-relationships:
    @echo "🔄 Re-embedding relationships with ada-002..."
    uv run python scripts/re_embed_with_ada002.py --relationships

# Re-embed entities and relationships with ada-002 (Phase 1 - Recommended)
reembed-phase1:
    @echo "🔄 Re-embedding entities + relationships with ada-002 (Phase 1)..."
    uv run python scripts/re_embed_with_ada002.py --entities --relationships

# Re-embed episodic nodes with ada-002 (Phase 2)
reembed-episodic:
    @echo "🔄 Re-embedding episodic nodes with ada-002 (Phase 2)..."
    uv run python scripts/re_embed_with_ada002.py --episodic

# Dry run - preview what would be re-embedded
reembed-dry:
    @echo "👀 Performing re-embedding dry run..."
    uv run python scripts/re_embed_with_ada002.py --entities --relationships --dry-run

# Test re-embedding with limited items (for testing)
reembed-test limit="10":
    @echo "🧪 Testing re-embedding with {{limit}} items..."
    uv run python scripts/re_embed_with_ada002.py --entities --limit {{limit}}

# Re-embed everything (entities + relationships + episodic)
reembed-all:
    @echo "🔄 Re-embedding all graph items with ada-002..."
    @echo "⚠️  This includes episodic nodes (7,794 items, ~$0.98)"
    @read -p "Continue? (y/N) " -n 1 -r; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        echo ""; \
        uv run python scripts/re_embed_with_ada002.py --entities --relationships --episodic; \
    fi

# Backup embeddings to JSON before re-embedding (safety measure)
backup-embeddings:
    @echo "💾 Backing up all embeddings to JSON..."
    uv run python scripts/backup_embeddings.py

# Backup entities only
backup-embeddings-entities:
    @echo "💾 Backing up entity embeddings..."
    uv run python scripts/backup_embeddings.py --entities

# Backup relationships only
backup-embeddings-relationships:
    @echo "💾 Backing up relationship embeddings..."
    uv run python scripts/backup_embeddings.py --relationships

# Backup episodic nodes only
backup-embeddings-episodic:
    @echo "💾 Backing up episodic node embeddings..."
    uv run python scripts/backup_embeddings.py --episodic

# Check re-embedding migration status (see progress)
reembed-status:
    @echo "📊 Checking re-embedding migration status..."
    uv run python scripts/check_migration_status.py

# Check entity migration status only
reembed-status-entities:
    @echo "📊 Checking entity migration status..."
    uv run python scripts/check_migration_status.py --entities

# Check relationship migration status only
reembed-status-relationships:
    @echo "📊 Checking relationship migration status..."
    uv run python scripts/check_migration_status.py --relationships

# Check episodic migration status only
reembed-status-episodic:
    @echo "📊 Checking episodic migration status..."
    uv run python scripts/check_migration_status.py --episodic

# Detailed migration status (with timestamps)
reembed-status-detailed:
    @echo "📊 Checking detailed migration status..."
    uv run python scripts/check_migration_status.py --detailed

# Restore embeddings from backup (rollback capability)
restore-embeddings backup_file:
    @echo "⏪ Restoring embeddings from {{backup_file}}..."
    uv run python scripts/restore_embeddings.py {{backup_file}}

# Restore entities only from backup
restore-embeddings-entities backup_file:
    @echo "⏪ Restoring entity embeddings from {{backup_file}}..."
    uv run python scripts/restore_embeddings.py {{backup_file}} --entities

# Restore relationships only from backup
restore-embeddings-relationships backup_file:
    @echo "⏪ Restoring relationship embeddings from {{backup_file}}..."
    uv run python scripts/restore_embeddings.py {{backup_file}} --relationships

# Restore episodic nodes only from backup
restore-embeddings-episodic backup_file:
    @echo "⏪ Restoring episodic embeddings from {{backup_file}}..."
    uv run python scripts/restore_embeddings.py {{backup_file}} --episodic

# Test graph embeddings (analyze current multilingual performance)
test-graph-embeddings:
    @echo "🧪 Analyzing graph embeddings..."
    uv run python test_graph_embeddings.py

# Test multilingual embedding models (compare ada-002 vs others)
test-multilingual-models:
    @echo "🧪 Testing multilingual embedding models..."
    uv run python test_embedding_comparison_with_voyage.py

# Verify ada-002 migration is working correctly
verify-ada002:
    @echo "✅ Verifying ada-002 migration..."
    uv run python scripts/verify_ada002_migration.py

# Verify ada-002 migration with detailed output
verify-ada002-detailed:
    @echo "✅ Verifying ada-002 migration (detailed)..."
    uv run python scripts/verify_ada002_migration.py --detailed

# Verify ada-002 migration (larger sample)
verify-ada002-large:
    @echo "✅ Verifying ada-002 migration (sample size: 100)..."
    uv run python scripts/verify_ada002_migration.py --sample-size 100

# Quick cross-lingual test only (skip entity checks)
verify-ada002-quick:
    @echo "✅ Quick cross-lingual verification..."
    uv run python scripts/verify_ada002_migration.py --skip-entity-check

# Check which embedding model each component is using
check-embedding-model:
    @echo "🔍 Checking embedding model configuration..."
    uv run python scripts/check_embedding_model.py