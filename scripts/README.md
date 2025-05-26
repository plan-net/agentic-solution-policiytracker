# Scripts Directory

This directory contains utility scripts for development, testing, and deployment of the Political Monitoring Agent.

## Available Scripts

### 🧪 **Testing & Development**

#### `test_simple_kg_pipeline.py`
Test the Neo4j GraphRAG SimpleKGPipeline with political documents.

```bash
# Test GraphRAG with example documents
uv run python scripts/test_simple_kg_pipeline.py
```

**Prerequisites:**
- Neo4j running (`docker-compose up neo4j`)
- OPENAI_API_KEY in .env
- ANTHROPIC_API_KEY in .env (for future Claude integration)

**What it does:**
- Processes political documents using SimpleKGPipeline
- Extracts entities, relationships, and topics
- Creates knowledge graph in Neo4j
- Tests semantic search functionality

### ☁️ **Azure Storage**

#### `import_data_to_azurite.py`
Import local data to Azurite (Azure Storage Emulator) for development.

```bash
# Import all data
uv run python scripts/import_data_to_azurite.py

# Import only input documents
uv run python scripts/import_data_to_azurite.py --input-only

# Import with custom job ID
uv run python scripts/import_data_to_azurite.py --job-id custom_job_123
```

**Prerequisites:**
- Azurite running (`docker-compose up azurite`)

### 🚀 **Deployment**

#### `sync_env_to_config.py`
Sync environment variables from .env to config.yaml for Kodosumi deployment.

```bash
# Sync config for deployment
uv run python scripts/sync_env_to_config.py
```

**What it does:**
- Creates config.yaml from template if needed
- Syncs .env variables to config.yaml
- Ensures Ray workers have access to environment variables

### 📊 **Observability**

#### `upload_prompts_to_langfuse.py`
Upload local prompt files to Langfuse for centralized management.

```bash
# Upload prompts to Langfuse
uv run python scripts/upload_prompts_to_langfuse.py
```

**Prerequisites:**
- Langfuse running (`docker-compose up langfuse`)
- Langfuse API keys in .env

## Quick Reference

```bash
# Start all services
docker-compose up -d

# Test GraphRAG
uv run python scripts/test_simple_kg_pipeline.py

# View knowledge graph
open http://localhost:7474  # Neo4j Browser

# View Langfuse traces
open http://localhost:3001  # Langfuse UI
```