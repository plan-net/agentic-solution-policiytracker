# Political Monitoring Agent v0.1.0

AI-powered document analysis system for political and regulatory monitoring.

## Project Context
- **Purpose**: Analyze political documents for relevance, priority, and topic clustering
- **Stack**: Kodosumi v0.9.2 + Ray + LangGraph + Azure Storage + Langfuse
- **Python**: 3.12.6 (strict requirement)
- **v0.2.0**: Migrating to Graphiti temporal knowledge graph via MCP

## Key Instructions
1. Read specifications in `/docs/specs/` before making changes
2. Follow two-file Kodosumi pattern: `src/app.py` + `src/political_analyzer.py`
3. Check existing code patterns before creating new files
4. Run `just format && just typecheck` before committing
5. Version is 0.1.0 - ensure consistency across all files

## Architecture & Patterns
@.claude/kodosumi-patterns.md
@.claude/azure-integration.md
@.claude/langfuse-prompts.md
@.claude/testing-standards.md
@.claude/development-workflow.md
@.claude/git-workflow.md
@.claude/graphrag-patterns.md
@.claude/mcp-patterns.md
@.claude/graphiti-patterns.md

## Project-Specific Details
@.claude/project-architecture.md

## Quick Reference
- **Admin Panel**: http://localhost:3370 (admin/admin)
- **Main Commands**: `just dev`, `just dev-quick`, `just test`
- **Logs**: `just kodosumi-logs`
- **Custom Commands**: `/deploy`, `/status`, `/test [scope]`

## MCP Server Configuration (v0.2.0)

### Available MCP Servers
1. **Graphiti MCP** (port 8000, SSE transport) - Temporal knowledge graph operations
2. **Neo4j Memory MCP** (Docker command) - Entity tracking with observations

### Setting Up Claude Code MCP Access
1. Ensure MCP servers are running: `docker ps | grep mcp`
2. Copy `.mcp.json.template` to `.mcp.json` and add your OpenAI API key
3. Claude can directly interact with both servers when they're running

### Using MCP in Claude Code
```python
# Example: Query temporal data via Graphiti
await graphiti_mcp.search(query="EU AI Act", time_range="last_week")

# Example: Track entity observations via Neo4j Memory
await neo4j_mcp.create_entity(name="EU AI Act", type="Policy")
await neo4j_mcp.add_observation(entity="EU AI Act", observation="Status changed to enacted")
```

### Troubleshooting MCP
- Check server logs: `docker logs policiytracker-graphiti-mcp`
- Verify connection: Test MCP endpoints are accessible
- Debug mode: Set `"debug": true` in .mcp.json