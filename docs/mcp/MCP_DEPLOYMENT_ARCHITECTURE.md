# MCP Server Deployment Architecture

**Version:** 2.0
**Last Updated:** March 2026
**Servers:** 4 MCP servers across Docker containers

---

## Overview

The PolicyTracker MCP servers are deployed as **standalone Docker containers** managed by `docker-compose.yml`. They are independent of the Ray Serve application layer (chat-server, Kodosumi flows) and communicate via HTTP/SSE.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Clients                                       │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐  │
│  │ Claude Agent │  │ Claude Code  │  │ Chat Agent  │  │ Open WebUI│  │
│  │ (Ray Serve) │  │ (.mcp.json)  │  │ (LangGraph) │  │ (Browser) │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └─────┬─────┘  │
│         │                │                  │                │        │
│         │    SSE/HTTP    │    SSE/stdio     │    SSE/HTTP    │        │
└─────────┼────────────────┼──────────────────┼────────────────┼────────┘
          │                │                  │                │
┌─────────▼────────────────▼──────────────────▼────────────────▼────────┐
│                     Docker Network                                     │
│                                                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ Neo4j CRUD   │ │ Graph        │ │ Bundestag    │ │ Web Search   │ │
│  │ MCP :8002    │ │ Retrieval    │ │ DIP MCP      │ │ MCP :8005    │ │
│  │ (REST/HTTP)  │ │ MCP :8003    │ │ :8004        │ │ (SSE)        │ │
│  │              │ │ (SSE)        │ │ (SSE)        │ │              │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
│         │                │                │                  │        │
│         ▼                ▼                ▼                  ▼        │
│  ┌──────────────┐  ┌──────────┐   ┌──────────────┐  ┌────────────┐  │
│  │  Neo4j DB    │  │ Neo4j DB │   │ Bundestag    │  │ Exa.ai API │  │
│  │  :7687       │  │ :7687    │   │ DIP API      │  │ DPA API    │  │
│  └──────────────┘  └──────────┘   │ (Public)     │  └────────────┘  │
│                                    └──────────────┘                   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    APISIX Gateway :9080                           │ │
│  │              (Optional LLM cost tracking proxy)                  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Transport Protocols

### SSE (Server-Sent Events) — Primary MCP Transport

Used by: **Graph Retrieval** (8003), **Bundestag DIP** (8004), **Web Search** (8005)

SSE is the standard MCP remote transport. The server exposes two endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sse` | GET | Persistent SSE connection for server-to-client events |
| `/messages/` | POST | Client-to-server request channel |

**How it works:**

```
Client                              MCP Server
  │                                      │
  │──── GET /sse ─────────────────────►  │  (1) Open SSE stream
  │◄──── SSE: connection established ──  │
  │                                      │
  │──── POST /messages/ ──────────────►  │  (2) Send tool call request
  │◄──── SSE: tool result ────────────  │  (3) Receive result via SSE
  │                                      │
  │◄──── SSE: keepalive ──────────────  │  (4) Connection stays open
  │                                      │
```

**Server-side implementation pattern:**

```python
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette

# Initialize MCP server and SSE transport
mcp_server = Server("graph-retrieval-mcp")
sse = SseServerTransport("/messages/")

# SSE endpoint — client connects here
async def handle_sse(request: Request):
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1],
            mcp_server.create_initialization_options()
        )

# Message endpoint — client sends requests here
async def handle_messages(request: Request):
    await sse.handle_post_message(
        request.scope, request.receive, request._send
    )

# Register routes
app = Starlette(routes=[
    Route("/sse", endpoint=handle_sse),
    Route("/messages/", endpoint=handle_messages, methods=["POST"]),
    Route("/health", endpoint=health_check),
])
```

**Client connection:**

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client("http://localhost:8003/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("search_knowledge_graph", {
            "query": "KI-Verordnung"
        })
```

### REST/HTTP — Neo4j CRUD Server

Used by: **Neo4j CRUD** (8002)

Standard FastAPI HTTP endpoints, not MCP protocol. Direct request/response.

```python
# FastAPI server (not MCP)
app = FastAPI(title="Neo4j CRUD MCP Server")

@app.post("/create_node")
async def create_node(request: CreateNodeRequest):
    ...

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### stdio — Claude Code NPX Integration

Used by: **Claude Code** via `.mcp.json` configuration

NPX spawns the MCP server as a child process and communicates over stdin/stdout.

```jsonc
// .mcp.json (Claude Code configuration)
{
  "servers": {
    "neo4j-memory": {
      "command": "uvx",
      "args": ["mcp-neo4j-memory@0.1.3"],
      "env": {
        "NEO4J_URL": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password123"
      }
    }
  }
}
```

**How stdio works:**

```
Claude Code                    NPX Child Process
    │                                │
    │── spawn(npx mcp-server) ────► │  (1) Start process
    │                                │
    │── stdin: JSON-RPC request ──► │  (2) Send tool call
    │◄── stdout: JSON-RPC response──│  (3) Receive result
    │                                │
    │── stdin: close ──────────────►│  (4) Terminate
