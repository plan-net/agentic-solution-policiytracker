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
    nohup uv run koco start --register http://localhost:8001/-/routes > logs/kodosumi.log 2>&1 &
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
    @echo "  🔍 Langfuse:       http://localhost:3001"
    @echo "  ✈️  Airflow:        http://localhost:8080 (admin/admin)"
    @echo "  ☁️  Azurite:        http://localhost:10000 (blob storage)"
    @echo "  🤖 Graphiti MCP:   http://localhost:8000 (SSE endpoint)"
    @echo ""
    @echo "  📡 API Endpoints:"
    @echo "  🗨️  Chat API:       http://localhost:8001/v1/chat/completions"
    @echo "  📝 Data Ingestion: http://localhost:8001/data-ingestion"
    @echo "  🔄 ETL Health:     http://localhost:8080/health"


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

# Deploy only chat server
deploy-chat:
    @echo "📦 Deploying chat server..."
    just sync-config
    uv run --active serve deploy config.yaml --app chat-server
    @echo "✅ Chat server deployed"

# Quick redeploy (for development)
redeploy: sync-config
    @echo "🔄 Quick redeployment..."
    -uv run --active serve shutdown --yes 2>/dev/null || true
    uv run --active serve deploy config.yaml
    @echo "✅ Applications redeployed"

# === Docker Services ===

# Start Docker services only
services-up:
    @echo "🐳 Starting Docker services..."
    docker compose up -d
    @echo "✅ Docker services started"

# Stop Docker services
services-down:
    docker compose down

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

# Reset specific ETL collector
etl-reset collector:
    @echo "🔄 Resetting ETL collector: {{collector}}"
    uv run python scripts/etl_init_manager.py reset {{collector}}

# Reset all ETL collectors
etl-reset-all:
    @echo "🔄 Resetting ALL ETL collectors..."
    uv run python scripts/etl_init_manager.py reset-all

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