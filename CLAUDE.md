# Political Monitoring Agent v0.2.0

AI-powered political monitoring with chat interface, knowledge graphs, and automated data collection.

## Project Context
- **Purpose**: Conversational political intelligence via chat interface + automated data collection
- **Stack**: Chat Interface + ETL Pipelines + Graphiti Knowledge Graph + Ray Deployment
- **Python**: 3.12.6 (strict requirement)
- **Architecture**: v0.2.0 - Multi-agent chat + temporal knowledge graphs + automated ETL

## Key Instructions v0.2.0
0. NEVER forget to work with uv and the correct venv
1. **NO legacy v0.1.0 patterns**: src/app.py + src/political_analyzer.py REMOVED
2. Use v0.2.0 structure: chat interface + flows + ETL + GraphRAG
3. Check pattern files in `.claude/` before making changes
4. Run `just format && just typecheck` before committing
5. Version is 0.2.0 - ensure consistency across all files

## Architecture & Core Patterns
@.claude/project-architecture.md
@.claude/chat-patterns.md
@.claude/kodosumi-patterns.md
@.claude/etl-patterns.md
@.claude/ray-deployment-patterns.md

## Advanced Patterns
@.claude/langgraph-patterns.md
@.claude/graphiti-patterns.md
@.claude/tool-integration-patterns.md
@.claude/mcp-patterns.md

## Development & Quality
@.claude/development-workflow.md
@.claude/git-workflow.md
@.claude/test-patterns.md
@.claude/testing-standards.md

## Infrastructure
@.claude/azure-integration.md
@.claude/langfuse-prompts.md

## Commands
@.claude/commands/status.md
@.claude/commands/deploy.md
@.claude/commands/test.md

## Quick Reference v0.2.0
- **Chat Interface**: http://localhost:3000 (Open WebUI)
- **Kodosumi Admin**: http://localhost:3370 (admin/admin)
- **Ray Dashboard**: http://localhost:8265
- **ETL Dashboard**: http://localhost:8080 (admin/admin)
- **Main Commands**: `just start`, `just deploy-all`, `just status`, `just test`
- **Custom Commands**: `/deploy`, `/status`, `/test [scope]`

## v0.2.0 Architecture Summary

### Core Components
```
Chat Interface (src/chat/)     - Multi-agent conversational analysis
├── 4 Agents: understand → plan → execute → synthesize
└── 15 Tools: entity, network, temporal, search

ETL Pipeline (src/etl/)        - Automated data collection
├── Airflow DAGs: policy (weekly) + news (daily)
└── Collectors: Exa.ai + Apify with smart deduplication

Kodosumi Flows (src/flows/)    - Document processing workflows
├── Data Ingestion: Batch document processing
└── Ray Integration: Distributed processing with progress tracking

GraphRAG (src/graphrag/)       - Knowledge graph construction  
├── Graphiti API: Temporal entity extraction
└── Political Schema: Policy, Politician, Organization entities
```

### Service Architecture
```
Open WebUI (3000) → Chat API (8001) → Multi-Agent System → Neo4j (7687)
Kodosumi (3370) → Data Ingestion Flow (8001) → Graphiti → Neo4j
Airflow (8080) → ETL Collectors → Document Storage → Processing Pipeline
```

## MCP Server Configuration

### Available MCP Servers
1. **Graphiti MCP** (port 8000, SSE transport) - Temporal knowledge graph operations
2. **Neo4j Memory MCP** (Docker container) - Entity tracking with observations

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

## v0.2.0 Development Flow

### Daily Development
```bash
just start                    # Start all services
# Make changes to chat interface, flows, or ETL
just deploy-all              # Redeploy Ray services
just status                  # Check health
```

### Testing
```bash
just test                    # All tests
just test-etl               # ETL pipeline tests
just test-chat              # Chat interface tests
```

### Key URLs
- **Chat Interface**: http://localhost:3000 - Natural language political queries
- **Document Processing**: http://localhost:3370 - Batch document upload and processing
- **Knowledge Graph**: http://localhost:7474 - Browse extracted entities and relationships
- **ETL Dashboard**: http://localhost:8080 - Monitor automated data collection