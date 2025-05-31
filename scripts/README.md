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
# Import sample data to Azurite
just import-data
```

### **ETL Pipeline Management**
#### `etl_init_manager.py`
Manage ETL initialization tracking for historical data collection.

```bash
# Check ETL initialization status (shows collector states and configuration)
just etl-status

# Reset specific collector (available: exa_direct, apify_news, policy_landscape)
just etl-reset exa_direct

# Reset all collectors (forces re-initialization)
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
# Test policy collection pipeline (requires EXA_API_KEY)
just test-etl
```


## Quick Reference

```bash
# Start all services
just services-up

# Deploy with config sync
just dev

# ETL management
just etl-status              # Check initialization status
just etl-reset exa_direct    # Reset specific collector
just etl-reset-all          # Reset all collectors
just test-etl               # Test policy collection

# Knowledge graph operations
just build-communities      # Build document communities

# Data operations
just import-data           # Import sample data to Azurite
just upload-prompts        # Upload prompts to Langfuse
```

## Prerequisites

- **Services Running**: `just services-up`
- **Environment**: Valid API keys in `.env`
- **Dependencies**: `uv sync` for Python packages