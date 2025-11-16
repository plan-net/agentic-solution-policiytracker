# Neo4j CRUD MCP Server

## Overview

The Neo4j CRUD MCP Server provides a generic REST API for performing Create, Read, Update, and Delete operations on any entity type in the Neo4j knowledge graph. It serves as a database abstraction layer that enables CRUD subagents to perform parallel operations without direct Neo4j driver management.

**Key Features:**
- Generic CRUD operations for all entity types (BundestagPerson, Vorgang, Drucksache, Aktivitaet, etc.)
- Reuses existing `Neo4jUpsertManager` infrastructure
- FastAPI-based REST API with OpenAPI documentation
- Docker container deployment with health checks
- Comprehensive error handling and logging

**Server Details:**
- **Port:** 8002
- **Container:** `policiytracker-neo4j-crud-mcp`
- **Base Path:** `/`
- **Health Check:** `GET /health`

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

Check the server and Neo4j connection health.

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "message": "Neo4j connection is working"
}
```

### 2. Create Node

**Endpoint:** `POST /create_node`

Create a new node in the knowledge graph.

**Request Body:**
```json
{
  "entity_type": "BundestagPerson",
  "properties": {
    "id": "11004809",
    "vorname": "Olaf",
    "nachname": "Scholz",
    "titel": "Dr.",
    "geschlecht": "männlich",
    "geburtsdatum": "1958-06-14",
    "geburtsort": "Osnabrück",
    "active": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Node created successfully",
  "data": {
    "entity_type": "BundestagPerson",
    "node_id": "11004809"
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "message": "Failed to create node",
  "error": "Upsert operation returned False"
}
```

### 3. Update Node

**Endpoint:** `POST /update_node`

Update properties of an existing node.

**Request Body:**
```json
{
  "entity_type": "BundestagPerson",
  "node_id": "11004809",
  "properties": {
    "titel": "Bundeskanzler Dr.",
    "fraktion": "SPD",
    "updated_at": "2025-11-16T10:30:00"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Node updated successfully",
  "data": {
    "entity_type": "BundestagPerson",
    "node_id": "11004809"
  }
}
```

### 4. Delete Node

**Endpoint:** `POST /delete_node`

Delete a node (soft delete by default, sets `active=false`).

**Request Body:**
```json
{
  "entity_type": "BundestagPerson",
  "node_id": "11004809",
  "hard_delete": false
}
```

**Parameters:**
- `hard_delete` (optional, default: `false`): If `true`, permanently deletes the node. If `false`, sets `active=false`.

**Response:**
```json
{
  "success": true,
  "message": "Node deactivated successfully",
  "data": {
    "entity_type": "BundestagPerson",
    "node_id": "11004809"
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "message": "Node not found",
  "error": "No node found with id=11004809"
}
```

### 5. Create Relationship

**Endpoint:** `POST /create_relationship`

Create a relationship between two nodes.

**Request Body:**
```json
{
  "from_entity_type": "BundestagPerson",
  "from_node_id": "11004809",
  "to_entity_type": "BundestagFraktion",
  "to_node_id": "SPD",
  "relationship_type": "MEMBER_OF",
  "properties": {
    "since": "2021-12-08",
    "position": "Vorsitzender",
    "active": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Relationship created successfully",
  "data": {
    "from_entity": "BundestagPerson",
    "to_entity": "BundestagFraktion",
    "relationship_type": "MEMBER_OF"
  }
}
```

**Error Response (404):**
```json
{
  "success": false,
  "message": "Failed to create relationship",
  "error": "One or both nodes not found"
}
```

### 6. Update Relationship

**Endpoint:** `POST /update_relationship`

Update properties of an existing relationship.

**Request Body:**
```json
{
  "from_entity_type": "BundestagPerson",
  "from_node_id": "11004809",
  "to_entity_type": "BundestagFraktion",
  "to_node_id": "SPD",
  "relationship_type": "MEMBER_OF",
  "properties": {
    "position": "Vorsitzender und Bundeskanzler",
    "updated_at": "2025-11-16T10:30:00"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Relationship updated successfully",
  "data": {
    "relationship_type": "MEMBER_OF"
  }
}
```

### 7. Query Nodes

**Endpoint:** `POST /query_nodes`

Query nodes with filters.

**Request Body:**
```json
{
  "entity_type": "BundestagPerson",
  "filters": {
    "fraktion": "SPD",
    "active": true
  },
  "limit": 10,
  "skip": 0
}
```

**Parameters:**
- `filters` (optional): Key-value pairs for exact property matches
- `limit` (optional, default: 100): Maximum number of results
- `skip` (optional, default: 0): Number of results to skip (pagination)

**Response:**
```json
{
  "success": true,
  "nodes": [
    {
      "id": "11004809",
      "vorname": "Olaf",
      "nachname": "Scholz",
      "fraktion": "SPD",
      "active": true
    }
  ],
  "total_count": 206,
  "returned_count": 1
}
```

## Supported Entity Types

The MCP server supports all entity types defined in `Neo4jUpsertManager.ENTITY_ID_FIELDS`:

- **BundestagPerson** (ID field: `id`)
- **BundestagVorgang** (ID field: `id`)
- **BundestagDrucksache** (ID field: `id`)
- **BundestagAktivitaet** (ID field: `id`)
- **BundestagFraktion** (ID field: `id`)
- **BundestagWahlperiode** (ID field: `nummer`)

## Setup Instructions

### Local Development

1. **Start Neo4j:**
```bash
docker compose up neo4j -d
```

2. **Build and start MCP server:**
```bash
docker compose build neo4j-crud-mcp
docker compose up neo4j-crud-mcp -d
```

3. **Verify health:**
```bash
curl http://localhost:8002/health
```

### Environment Variables

Configure in `.env` or `docker-compose.yml`:

```env
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=politicamonitoring.v2
MCP_HOST=0.0.0.0
MCP_PORT=8002
LOG_LEVEL=INFO
```

## Error Handling

### Common Error Codes

- **400 Bad Request**: Invalid request parameters or operation failed
- **404 Not Found**: Node or relationship not found
- **500 Internal Server Error**: Unexpected server error

### Error Response Format

All error responses follow this structure:

```json
{
  "success": false,
  "message": "High-level error description",
  "error": "Detailed error message"
}
```

### Handling Errors in Client Code

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8002/create_node",
        json={"entity_type": "BundestagPerson", "properties": {...}}
    )

    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            print(f"Created node: {result['data']['node_id']}")
        else:
            print(f"Operation failed: {result['message']}")
    else:
        print(f"HTTP Error {response.status_code}: {response.text}")
```

## Testing

### Manual Testing with curl

**Create a node:**
```bash
curl -X POST http://localhost:8002/create_node \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "BundestagPerson",
    "properties": {
      "id": "test123",
      "vorname": "Max",
      "nachname": "Mustermann"
    }
  }'
```

**Query nodes:**
```bash
curl -X POST http://localhost:8002/query_nodes \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "BundestagPerson",
    "filters": {"nachname": "Mustermann"},
    "limit": 5
  }'
```

**Update node:**
```bash
curl -X POST http://localhost:8002/update_node \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "BundestagPerson",
    "node_id": "test123",
    "properties": {"titel": "Dr."}
  }'
```

**Delete node (soft):**
```bash
curl -X POST http://localhost:8002/delete_node \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "BundestagPerson",
    "node_id": "test123",
    "hard_delete": false
  }'
```

### Python Testing

```python
import asyncio
import httpx

async def test_mcp_server():
    base_url = "http://localhost:8002"

    async with httpx.AsyncClient() as client:
        # Health check
        health = await client.get(f"{base_url}/health")
        print(f"Health: {health.json()}")

        # Create node
        create_response = await client.post(
            f"{base_url}/create_node",
            json={
                "entity_type": "BundestagPerson",
                "properties": {
                    "id": "test456",
                    "vorname": "Anna",
                    "nachname": "Test"
                }
            }
        )
        print(f"Create: {create_response.json()}")

        # Query nodes
        query_response = await client.post(
            f"{base_url}/query_nodes",
            json={
                "entity_type": "BundestagPerson",
                "filters": {"nachname": "Test"},
                "limit": 10
            }
        )
        print(f"Query: {query_response.json()}")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
```

## Performance Considerations

### Batch Operations

For bulk operations, use parallel CRUD subagents instead of sequential API calls:

```python
# ❌ BAD: Sequential calls
for person in persons:
    await mcp_client.create_node("BundestagPerson", person)

# ✅ GOOD: Parallel subagents (see CRUD Subagent documentation)
await crud_subagent_pool.execute_parallel(
    operations=[{"type": "create_node", ...} for person in persons]
)
```

### Connection Pooling

The MCP server maintains a single Neo4j driver instance with connection pooling. Default pool size handles up to 50 concurrent requests.

### Query Optimization

- Use `filters` to reduce result set size
- Use `limit` and `skip` for pagination
- Query by indexed fields (entity ID fields) when possible

## OpenAPI Documentation

Interactive API documentation available at:
- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc

## Logs and Monitoring

### View Container Logs

```bash
docker logs policiytracker-neo4j-crud-mcp -f
```

### Log Levels

Configure via `LOG_LEVEL` environment variable:
- `DEBUG`: Detailed operation logs
- `INFO`: Standard operation logs (default)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

### Example Log Output

```
INFO:     Starting Neo4j CRUD MCP Server...
INFO:     Connecting to Neo4j at bolt://neo4j:7687
INFO:     Initialized Neo4jCRUDOperations for database: politicamonitoring.v2
INFO:     Neo4j CRUD MCP Server started successfully
INFO:     POST /create_node: BundestagPerson
INFO:     Creating node: BundestagPerson
```

## Integration with CRUD Subagent

The MCP server is designed to be consumed by CRUD subagents. See `docs/subagents/crud-subagent.md` for integration details.

**Example subagent usage:**

```python
from src.subagents.crud_subagent import CRUDSubagent

subagent = CRUDSubagent(mcp_url="http://localhost:8002")

result = await subagent.execute_operation({
    "operation": "create_node",
    "entity_type": "BundestagPerson",
    "properties": {...}
})
```

## Troubleshooting

### Server Won't Start

**Check Neo4j connection:**
```bash
docker compose ps neo4j
docker logs policiytracker-neo4j
```

**Verify environment variables:**
```bash
docker compose config | grep -A 10 neo4j-crud-mcp
```

### Connection Refused

**Ensure container is running:**
```bash
docker compose ps neo4j-crud-mcp
```

**Check port mapping:**
```bash
docker compose port neo4j-crud-mcp 8002
```

### Operations Failing

**Check Neo4j database exists:**
```cypher
# In Neo4j Browser (http://localhost:7474)
SHOW DATABASES
```

**Verify entity type ID field mapping:**
```python
# In Neo4jUpsertManager
ENTITY_ID_FIELDS = {
    "BundestagPerson": "id",
    # ... check entity_type exists
}
```

## Next Steps

- **Use CRUD Subagent:** See `docs/subagents/crud-subagent.md` for parallel execution
- **Create Manager Skill:** See `docs/skills/bundestag-person-manager.md` for intelligent sync
- **Architecture Overview:** See `docs/architecture/parallel-crud-architecture.md` for system design
