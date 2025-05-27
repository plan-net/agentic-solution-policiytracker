# Phase 1: Graphiti Foundation - TODO List

## Goal
Set up Neo4j + Graphiti infrastructure and test temporal queries with sample political documents.

## Prerequisites Check
- [ ] Python 3.12.6 environment active
- [ ] Docker and Docker Compose installed
- [ ] Current services running (`just services-up`)

## 1. Infrastructure Setup

### 1.1 Neo4j Setup
- [x] Neo4j service already in `docker-compose.yml` ✓
  - [x] Neo4j 5.20 Enterprise configured
  - [x] Ports: 7474 (browser), 7687 (bolt)
  - [x] Password: neo4j/password123
  - [x] APOC and GDS plugins enabled
  - [x] Database: politicalmonitoring
- [x] Verify Neo4j is running: `just services-status` ✓
- [x] Access Neo4j browser: http://localhost:7474 ✓

### 1.6 Start MCP Services
- [x] Rebuild Docker services: `docker compose build` ✓
- [x] Start updated services: `just services-up` ✓
- [x] Verify Graphiti MCP is running: `docker ps | grep graphiti` ✓
- [x] Check Graphiti logs: `docker logs policiytracker-graphiti-mcp` ✓
- [x] Graphiti running on SSE transport (port 8000) ✓

### 1.2 MCP Servers Setup
- [x] Add Graphiti MCP server to `docker-compose.yml` ✓
  - [x] Build from Graphiti GitHub repo ✓
  - [x] Configure environment variables ✓
  - [x] Link to Neo4j container ✓
- [x] Add Neo4j MCP-Memory server to `docker-compose.yml` ✓
  - [x] Use official Neo4j MCP image ✓
  - [x] Configure for political entity tracking ✓
  - [x] Link to same Neo4j instance ✓
- [x] Add langchain-mcp-adapters to dependencies ✓
  - [x] Removed direct graphiti-core dependency ✓
  - [x] Added `langchain-mcp-adapters>=0.1.1` ✓
- [x] Update dependencies with `uv pip install -e .` ✓
  - [x] Updated langchain packages to 0.3.x ✓
  - [x] Updated langgraph to 0.4.7 ✓
  - [x] Installed langchain-mcp-adapters ✓

### 1.3 Environment Configuration
- [x] Neo4j credentials already in `.env` ✓
  - [x] `NEO4J_URI=bolt://localhost:7687` ✓
  - [x] `NEO4J_USERNAME=neo4j` ✓
  - [x] `NEO4J_PASSWORD=password123` ✓
  - [x] `NEO4J_DATABASE=politicalmonitoring` ✓
  - [x] `ENABLE_GRAPHRAG=true` ✓
- [x] `src/config.py` already has Neo4j settings ✓
- [x] Run `just sync-config` to update `config.yaml` ✓

### 1.4 Claude Code MCP Configuration
- [x] Create `mcp.json` for Claude Code ✓
  - [x] Configure Graphiti MCP server ✓
  - [x] Configure Neo4j MCP-Memory server ✓
  - [x] Set up proper authentication ✓
- [x] Update `CLAUDE.md` with MCP setup instructions ✓
- [x] Create `.claude/mcp-patterns.md` documentation ✓
- [ ] Test Claude Code can connect to both servers (after Docker setup)

### 1.5 MCP Server Configuration
- [x] Add MCP server settings to `.env` ✓
  - [x] `GRAPHITI_MCP_HOST=localhost` ✓
  - [x] `GRAPHITI_MCP_PORT=8000` (SSE transport) ✓
  - [x] Neo4j Memory MCP runs via Docker command (no port) ✓
  - [x] API keys use existing OPENAI_API_KEY and ANTHROPIC_API_KEY ✓
- [x] Configure Graphiti MCP Docker service ✓
  - [x] Mount Neo4j connection config ✓
  - [x] Set OpenAI/Anthropic API keys ✓
  - [x] Configure port mapping (8000) ✓
- [x] Configure Neo4j MCP-Memory Docker service ✓
  - [x] Runs via Docker command in .mcp.json ✓
  - [x] Uses network connection to Neo4j ✓
  - [x] No port mapping needed (command-based) ✓

## 2. Basic Graphiti Integration via MCP

### MCP API Reference
Key operations we'll use:
- `add_episode()` - Add document/event with timestamp
- `search()` - Temporal and semantic search
- `get_entity_mentions()` - Get entity history
- `delete_episode()` - Remove episodes
- `clear()` - Clear entire graph

### 2.1 Create MCP Client Adapter
- [ ] Create `src/graphrag/mcp_graphiti_client.py`
  - [ ] Initialize MCP client connection
  - [ ] Set up langchain-mcp adapter
  - [ ] Configure error handling and logging
  - [ ] Test connection to MCP server