```

### Transport Comparison

| Transport | Protocol | Latency | Use Case | Connection |
|-----------|----------|---------|----------|------------|
| **SSE** | HTTP streaming | Low | Remote servers, Docker containers | Persistent |
| **stdio** | stdin/stdout | Lowest | Local CLI tools, Claude Code | Process lifetime |
| **REST** | HTTP req/res | Medium | Simple CRUD, non-MCP clients | Per-request |

---

## Docker Deployment

### Container Configuration

All MCP servers are defined in `docker-compose.yml`:

```yaml
# Graph Retrieval MCP Server
graph-retrieval-mcp:
  build:
    context: .
    dockerfile: src/mcp/graph_retrieval/Dockerfile
  container_name: policiytracker-graph-retrieval-mcp
  ports:
    - "8003:8003"
  environment:
    - NEO4J_URI=bolt://neo4j:7687
    - NEO4J_USER=neo4j
    - NEO4J_PASSWORD=${NEO4J_PASSWORD}
    - NEO4J_DATABASE=${NEO4J_DATABASE}
    - MCP_HOST=0.0.0.0
    - MCP_PORT=8003
  depends_on:
    neo4j:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
    interval: 30s
    timeout: 10s
    start_period: 5s
    retries: 3

# Bundestag DIP MCP Server
bundestag-dip-mcp:
  build:
    context: .
    dockerfile: src/mcp/bundestag_dip/Dockerfile
  container_name: policiytracker-bundestag-dip-mcp
  ports:
    - "8004:8004"
  environment:
    - MCP_HOST=0.0.0.0
    - MCP_PORT=8004
    - BUNDESTAG_DIP_API_KEY=${BUNDESTAG_DIP_API_KEY:-}
    - APISIX_GATEWAY_URL=http://apisix:9080
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
    interval: 30s
    timeout: 10s
    retries: 3

# Web Search MCP Server
web-search-mcp:
  build:
    context: .
    dockerfile: src/mcp/web_search/Dockerfile
  container_name: policiytracker-web-search-mcp
  ports:
    - "8005:8005"
  environment:
    - MCP_HOST=0.0.0.0
    - MCP_PORT=8005
    - EXA_API_KEY=${EXA_API_KEY}
    - DPA_API_KEY=${DPA_API_KEY:-}
    - APISIX_GATEWAY_URL=http://apisix:9080
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
    interval: 30s
    timeout: 10s
    retries: 3

# Neo4j CRUD MCP Server
neo4j-crud-mcp:
  build:
    context: .
    dockerfile: src/mcp/neo4j_crud/Dockerfile
  container_name: policiytracker-neo4j-crud-mcp
  ports:
    - "8002:8002"
  environment:
    - NEO4J_URI=bolt://neo4j:7687
    - NEO4J_USER=neo4j
    - NEO4J_PASSWORD=${NEO4J_PASSWORD}
    - NEO4J_DATABASE=${NEO4J_DATABASE}
    - MCP_HOST=0.0.0.0
    - MCP_PORT=8002
  depends_on:
    neo4j:
      condition: service_healthy
    apisix:
      condition: service_started
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

### Dockerfile Pattern

All MCP servers follow the same Dockerfile structure:

```dockerfile
FROM python:3.12-slim
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY src/mcp/{server_name}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ /app/src/

# Expose port
EXPOSE {port}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:{port}/health || exit 1

# Run server
CMD ["python", "-m", "src.mcp.{server_name}.server"]
```

### Dependency Graph

```
neo4j (must be healthy)
  ├── neo4j-crud-mcp
  └── graph-retrieval-mcp

apisix (must be started)
  ├── neo4j-crud-mcp
  ├── bundestag-dip-mcp (optional, for cost tracking)
  └── web-search-mcp (optional, for cost tracking)

No dependencies:
  ├── bundestag-dip-mcp (uses public Bundestag API)
  └── web-search-mcp (uses Exa.ai / DPA APIs)
```

---

## Source Code Structure

