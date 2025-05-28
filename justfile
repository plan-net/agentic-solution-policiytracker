# Political Monitoring Agent - Task Runner

# Default recipe to display available commands
default:
    @just --list

# === Development Setup ===

# Install dependencies and setup development environment
setup:
    @echo "🚀 Setting up development environment..."
    uv sync
    @if [ ! -f .env ]; then cp .env.template .env; echo "📝 Created .env from template"; fi
    @if [ ! -f config.yaml ]; then just sync-config; fi
    @mkdir -p data/input
    @mkdir -p data/output
    @echo "✅ Setup complete. Next: 'just setup-context' then 'just first-run'"

# Setup client context (first-time setup helper)
setup-context:
    @echo "📝 Setting up client context..."
    @echo "Edit data/context/client.yaml with your organization's information:"
    @echo ""
    @echo "Required sections to customize:"
    @echo "  - company_terms: Your company names/brands"  
    @echo "  - core_industries: Your business sectors"
    @echo "  - primary_markets: Your main geographic markets"
    @echo "  - strategic_themes: Your business priorities"
    @echo ""
    @echo "💡 The example context is already configured for an e-commerce company"
    @echo "   You can test with it as-is, or customize for your organization"

# === Configuration Management ===

# Create or update config.yaml from template and .env variables
sync-config:
    @echo "🔧 Syncing configuration..."
    uv run python scripts/sync_env_to_config.py

# Validate config.yaml for placeholder values
validate-config:
    @echo "🔍 Validating configuration..."
    @if [ ! -f config.yaml ]; then echo "❌ config.yaml not found. Run 'just sync-config' first"; exit 1; fi
    @echo "✅ config.yaml exists"
    @if grep -q "your-.*-key-here" config.yaml; then echo "⚠️  Found placeholder API keys in config.yaml"; echo "💡 Update your .env file with real API keys"; else echo "✅ No placeholder values detected"; fi

# Reset config.yaml from template (for troubleshooting)
reset-config:
    @echo "🔄 Resetting config.yaml from template..."
    @if [ -f config.yaml ]; then cp config.yaml config.yaml.backup; echo "📦 Backed up existing config.yaml"; fi
    just sync-config
    @echo "✅ config.yaml reset complete"
    @echo ""
    @echo "Next step: 'just first-run' to complete setup"

# Complete first-time setup and run initial analysis
first-run:
    @echo "🎯 First-time setup and test run..."
    @echo ""
    @echo "Step 1: Starting services..."
    @just services-up
    @echo ""
    @echo "Step 2: Setting up Langfuse..."
    @just setup-langfuse
    @echo ""
    @echo "⏸️  Please complete Langfuse setup, then run 'just complete-setup'"

# Complete the setup after Langfuse configuration
complete-setup:
    @echo "🎯 Completing first-time setup..."
    @echo ""
    @echo "Step 1: Uploading prompts to Langfuse..."
    @just upload-prompts
    @echo ""
    @echo "Step 2: Importing sample data to Azurite..."
    @just azure-import
    @echo ""
    @echo "Step 3: Starting development environment..."
    @just dev
    @echo ""
    @echo "🎉 Setup complete! Ready for first analysis:"
    @echo "   📊 Admin Panel: http://localhost:3370 (admin/admin)"
    @echo "   🎯 Test with sample data in: data/input/examples/"
    @echo ""
    @echo "💡 Next: Visit the admin panel and run an analysis on the sample documents"

# === Services ===

# Start development services (Azurite, PostgreSQL, Langfuse)
services-up:
    @echo "🐳 Starting services..."
    docker compose up -d
    @echo "✅ Services started"
    @just services-status

# Stop all services
services-down:
    docker compose down

# Show service status
services-status:
    @echo "📊 Services:"
    @docker compose ps
    @echo ""
    @echo "🌐 URLs:"
    @echo "  Azurite:     http://localhost:10000"
    @echo "  PostgreSQL:  localhost:5432" 
    @echo "  Langfuse:    http://localhost:3001"
    @echo "  Neo4j:       http://localhost:7474"
    @echo "  Airflow:     http://localhost:8080"

# View service logs
logs service="":
    @if [ "{{service}}" = "" ]; then \
        docker compose logs -f; \
    else \
        docker compose logs -f {{service}}; \
    fi

# === Kodosumi Deployment ===

# Start Ray and deploy Flow 1 to Kodosumi
kodosumi-deploy:
    @echo "🚀 Starting Ray cluster..."
    uv run --active ray start --head
    @echo "📝 Syncing environment variables to config.yaml..."
    uv run python scripts/sync_env_to_config.py
    @echo "📦 Deploying Flow 1 (Data Ingestion) to Ray Serve..."
    uv run --active serve deploy config.yaml
    @echo "🎯 Starting Kodosumi server..."
    uv run --active koco start --register http://localhost:8001/-/routes
    @echo "✅ Flow 1 deployment complete!"
    @echo "🌐 Admin Panel: http://localhost:3370 (admin/admin)"
    @echo "📊 Ray Dashboard: http://localhost:8265"
    @echo "📄 Data Ingestion: http://localhost:8001/data-ingestion"

