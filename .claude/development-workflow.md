# Development Workflow & Commands

## Quick Development Cycle
1. Make changes to code
2. Run: `just deploy-all` (redeploy services)
3. Test flows: http://localhost:3370 (Kodosumi admin)
4. Test chat: http://localhost:3000 (Open WebUI)
5. Check logs: `just ray-logs`

## Before Committing
ALWAYS run these commands:
```bash
just format        # Format with ruff
just typecheck     # Check types with mypy
```

## Common Workflows

### First Time Setup
```bash
just setup
just first-run
# Complete Langfuse setup
just complete-setup
```

### Daily Development
```bash
just start         # Full stack startup
just deploy-all    # Redeploy Ray services after changes
just status        # Check all service status
just ray-logs      # View Ray application logs
```

### Testing Changes
```bash
just test          # Run all tests
just test-unit     # Unit tests only
just test-etl      # Test ETL pipeline
just etl-status    # Check ETL health
```

## Debugging Tips
- **Ray Dashboard**: http://localhost:8265 - Service status, resource usage
- **Chat Interface**: http://localhost:3000 - Test multi-agent conversations
- **Kodosumi Admin**: http://localhost:3370 - Flow management (admin/admin)
- **Neo4j Browser**: http://localhost:7474 - Knowledge graph exploration
- **Langfuse**: http://localhost:3001 - LLM operation tracing
- **Airflow**: http://localhost:8080 - ETL pipeline monitoring (admin/admin)
- **Container logs**: `docker logs <container-name>`

## Important Reminders
- Config changes need `just sync-config`
- New dependencies: Update pyproject.toml AND config.yaml.template
- Langfuse issues: `just reset-langfuse` for fresh start