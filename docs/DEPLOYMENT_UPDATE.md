# Deployment Update Summary

**Last Updated**: 2025-05-30

## Overview
The deployment system has been streamlined to provide a unified approach for managing all services including Docker containers, Ray Serve applications, and the Kodosumi admin panel.

## Key Changes

### 1. Streamlined Justfile
The justfile has been dramatically simplified from ~490 lines to ~200 lines with focused commands:

**Core Commands:**
- `just setup` - Initial environment setup
- `just start` - Start all services (Docker + Ray + Kodosumi + Apps)
- `just stop` - Stop everything cleanly
- `just status` - Check service status with all URLs
- `just restart` - Full restart cycle

**Deployment Commands:**
- `just deploy-all` - Deploy all Ray Serve applications
- `just deploy-data` - Deploy only data ingestion
- `just deploy-chat` - Deploy only chat server
- `just redeploy` - Quick redeploy for development

**Utility Commands:**
- `just test-chat` - Test the chat API
- `just test-ingestion` - Test data ingestion
- `just build-communities` - Run Graphiti community detection
- `just neo4j-clear` - Clear the graph database
- `just logs [service]` - View Docker service logs

### 2. Unified Configuration
The `config.yaml.template` now includes both applications with minimal configuration:
- **flow1-data-ingestion** at `/data-ingestion`
- **chat-server** at `/chat` (OpenAI-compatible API)

Only essential environment variables are included - removed dozens of unused settings.

### 3. Fixed Open WebUI Integration
- **CRITICAL**: `OPENAI_API_BASE_URL` must include `/v1` suffix
- Chat server runs at `/chat` route prefix (not root `/`)
- Proper model detection via `/v1/models` endpoint
- See `/docs/OPEN_WEBUI_SETUP.md` for troubleshooting

### 4. Kodosumi Admin Panel Integration
- Automatically starts with `just start`
- Accessible at http://localhost:3370 (admin/admin)
- Registers Ray Serve endpoints automatically
- Logs saved to `logs/kodosumi.log`

## Complete Service List

After running `just start`, all these services are available:

### Web Interfaces
- 🎛️ **Kodosumi Admin**: http://localhost:3370 (admin/admin)
- 📊 **Ray Dashboard**: http://localhost:8265
- 💬 **Open WebUI**: http://localhost:3000
- 🗄️ **Neo4j Browser**: http://localhost:7474 (neo4j/password123)
- 🔍 **Langfuse**: http://localhost:3001
- ✈️ **Airflow**: http://localhost:8080 (admin/admin)
- ☁️ **Azurite**: http://localhost:10000 (blob storage)
- 🤖 **Graphiti MCP**: http://localhost:8000 (SSE endpoint)

### API Endpoints
- 🗨️ **Chat API**: http://localhost:8001/chat/v1/chat/completions
- 📝 **Data Ingestion**: http://localhost:8001/data-ingestion
- 🔄 **ETL Health**: http://localhost:8080/health

## Usage Examples

### First Time Setup
```bash
# Clone and setup
git clone <repository>
cd policiytracker
just setup

# Start everything
just start
```

### Development Workflow
```bash
# Make code changes
just redeploy

# Test the chat API
just test-chat

# Check logs
just ray-logs
just logs langfuse
```

### Service Management
```bash
# Check what's running
just status

# Stop everything
just stop

# Full restart
just restart
```

## Key Improvements
1. **Single Command Startup**: `just start` launches everything
2. **Clean Configuration**: Only necessary env vars in config.yaml
3. **Proper Service Discovery**: All URLs displayed in status
4. **Error Prevention**: Documented Open WebUI setup requirements
5. **Better Logging**: Kodosumi logs to file, not cluttering terminal

## Troubleshooting

### Open WebUI Can't Find Model
- Check `/docs/OPEN_WEBUI_SETUP.md`
- Ensure `OPENAI_API_BASE_URL` includes `/v1`
- Verify chat server is at `/chat` not `/`

### Kodosumi Not Starting
- Check logs: `tail -f logs/kodosumi.log`
- Ensure Ray is running: `ray status`
- Verify port 3370 is free

### Services Not Starting
- Check Docker: `docker compose ps`
- View logs: `just logs [service-name]`
- Ensure ports are free: 3370, 8265, 3000, 7474, 3001, 8080, 10000, 8000

## Next Steps
1. Configure client context in `/data/context/client.yaml`
2. Set up Langfuse for observability
3. Configure ETL pipelines in Airflow
4. Import sample data: `just import-data`