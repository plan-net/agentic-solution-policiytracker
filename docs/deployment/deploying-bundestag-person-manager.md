# Deploying BundestagPerson Manager

## Quick Start

Get the complete system running in 5 minutes:

```bash
# 1. Ensure Docker and Ray are available
docker --version  # Should show Docker 20+
ray --version     # Should show Ray 2.0+

# 2. Start Neo4j database
docker compose up neo4j -d

# 3. Start MCP server
docker compose build neo4j-crud-mcp
docker compose up neo4j-crud-mcp -d

# 4. Start Ray
ray start --head

# 5. Run demo
uv run python scripts/demo_bundestag_person_manager.py
```

## Detailed Setup

### Prerequisites

**Required Software**:
- Docker Desktop or Docker Engine (20.0+)
- Python 3.12.6
- uv (Python package manager)
- Ray (2.0+)

**Optional**:
- Bundestag DIP API key (for real data sync)

### Step-by-Step Deployment

#### 1. Environment Setup

Create `.env` file:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=politicamonitoring.v2

# MCP Server
NEO4J_CRUD_MCP_URL=http://localhost:8002

# CRUD Subagent
CRUD_SUBAGENT_REPLICAS=10
CRUD_SUBAGENT_TIMEOUT=30.0
CRUD_SUBAGENT_MAX_RETRIES=3

# Manager Configuration
MANAGER_MAX_CONCURRENT_OPS=100
MANAGER_BATCH_SIZE=50
MANAGER_CHECK_INTERVAL_HOURS=6

# Optional: Real DIP API
# BUNDESTAG_DIP_API_KEY=your_api_key_here
```

#### 2. Install Dependencies

```bash
# Install Python dependencies
uv sync

# Verify installation
uv run python -c "import ray; import httpx; import pydantic; print('✅ All dependencies installed')"
```

#### 3. Start Services

**Start Neo4j**:
```bash
docker compose up neo4j -d

# Wait for Neo4j to be healthy
docker compose ps neo4j

# Verify Neo4j is accessible
curl http://localhost:7474
```

**Build and start MCP Server**:
```bash
docker compose build neo4j-crud-mcp
docker compose up neo4j-crud-mcp -d

# Verify MCP server health
curl http://localhost:8002/health
```

**Start Ray cluster**:
```bash
# Start Ray head node
ray start --head

# Verify Ray is running
ray status

# Optional: View Ray dashboard
open http://localhost:8265
```

#### 4. Verify Installation

Run the demo script:

```bash
uv run python scripts/demo_bundestag_person_manager.py
```

Expected output:
```
================================================================================
BundestagPerson Manager - Complete Demo
================================================================================

DEMO 1: MCP Server - Direct CRUD Operations
...
✅ MCP Server demo complete!

DEMO 2: CRUD Subagent - Parallel Execution
...
✅ CRUD Subagent demo complete!

DEMO 3: Manager Skill - Intelligent Sync
...
✅ Manager Skill demo complete!

================================================================================
Demo Complete!
================================================================================
```

## Production Deployment

### Docker Compose Configuration

Add to your `docker-compose.yml`:

```yaml
services:
  neo4j:
    image: neo4j:5.26.0
    environment:
      NEO4J_AUTH: neo4j/password123
      NEO4J_PLUGINS: '["apoc"]'
    ports:
      - "7687:7687"
      - "7474:7474"
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "password123", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  neo4j-crud-mcp:
    build:
      context: .
      dockerfile: ./src/mcp/neo4j_crud/Dockerfile
    container_name: policiytracker-neo4j-crud-mcp
    depends_on:
      neo4j:
        condition: service_healthy
    ports:
      - "8002:8002"
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: password123
      NEO4J_DATABASE: politicamonitoring.v2
      MCP_HOST: 0.0.0.0
      MCP_PORT: 8002
      LOG_LEVEL: INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  neo4j_data:
```

### Ray Production Configuration

Create `ray_config.yaml`:

```yaml
cluster_name: bundestag-person-manager
max_workers: 10
upscaling_speed: 1.0

head_node:
  resources: {}

worker_nodes:
  min_workers: 0
  max_workers: 10
  resources: {}

provider:
  type: local
```

Start Ray cluster:

```bash
ray start --head --port=6379 --dashboard-host=0.0.0.0
```

### Systemd Service (Linux)

Create `/etc/systemd/system/bundestag-person-manager.service`:

```ini
[Unit]
Description=BundestagPerson Manager - Periodic Sync
After=network.target docker.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python scripts/scheduled_sync.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable bundestag-person-manager
sudo systemctl start bundestag-person-manager
sudo systemctl status bundestag-person-manager
```

## Monitoring

### Health Checks

Create `scripts/health_check.py`:

```python
import asyncio
import httpx
from neo4j import GraphDatabase