# Stop Kodosumi and Ray
kodosumi-stop:
    @echo "🛑 Stopping Kodosumi services..."
    -pkill -f "koco start"
    -uv run --active serve shutdown --yes
    -uv run --active ray stop
    @echo "✅ All services stopped"

# Check Kodosumi deployment status
kodosumi-status:
    @echo "📊 Kodosumi Status:"
    @uv run --active ray status || echo "❌ Ray not running"
    @echo ""
    @echo "🌐 Service URLs:"
    @echo "  Kodosumi Admin: http://localhost:3370"
    @echo "  Ray Dashboard:  http://localhost:8265"
    @echo "  Flow 1 Endpoint: http://localhost:8001/data-ingestion"

# View Kodosumi logs
kodosumi-logs:
    @echo "📋 Recent Ray logs:"
    uv run --active ray logs --follow

# Restart entire Kodosumi stack
kodosumi-restart: kodosumi-stop kodosumi-deploy

# Quick Kodosumi development cycle (restart only app)
dev-quick:
    @echo "🔄 Quick Flow 1 restart..."
    @echo "📝 Syncing environment variables to config.yaml..."
    uv run python scripts/sync_env_to_config.py
    -uv run --active serve shutdown --yes 2>/dev/null || true
    uv run --active serve deploy config.yaml
    @echo "✅ Flow 1 redeployed to Kodosumi"

# Main development command (alias for kodosumi-deploy)
dev: kodosumi-deploy

# Deploy specific flows (for future use)
dev-flow1: dev-quick

# === Development ===

# First-time setup helper
setup-langfuse:
    @echo "🔧 Setting up Langfuse for first time use..."
    @echo ""
    @echo "1. Starting services (if not already running)..."
    @just services-up
    @echo ""
    @echo "2. 🌐 Open Langfuse: http://localhost:3001"
    @echo ""
    @echo "3. 📝 Complete Langfuse Setup:"
    @echo "   • Sign up with new account"
    @echo "   • Create organization (e.g., 'Political Monitoring')"
    @echo "   • Create project (e.g., 'political-monitoring-agent')"
    @echo ""
    @echo "4. 🔑 Get your API keys:"
    @echo "   • Go to Settings → API Keys (within your project)"
    @echo "   • Click 'Create new API key'"
    @echo "   • Copy both Public Key (pk-lf-...) and Secret Key (sk-lf-...)"
    @echo ""
    @echo "5. ✏️  Update your .env file with the real keys"
    @echo "6. 🔄 Run: just kodosumi-restart"
    @echo ""
    @echo "💡 This setup is only needed once!"

# Upload local prompts to Langfuse for centralized management
upload-prompts:
    @echo "📤 Uploading prompts to Langfuse..."
    uv run python scripts/upload_prompts_to_langfuse.py

# Reset Langfuse data (useful if login issues occur)
reset-langfuse:
    @echo "🔄 Resetting Langfuse data..."
    @echo "⚠️  This will delete all Langfuse data and reset to fresh state"
    @read -p "Continue? (y/N) " -n 1 -r; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        echo ""; \
        docker compose stop langfuse-server; \
        docker volume rm policiytracker_langfuse_data policiytracker_postgres_data 2>/dev/null || true; \
        echo "✅ Langfuse data reset. Run 'just services-up' to restart with fresh installation"; \
    else \
        echo ""; \
        echo "❌ Reset cancelled"; \
    fi

# Start full development environment (Kodosumi-first) - alias for backwards compatibility
dev-full: services-up kodosumi-deploy


# Watch for changes and auto-redeploy (development workflow)
dev-watch:
    @echo "👀 Starting development with file watching..."
    @echo "📝 Edit app.py or political_analyzer.py and run 'just dev-quick' to redeploy"
    @echo "🌐 Kodosumi Admin: http://localhost:3370 (admin/admin)"
    @echo "📊 Ray Dashboard: http://localhost:8265"
    @echo "🎯 Your App: http://localhost:8001/political-analysis"
    @echo ""
    @echo "💡 Development Tips:"
    @echo "  - Run 'just dev-quick' after code changes"
    @echo "  - Run 'just kodosumi-logs' to view logs"
    @echo "  - Run 'just kodosumi-status' to check health"



# === Testing ===

# Run all tests
test:
    uv run pytest -v

# Run tests with coverage
test-coverage:
    uv run pytest --cov=src --cov-report=html --cov-report=term