```
src/mcp/
├── __init__.py
├── neo4j_crud/
│   ├── __init__.py
│   ├── server.py              # FastAPI REST server
│   ├── config.py              # Configuration (Neo4j connection)
│   ├── operations.py          # CRUD operations
│   ├── schemas.py             # Pydantic request/response models
│   ├── Dockerfile
│   └── requirements.txt
├── graph_retrieval/
│   ├── __init__.py
│   ├── server.py              # SSE MCP server (19 tools)
│   ├── retriever.py           # 4-stage context retrieval + hybrid search
│   ├── config.py
│   ├── Dockerfile
│   └── requirements.txt
├── bundestag_dip/
│   ├── __init__.py
│   ├── server.py              # SSE MCP server (8 tools)
│   ├── client.py              # Bundestag DIP API client
│   ├── Dockerfile
│   └── requirements.txt
└── web_search/
    ├── __init__.py
    ├── server.py              # SSE MCP server (4 tools)
    ├── exa_client.py          # Exa.ai search client
    ├── dpa_client.py          # DPA news client
    ├── Dockerfile
    └── requirements.txt
```

---

## Port Allocation

| Port | Service | Transport | Protocol |
|------|---------|-----------|----------|
| 7687 | Neo4j (Bolt) | TCP | Bolt |
| 7474 | Neo4j Browser | HTTP | HTTP |
| 8001 | Ray Serve (Chat + Flows) | HTTP | REST/SSE |
| 8002 | Neo4j CRUD MCP | HTTP | REST |
| 8003 | Graph Retrieval MCP | HTTP | SSE |
| 8004 | Bundestag DIP MCP | HTTP | SSE |
| 8005 | Web Search MCP | HTTP | SSE |
| 8265 | Ray Dashboard | HTTP | HTTP |
| 9080 | APISIX Gateway | HTTP | HTTP |

---

## Environment Variables

### Required for All Neo4j-Connected Servers

```bash
NEO4J_URI=bolt://neo4j:7687          # Docker internal: bolt://neo4j:7687
NEO4J_USER=neo4j                      # Local: bolt://localhost:7687
NEO4J_PASSWORD=password123
NEO4J_DATABASE=politicalmonitoring.v3
```

### Server-Specific Variables

```bash
# Graph Retrieval (8003)
MCP_HOST=0.0.0.0
MCP_PORT=8003

# Bundestag DIP (8004)
MCP_HOST=0.0.0.0
MCP_PORT=8004
BUNDESTAG_DIP_API_KEY=              # Optional (public API works without key)

# Web Search (8005)
MCP_HOST=0.0.0.0
MCP_PORT=8005
EXA_API_KEY=your-exa-api-key        # Required
DPA_API_KEY=your-dpa-api-key        # Optional

# Neo4j CRUD (8002)
MCP_HOST=0.0.0.0
MCP_PORT=8002
OPENAI_API_KEY=your-key             # For Graphiti registration features
APISIX_GATEWAY_URL=http://apisix:9080
```

---

## Health Checks

All servers expose a `/health` endpoint:

```bash
# Check all MCP servers
curl http://localhost:8002/health    # Neo4j CRUD
curl http://localhost:8003/health    # Graph Retrieval
curl http://localhost:8004/health    # Bundestag DIP
curl http://localhost:8005/health    # Web Search
```

**Response format:**

```json
{
  "status": "healthy",
  "server": "graph-retrieval-mcp",
  "database": "politicalmonitoring.v3",
  "version": "2.0"
}
```

**Docker health check configuration:**
- **Interval:** 30 seconds
- **Timeout:** 10 seconds
- **Start period:** 5 seconds
- **Retries:** 3

---

## Hybrid Search Architecture (Graph Retrieval Server)

The Graph Retrieval MCP server implements a 4-stage retrieval pipeline with hybrid search:

```
Query: "What regulations affect AI?"
                │
                ▼
┌─────────────────────────────────┐
│  Stage 1: Entity Search         │
│  (0.4 * keyword + 0.6 * vector) │
│  → Entity nodes with names,     │
│    embeddings (1536-dim)         │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Stage 2: Relationship Search   │
│  (0.3 * keyword + 0.7 * vector) │
│  → Edge facts with embeddings   │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Stage 3: Episode Search        │
│  (0.3 * BM25 + 0.7 * vector)   │
│  → Source document chunks with   │
│    content embeddings (1536-dim) │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  Stage 4: Score Fusion &        │
│  Result Assembly                 │
│  → Combined ranked results       │
└─────────────────────────────────┘
```

**Required Neo4j indexes:**