async def check_health():
    issues = []

    # Check MCP server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8002/health", timeout=5)
            if response.status_code != 200:
                issues.append(f"MCP server unhealthy: {response.status_code}")
    except Exception as e:
        issues.append(f"MCP server unreachable: {e}")

    # Check Neo4j
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
    except Exception as e:
        issues.append(f"Neo4j unreachable: {e}")

    # Check Ray
    try:
        import ray
        if not ray.is_initialized():
            issues.append("Ray not initialized")
    except Exception as e:
        issues.append(f"Ray unavailable: {e}")

    if issues:
        print("❌ Health check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ All systems healthy")
        return True

if __name__ == "__main__":
    asyncio.run(check_health())
```

Run health check:

```bash
uv run python scripts/health_check.py
```

### Logging Configuration

Create `logging_config.yaml`:

```yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  structured:
    format: '{"timestamp":"%(asctime)s","component":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    formatter: default
    level: INFO
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/bundestag_person_manager.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    formatter: structured
    level: DEBUG

loggers:
  src.skills.bundestag_person_manager:
    level: DEBUG
    handlers: [console, file]
  src.subagents.crud_subagent:
    level: DEBUG
    handlers: [console, file]
  src.mcp.neo4j_crud:
    level: INFO
    handlers: [console, file]

root:
  level: INFO
  handlers: [console, file]
```

Use in code:

```python
import logging.config
import yaml

with open("logging_config.yaml") as f:
    config = yaml.safe_load(f)
    logging.config.dictConfig(config)
```

## Troubleshooting

### Common Issues

**Issue 1: MCP Server Won't Start**

```bash
# Check Docker logs
docker logs policiytracker-neo4j-crud-mcp

# Common causes:
# - Neo4j not running
# - Port 8002 already in use
# - Environment variables not set

# Solutions:
docker compose restart neo4j-crud-mcp
docker compose up neo4j -d
lsof -i :8002  # Check port usage
```

**Issue 2: Ray Actors Not Starting**

```bash
# Check Ray status
ray status

# Check Ray logs
tail -f /tmp/ray/session_latest/logs/*.log

# Solutions:
ray stop
ray start --head
```

**Issue 3: Sync Operations Failing**

```python
# Enable debug logging
import logging
logging.getLogger('src.skills.bundestag_person_manager').setLevel(logging.DEBUG)

# Check specific error messages
result = await manager.sync_all_persons()
if not result.success:
    for error in result.errors:
        print(error)
```

### Performance Issues

**Slow Sync Times**:

1. Increase actor count:
```python
manager = BundestagPersonManager()
manager.config.crud_num_replicas = 20  # Increase from 10
```

2. Check Neo4j indexes:
```cypher
// In Neo4j Browser
SHOW INDEXES
// Should see indexes on BundestagPerson.id
```

3. Monitor Ray dashboard:
```bash
open http://localhost:8265
# Check CPU/memory usage
```

## Maintenance

### Regular Tasks

**Daily**:
- Check health status
- Review error logs
- Monitor disk space

**Weekly**:
- Run full sync
- Review sync metrics
- Check for updates

**Monthly**:
- Backup Neo4j database
- Review and optimize indexes
- Update dependencies

### Backup and Restore

**Backup Neo4j**:
```bash
docker exec policiytracker-neo4j neo4j-admin database dump neo4j --to-path=/backups
docker cp policiytracker-neo4j:/backups ./backups/
```

**Restore Neo4j**:
```bash
docker cp ./backups/neo4j.dump policiytracker-neo4j:/backups/
docker exec policiytracker-neo4j neo4j-admin database load neo4j --from-path=/backups
```

## Scaling

### Horizontal Scaling

For higher throughput, increase Ray actors:

```python
# Configuration for high throughput
config = ManagerConfig(
    crud_num_replicas=50,  # 50 actors
    batch_size=100,
    max_concurrent_operations=500
)
```

### Multi-Machine Ray Cluster

On head machine:
```bash
ray start --head --port=6379 --dashboard-host=0.0.0.0
```

On worker machines:
```bash
ray start --address='head-machine-ip:6379'
```

## Security

### Production Checklist

- [ ] Change default Neo4j password
- [ ] Use HTTPS for MCP server
- [ ] Implement API authentication
- [ ] Enable Neo4j encryption
- [ ] Restrict network access
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Implement rate limiting

### Environment Variables Security

Never commit `.env` file. Use secrets management:

```bash
# Use AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id bundestag-db-credentials

# Use HashiCorp Vault
vault kv get secret/bundestag/neo4j
```

## Next Steps

- Review [Architecture Documentation](../architecture/parallel-crud-architecture.md)
- Read [Manager Skill Guide](../skills/bundestag-person-manager.md)
- Check [CRUD Subagent Documentation](../subagents/crud-subagent.md)
- Explore [MCP Server API](../mcp/neo4j-crud-server.md)