# Run unit tests only
test-unit:
    uv run pytest tests/unit/ -v

# Run integration tests only  
test-integration:
    uv run pytest tests/integration/ -v

# Run Azure-specific tests
test-azure:
    uv run pytest -k "azure" -v

# === Code Quality ===

# Format and lint code
format:
    uv run ruff format src tests
    uv run ruff check src tests --fix

# Type check code
typecheck:
    uv run mypy src

# Run all quality checks
check: format typecheck
    @echo "✅ All checks passed"

# === Azure Storage ===

# Import local data to Azurite for development
azure-import:
    uv run python scripts/import_data_to_azurite.py

# Import with custom job ID
azure-import-job job_id:
    uv run python scripts/import_data_to_azurite.py --job-id {{job_id}}

# Dry run import (show what would be imported)
azure-import-dry:
    uv run python scripts/import_data_to_azurite.py --dry-run

# Verify Azurite connection
azure-verify:
    uv run python scripts/import_data_to_azurite.py --verify-only

# === Airflow ETL ===

# Start Airflow services (including webserver and scheduler)
airflow-up:
    @echo "🚁 Starting Airflow services..."
    docker compose up -d airflow-postgres airflow-init airflow-webserver airflow-scheduler
    @echo "✅ Airflow started"
    @echo "🌐 Airflow UI: http://localhost:8080 (admin/admin)"
    @echo "📊 Available DAGs: news_collection, flow_orchestration"

# Stop Airflow services
airflow-down:
    docker compose stop airflow-webserver airflow-scheduler airflow-postgres

# View Airflow logs
airflow-logs service="webserver":
    docker compose logs -f airflow-{{service}}

# Trigger news collection DAG manually
airflow-trigger-news:
    @echo "📰 Triggering news collection DAG..."
    docker compose exec airflow-webserver airflow dags trigger news_collection

# Trigger flow orchestration DAG manually
airflow-trigger-flows:
    @echo "🔄 Triggering flow orchestration DAG..."
    docker compose exec airflow-webserver airflow dags trigger flow_orchestration

# Check ETL initialization status
etl-status:
    @echo "🔍 ETL Initialization Status:"
    uv run python scripts/etl_init_manager.py status

# Reset ETL initialization for specific collector
etl-reset collector:
    @echo "🔄 Resetting ETL initialization for {{collector}}..."
    uv run python scripts/etl_init_manager.py reset {{collector}}

# Reset ETL initialization for all collectors
etl-reset-all:
    @echo "🔄 Resetting ETL initialization for all collectors..."
    uv run python scripts/etl_init_manager.py reset-all

# === Policy Collection (Flow 1) ===

# Test policy collection system
policy-test:
    @echo "🧪 Testing policy collection system..."
    uv run python scripts/test_policy_simple.py

# Test policy collection with full features (requires EXA_API_KEY)
policy-test-full:
    @echo "🧪 Testing complete policy collection system..."
    uv run python scripts/test_policy_collection.py

# Generate sample policy queries (no API calls)
policy-queries:
    @echo "🔍 Generating policy search queries from client context..."
    uv run python src/etl/utils/policy_query_generator.py

# Reset Airflow database (for development)
airflow-reset:
    @echo "⚠️  This will reset Airflow database!"
    @read -p "Continue? (y/N) " -n 1 -r; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        docker compose stop airflow-webserver airflow-scheduler; \
        docker volume rm policiytracker_airflow_postgres_data 2>/dev/null || true; \
        docker compose up -d airflow-postgres airflow-init; \
        echo "✅ Airflow database reset"; \
    fi

# === Database ===

# Connect to PostgreSQL
db-connect:
    docker compose exec postgres psql -U postgres -d policiytracker

# Connect to Airflow PostgreSQL
airflow-db-connect:
    docker compose exec airflow-postgres psql -U airflow -d airflow

# Reset database
db-reset:
    @echo "⚠️  This will delete all data!"
    @read -p "Continue? (y/N) " -n 1 -r; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS policiytracker; CREATE DATABASE policiytracker;"; \
        echo "✅ Database reset"; \
    fi

# === Cleanup ===

# Clean temporary files
clean:
    @echo "🧹 Cleaning up..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    rm -rf htmlcov .coverage 2>/dev/null || true
    @echo "✅ Cleaned"

# Full cleanup (code + docker)
clean-all: clean services-down
    docker system prune -f
    @echo "✅ Full cleanup complete"

# === Health Check ===

# Check system health
health:
    @echo "🏥 System Health:"
    @echo "=================="
    @just services-status
    @echo ""
    @echo "Environment:"
    @uv run python -c "from src.config import settings; print('✅ Config valid')" 2>/dev/null || echo "❌ Config invalid"
    @echo ""
    @echo "Dependencies:"
    @uv --version | head -1
    @docker --version | head -1