### 2.2 Define Political Schema
- [ ] Create `src/graphrag/political_schema_v2.py`
  - [ ] Define entity types (Policy, Politician, Organization, Event)
  - [ ] Define relationships (PROPOSES, AFFECTS, AMENDS, etc.)
  - [ ] Create Pydantic models for validation

### 2.3 Test MCP Connection
- [ ] Create `scripts/test_mcp_graphiti_connection.py`
  - [ ] Test MCP server availability
  - [ ] Test Graphiti operations via MCP
  - [ ] Verify Neo4j connection through MCP
  - [ ] Test basic episode creation

## 3. Document Processing Pipeline

### 3.1 Sample Data Preparation
- [ ] Select 3-5 sample political documents
  - [ ] EU AI Act proposal
  - [ ] GDPR enforcement update
  - [ ] Recent regulatory news
- [ ] Place in `data/test/phase1/` folder

### 3.2 Episode Creation via MCP
- [ ] Create `scripts/test_mcp_episode_creation.py`
  - [ ] Load sample documents
  - [ ] Create episodes via MCP API
  - [ ] Test entity extraction through MCP
  - [ ] Verify graph population in Neo4j

### 3.3 Temporal Data Verification
- [ ] Query Neo4j browser to see:
  - [ ] Nodes created with temporal properties
  - [ ] Relationships with valid_from/valid_to
  - [ ] Episode nodes with timestamps

## 4. Temporal Query Testing

### 4.1 Basic Temporal Queries
- [ ] Create `scripts/test_temporal_queries.py`
  - [ ] Query entities at specific time points
  - [ ] Get entity history over time
  - [ ] Find relationships valid at certain dates

### 4.2 Political Domain Queries
- [ ] Test "What changed since date X?"
- [ ] Test "Show policy evolution"
- [ ] Test "Find all events in time range"
- [ ] Test "Get entity state at point in time"

### 4.3 Performance Benchmarks
- [ ] Measure query response times
- [ ] Test with increasing data volumes
- [ ] Document performance characteristics

## 5. Integration Points

### 5.1 Langfuse Integration
- [ ] Create Langfuse prompts for:
  - [ ] Entity extraction
  - [ ] Relationship identification
  - [ ] Temporal context analysis
- [ ] Upload prompts with `just upload-prompts`

### 5.2 Shared Document Processor
- [ ] Create `src/processors/mcp_document_processor.py`
  - [ ] Reusable document chunking
  - [ ] MCP API calls for entity extraction
  - [ ] Episode creation via MCP
  - [ ] Error handling for MCP operations

## 6. Validation & Testing

### 6.1 Unit Tests
- [ ] Create `tests/unit/test_graphiti_client.py`
- [ ] Create `tests/unit/test_temporal_queries.py`
- [ ] Test error scenarios
- [ ] Test data validation

### 6.2 Integration Tests
- [ ] Create `tests/integration/test_graphiti_pipeline.py`
- [ ] Test full document → graph flow
- [ ] Test temporal query accuracy
- [ ] Verify data integrity

### 6.3 Manual Validation
- [ ] Use Neo4j Browser to inspect graph
- [ ] Verify temporal relationships
- [ ] Check entity deduplication
- [ ] Validate query results

## 7. Documentation

### 7.1 Setup Guide
- [ ] Document Neo4j setup steps
- [ ] Create Graphiti configuration guide
- [ ] Write troubleshooting section

### 7.2 Query Examples
- [ ] Document common temporal queries
- [ ] Create political domain examples
- [ ] Show expected results

## Success Criteria

Phase 1 is complete when:
1. ✅ Neo4j + Graphiti running in Docker
2. ✅ Sample documents successfully ingested
3. ✅ Temporal queries return accurate results
4. ✅ Can query "what changed" between dates
5. ✅ Performance meets requirements (<300ms queries)
6. ✅ All tests passing

## Next Steps
Once Phase 1 is complete, we'll move to Phase 2: Building the Data Ingestion Kodosumi app with entity extraction and web research capabilities.

## Notes
- Start with minimal configuration
- Focus on temporal query validation
- Keep sample data small for quick iteration
- Document any Graphiti limitations discovered

### Why MCP Server Approach?
- **Avoids dependency conflicts**: Graphiti runs in its own Docker container
- **Clean API boundary**: Interact via MCP protocol instead of Python imports
- **Language agnostic**: Can be used by any language that supports MCP
- **Better isolation**: Graphiti dependencies don't affect our main app
- **Easier updates**: Update Graphiti independently of our application

### Why Both MCP Servers?
**Development Benefits**:
- **Graphiti MCP**: Document processing, temporal queries, episode management
- **Neo4j MCP-Memory**: Entity observations, relationship tracking, domain modeling

**Use Cases**:
- Use Graphiti for ingesting documents and temporal analysis
- Use Neo4j Memory for maintaining political entity state and observations
- Both servers share the same Neo4j instance but offer different abstractions