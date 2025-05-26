# Development Workflow & Commands

## Quick Development Cycle
1. Make changes to code
2. Run: `just dev-quick` (faster than full restart)
3. Test at http://localhost:3370
4. Check logs: `just kodosumi-logs`

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
just dev           # Full stack startup
just dev-quick     # Quick redeploy after changes
just kodosumi-logs # View logs
```

### Testing Changes
```bash
just test          # Run all tests
just test-unit     # Just unit tests
just azure-import  # Import test data
```

## Debugging Tips
- Check Ray dashboard: http://localhost:8265
- View Langfuse traces: http://localhost:3001
- Container logs: `just logs azurite`
- Python debugging: Set `DEBUG=true` in .env

## Important Reminders
- Config changes need `just sync-config`
- New dependencies: Update pyproject.toml AND config.yaml.template
- Langfuse issues: `just reset-langfuse` for fresh start