```sql
-- Entity indexes
CREATE CONSTRAINT entity_uuid_unique FOR (e:Entity) REQUIRE e.uuid IS UNIQUE;
CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name);
CREATE VECTOR INDEX entity_name_embedding FOR (e:Entity) ON (e.name_embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

-- Episode indexes
CREATE CONSTRAINT episodic_uuid_unique FOR (ep:Episodic) REQUIRE ep.uuid IS UNIQUE;
CREATE VECTOR INDEX episodic_content_embedding_index FOR (ep:Episodic) ON (ep.content_embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};
CREATE FULLTEXT INDEX episodic_content_fulltext FOR (ep:Episodic) ON EACH [ep.content, ep.name];
```

---

## Claude Code MCP Configuration

### Setup

1. Copy `.mcp.json.template` to `.mcp.json`
2. Add API keys
3. Ensure Docker containers are running

### .mcp.json Structure

```jsonc
{
  "servers": {
    // SSE-based servers (connect to running Docker containers)
    "graph-retrieval": {
      "transport": "sse",
      "url": "http://localhost:8003/sse"
    },
    "bundestag-dip": {
      "transport": "sse",
      "url": "http://localhost:8004/sse"
    },
    "web-search": {
      "transport": "sse",
      "url": "http://localhost:8005/sse"
    },

    // stdio-based servers (spawned as child processes)
    "neo4j-memory": {
      "command": "uvx",
      "args": ["mcp-neo4j-memory@0.1.3"],
      "env": {
        "NEO4J_URL": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password123"
      }
    }
  }
}
```

---

## Operations

### Starting MCP Servers

```bash
# Start all services including MCP servers
docker compose up -d

# Start only MCP servers
docker compose up -d neo4j-crud-mcp graph-retrieval-mcp bundestag-dip-mcp web-search-mcp

# Verify all healthy
docker compose ps | grep mcp
```

### Viewing Logs

```bash
# All MCP server logs
docker compose logs -f --tail=50 graph-retrieval-mcp bundestag-dip-mcp web-search-mcp neo4j-crud-mcp

# Single server
docker logs -f policiytracker-graph-retrieval-mcp

# Search for errors
docker logs policiytracker-graph-retrieval-mcp 2>&1 | grep -i error
```

### Restarting a Server

```bash
# Restart single server
docker compose restart graph-retrieval-mcp

# Rebuild and restart (after code changes)
docker compose up -d --build graph-retrieval-mcp
```

### Testing Connectivity

```bash
# Test SSE connection
curl -N http://localhost:8003/sse
# Should establish SSE stream (hangs open — Ctrl+C to exit)

# Test health endpoints
for port in 8002 8003 8004 8005; do
  echo "Port $port: $(curl -s http://localhost:$port/health | jq -r .status)"
done
```

---

## Troubleshooting

### Server Not Starting

```bash
# Check container status
docker compose ps | grep mcp

# Check container logs
docker logs policiytracker-graph-retrieval-mcp --tail=50

# Common issues:
# - Neo4j not ready: Check depends_on and neo4j health
# - Port conflict: Check if port is already in use
# - Missing env vars: Check .env file
```

### SSE Connection Refused

```bash
# Verify container is running and healthy
docker inspect policiytracker-graph-retrieval-mcp --format='{{.State.Health.Status}}'

# Check if port is exposed
docker port policiytracker-graph-retrieval-mcp

# Test from inside Docker network
docker exec policiytracker-graph-retrieval-mcp curl -s http://localhost:8003/health
```

### Neo4j Connection Errors

```bash
# Check Neo4j is running
docker compose ps neo4j

# Verify connection from MCP container
docker exec policiytracker-graph-retrieval-mcp python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'password123'))
d.verify_connectivity()
print('Connected')
d.close()
"
```

---

## Key Design Decisions

### Why Docker Containers (Not Ray Serve)?

MCP servers are deployed as Docker containers rather than Ray Serve applications because:

1. **Dependency isolation** — MCP servers have different Python dependencies than the main app (e.g., `mcp` SDK, specific API clients)
2. **Independent lifecycle** — MCP servers rarely change; Ray Serve apps change frequently
3. **Protocol requirements** — SSE transport needs persistent connections that Ray Serve's request-based model doesn't naturally support
4. **Simplicity** — Each server is a self-contained unit with its own Dockerfile

### Why SSE Over stdio for Production?

1. **Multi-client support** — Multiple clients can connect to one SSE server simultaneously
2. **Docker-native** — SSE works over HTTP, natural for container networking
3. **Monitoring** — Health checks, logging, and metrics via HTTP endpoints
4. **Scalability** — Can run multiple replicas behind a load balancer

### Why stdio for Claude Code?

1. **Zero configuration** — No Docker container needed, just `npx`/`uvx`
2. **Instant startup** — No server to wait for
3. **Session-scoped** — Process dies when Claude Code session ends

---

*Generated: March 2026 | 4 MCP servers across Docker containers*
