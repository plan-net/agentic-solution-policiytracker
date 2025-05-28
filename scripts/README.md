# Scripts Directory

This directory contains utility scripts for the Political Monitoring Agent production workflows and testing.

## 🛠️ **Core Utility Scripts**

These scripts are integrated into the main workflow via `justfile` commands and provide essential functionality:

### **Community Building**
#### `build_communities.py`
Build document communities from existing knowledge graph using Graphiti.

```bash
# Manual community detection
just build-communities
```

### **Environment & Configuration**
#### `sync_env_to_config.py`
Sync environment variables from .env to config.yaml for Kodosumi deployment.

```bash
# Sync config for deployment (auto-run by just dev)
just sync-config
```

### **Azure Storage Management**
#### `import_data_to_azurite.py`
Import local data to Azurite (Azure Storage Emulator) for development.

```bash
# Import all data
just azure-import

# Import with custom job ID
just azure-import-job my_job_123

# Dry run (preview)
just azure-import-dry

# Verify connection
just azure-verify
```

### **ETL Pipeline Management**
#### `etl_init_manager.py`
Manage ETL initialization tracking for historical data collection.

```bash
# Check ETL status
just etl-status

# Reset specific collector
just etl-reset exa_direct

# Reset all collectors
just etl-reset-all
```

### **Prompt Management**
#### `upload_prompts_to_langfuse.py`
Upload local prompt files to Langfuse for centralized management.

```bash
# Upload prompts to Langfuse
just upload-prompts
```

### **Policy Collection Testing**
#### `test_policy_collection.py`
Test complete policy collection system with full features.

```bash
# Test policy collection (requires EXA_API_KEY)
just policy-test

# Test basic policy components (no API needed)
just policy-test-simple
```

## 🧪 **Development Testing Scripts**

Located in `_dev_testing/` - these are ad-hoc scripts created during development for testing specific features:

- **ETL Testing**: `etl_test_summary.py`, `test_etl_*` files
- **News Collection**: `compare_news_collectors.py`, `test_exa_*` files  
- **Document Processing**: `full_document_processing.py`, `process_*` files
- **GraphRAG**: `test_graphrag_langfuse.py`, `explore_graphiti_mcp_search.py`
- **Validation**: `validate_*`, `verify_*`, `inspect_*` files

These scripts are preserved for reference but not part of the main workflow.

## Quick Reference

```bash
# Start all services
just services-up

# Deploy Flow1 with config sync
just dev

# Build communities manually
just build-communities

# Test policy collection
just policy-test

# Import sample data
just azure-import

# Upload prompts
just upload-prompts
```

## Prerequisites

- **Services Running**: `just services-up`
- **Environment**: Valid API keys in `.env`
- **Dependencies**: `uv sync` for Python packages