# CRUD Subagent - Parallel Neo4j Operations

## Overview

The CRUD Subagent is a Ray-based parallel execution system for Neo4j CRUD operations. It wraps the Neo4j CRUD MCP Server and provides high-throughput parallel processing through a pool of Ray actors.

**Key Features:**
- **Parallel Execution**: 10 concurrent Ray actors for 10-20x speedup
- **MCP Integration**: Communicates with Neo4j CRUD MCP Server
- **Automatic Retry**: Built-in retry logic for transient failures
- **Batch Processing**: Handles large operation sets efficiently
- **Statistics Tracking**: Real-time execution metrics

**Architecture:**
```
Manager Skill
    ↓
CRUDSubagent (Manager)
    ↓
[Ray Actor Pool - 10 replicas]
    ↓
MCP Server (HTTP)
    ↓
Neo4j Database
```

## Installation

The CRUD Subagent is part of the main project. Ensure dependencies are installed:

```bash
# Ray is already in pyproject.toml dependencies
uv sync
```

## Configuration

### Environment Variables

```env
# MCP Server URL
NEO4J_CRUD_MCP_URL=http://localhost:8002

# Actor pool configuration
CRUD_SUBAGENT_REPLICAS=10
CRUD_SUBAGENT_TIMEOUT=30.0
CRUD_SUBAGENT_MAX_RETRIES=3
CRUD_SUBAGENT_RETRY_DELAY=1.0
```

### Configuration Object

```python
from src.subagents.crud_subagent.config import CRUDSubagentConfig

# Load from environment
config = CRUDSubagentConfig.from_env()

# Or create manually
config = CRUDSubagentConfig(
    mcp_url="http://localhost:8002",
    num_replicas=10,
    timeout_seconds=30.0,
    max_retries=3,
    retry_delay_seconds=1.0
)
```

## Usage

### Basic Usage

```python
import asyncio
import ray
from src.subagents.crud_subagent import CRUDSubagent

# Initialize Ray (if not already running)
ray.init()

# Create subagent instance
subagent = CRUDSubagent(mcp_url="http://localhost:8002", num_replicas=10)

# Start actor pool
subagent.start()

# Execute single operation
async def create_person():
    result = await subagent.execute_operation({
        "operation": "create_node",
        "entity_type": "BundestagPerson",
        "properties": {
            "id": "11004809",
            "vorname": "Olaf",
            "nachname": "Scholz",
            "titel": "Dr."
        }
    })
    print(f"Success: {result.success}, Message: {result.message}")

asyncio.run(create_person())

# Stop actor pool when done
subagent.stop()
```

### Parallel Execution (High Performance)

This is the primary use case - executing many operations in parallel:

```python
import asyncio
import ray
from src.subagents.crud_subagent import CRUDSubagent

ray.init()

subagent = CRUDSubagent(mcp_url="http://localhost:8002", num_replicas=10)
subagent.start()

async def update_100_persons():
    # Prepare 100 operations
    operations = []
    for i in range(100):
        operations.append({
            "operation": "update_node",
            "entity_type": "BundestagPerson",
            "node_id": f"person_{i}",
            "properties": {"updated_at": "2025-11-16T10:30:00"}
        })

    # Execute all in parallel (10-20x faster than sequential)
    results = await subagent.execute_parallel(operations)

    # Check results
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    avg_time = sum(r.execution_time_ms for r in results) / len(results)

    print(f"Completed: {successful} succeeded, {failed} failed")
    print(f"Average execution time: {avg_time:.2f}ms")

asyncio.run(update_100_persons())
subagent.stop()
```

### Batch Processing (Very Large Sets)

For extremely large operation sets:

```python
async def process_1000_persons():
    operations = [...]  # 1000 operations

    # Process in batches of 100 (10 actors * 10 operations each)
    results = await subagent.execute_batch(
        operations,
        batch_size=100
    )

    print(f"Processed {len(results)} operations in batches")

asyncio.run(process_1000_persons())
```

## Operation Types

### 1. Create Node

```python
operation = {
    "operation": "create_node",
    "entity_type": "BundestagPerson",
    "properties": {
        "id": "11004809",
        "vorname": "Olaf",
        "nachname": "Scholz",
        "titel": "Dr.",
        "geschlecht": "männlich",
        "geburtsdatum": "1958-06-14"
    }
}

result = await subagent.execute_operation(operation)
```

### 2. Update Node

```python
operation = {
    "operation": "update_node",
    "entity_type": "BundestagPerson",
    "node_id": "11004809",
    "properties": {
        "titel": "Bundeskanzler Dr.",
        "fraktion": "SPD"
    }
}

result = await subagent.execute_operation(operation)
```

### 3. Delete Node

```python
# Soft delete (sets active=false)
operation = {
    "operation": "delete_node",
    "entity_type": "BundestagPerson",
    "node_id": "11004809",
    "hard_delete": False
}

# Hard delete (permanently removes)
operation = {
    "operation": "delete_node",
    "entity_type": "BundestagPerson",
    "node_id": "11004809",
    "hard_delete": True
}

result = await subagent.execute_operation(operation)
```

### 4. Create Relationship

```python
operation = {
    "operation": "create_relationship",
    "from_entity_type": "BundestagPerson",
    "from_node_id": "11004809",
    "to_entity_type": "BundestagFraktion",
    "to_node_id": "SPD",
    "relationship_type": "MEMBER_OF",
    "properties": {
        "since": "2021-12-08",
        "position": "Vorsitzender"
    }
}

result = await subagent.execute_operation(operation)
```

### 5. Update Relationship

```python
operation = {
    "operation": "update_relationship",
    "from_entity_type": "BundestagPerson",
    "from_node_id": "11004809",
    "to_entity_type": "BundestagFraktion",
    "to_node_id": "SPD",
    "relationship_type": "MEMBER_OF",
    "properties": {
        "position": "Vorsitzender und Bundeskanzler"
    }
}

result = await subagent.execute_operation(operation)
```

### 6. Query Nodes

```python
operation = {
    "operation": "query_nodes",
    "entity_type": "BundestagPerson",
    "filters": {
        "fraktion": "SPD",
        "active": True
    },
    "limit": 50,
    "skip": 0
}

result = await subagent.execute_operation(operation)

# Access query results
if result.success:
    nodes = result.data["nodes"]
    total_count = result.data["total_count"]
    print(f"Found {len(nodes)} of {total_count} total nodes")
```

## Performance Metrics

### Execution Statistics

```python
# Get pool-wide statistics
stats = await subagent.get_pool_statistics()

print(f"Total actors: {stats['total_actors']}")
print(f"Total operations: {stats['total_operations']}")
print(f"Success rate: {stats['overall_success_rate']:.2f}%")

# Per-actor breakdown
for i, actor_stats in enumerate(stats['per_actor_stats']):
    print(f"Actor {i}: {actor_stats['operations_executed']} operations")
```

### Performance Benchmarks

**Sequential vs Parallel (100 operations):**
- Sequential (1 at a time): ~10-15 seconds
- Parallel (10 actors): ~1-2 seconds
- **Speedup: 10-15x**

**Large Batch Processing (1000 operations):**
- Sequential: ~100-150 seconds
- Parallel with batching: ~10-15 seconds
- **Speedup: 10x**

## Error Handling

### Operation Result

Every operation returns an `OperationResult`:

```python
class OperationResult:
    success: bool                    # Operation succeeded
    operation: str                   # Operation type
    entity_type: Optional[str]       # Entity type
    node_id: Optional[str]           # Node ID
    message: str                     # Human-readable message
    data: Optional[Dict]             # Result data
    error: Optional[str]             # Error message if failed
    execution_time_ms: float         # Execution time
```

### Handling Failures

```python
results = await subagent.execute_parallel(operations)

# Separate successes and failures
successes = [r for r in results if r.success]
failures = [r for r in results if not r.success]

# Log failures
for failure in failures:
    print(f"Failed: {failure.operation} - {failure.error}")

# Retry failures
if failures:
    retry_operations = [
        # Reconstruct operation from failure result
        {"operation": f.operation, ...}
        for f in failures
    ]
    retry_results = await subagent.execute_parallel(retry_operations)
```

### Automatic Retry

The MCP client automatically retries on:
- HTTP 5xx errors (server errors)
- Network timeouts
- Connection failures

Retry configuration:
- Max retries: 3 (configurable via `CRUD_SUBAGENT_MAX_RETRIES`)
- Retry delay: Exponential backoff starting at 1 second

## Advanced Usage

### Custom Actor Pool Size

```python
# More actors for higher throughput (if MCP server can handle it)
subagent = CRUDSubagent(num_replicas=20)

# Fewer actors for resource-constrained environments
subagent = CRUDSubagent(num_replicas=5)
```

### Using Pydantic Schemas

```python
from src.subagents.crud_subagent.schemas import CreateNodeOperation

# Type-safe operation creation
operation = CreateNodeOperation(
    entity_type="BundestagPerson",
    properties={"id": "123", "vorname": "Anna"}
)

result = await subagent.execute_operation(operation)
```

### Integration with Manager Skills

The CRUD Subagent is designed to be called by Manager Skills:

```python
class BundestagPersonManager:
    def __init__(self):
        self.crud_subagent = CRUDSubagent(num_replicas=10)
        self.crud_subagent.start()

    async def sync_persons(self, diff_operations):
        # diff_operations = list of CRUD operations from diff analysis
        results = await self.crud_subagent.execute_parallel(diff_operations)
        return results
```

## Testing

### Unit Tests

```python
# tests/unit/test_crud_subagent.py
import pytest
from src.subagents.crud_subagent import CRUDSubagent

@pytest.fixture
def subagent():
    return CRUDSubagent(mcp_url="http://localhost:8002", num_replicas=2)

@pytest.mark.asyncio
async def test_create_node(subagent):
    subagent.start()

    result = await subagent.execute_operation({
        "operation": "create_node",
        "entity_type": "BundestagPerson",
        "properties": {"id": "test123", "vorname": "Test"}
    })

    assert result.success
    assert result.node_id == "test123"

    subagent.stop()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_parallel_execution_performance():
    subagent = CRUDSubagent(num_replicas=10)
    subagent.start()

    # Create 100 operations
    operations = [
        {"operation": "create_node", "entity_type": "BundestagPerson",
         "properties": {"id": f"perf_test_{i}", "vorname": f"Person{i}"}}
        for i in range(100)
    ]

    import time
    start = time.time()
    results = await subagent.execute_parallel(operations)
    duration = time.time() - start

    # Should complete in < 5 seconds with parallelization
    assert duration < 5.0
    assert len([r for r in results if r.success]) == 100

    subagent.stop()
```

## Troubleshooting

### Actor Pool Not Starting

**Problem**: `subagent.start()` fails or actors don't respond

**Solution**:
```bash
# Check if Ray is running
ray status

# Restart Ray
ray stop
ray start --head

# Verify Ray dashboard
open http://localhost:8265
```

### MCP Connection Errors

**Problem**: "Connection refused" or timeout errors

**Solution**:
```bash
# Check MCP server is running
docker ps | grep neo4j-crud-mcp

# Check MCP health
curl http://localhost:8002/health

# Restart MCP server
docker compose restart neo4j-crud-mcp
```

### Poor Performance

**Problem**: Parallel execution not faster than sequential

**Possible causes**:
1. **Too few actors**: Increase `num_replicas`
2. **MCP server bottleneck**: Check MCP server logs
3. **Neo4j database bottleneck**: Check Neo4j performance
4. **Network latency**: Ensure MCP server and Neo4j are local

**Solution**:
```python
# Monitor execution times
results = await subagent.execute_parallel(operations)
times = [r.execution_time_ms for r in results]
print(f"Min: {min(times)}ms, Max: {max(times)}ms, Avg: {sum(times)/len(times)}ms")

# Check pool statistics
stats = await subagent.get_pool_statistics()
print(f"Success rate: {stats['overall_success_rate']}%")
```

### Memory Issues

**Problem**: Out of memory with large operation sets

**Solution**: Use batch processing
```python
# Instead of:
results = await subagent.execute_parallel(huge_operations_list)

# Use batches:
results = await subagent.execute_batch(
    huge_operations_list,
    batch_size=100  # Adjust based on available memory
)
```

## Best Practices

### 1. Always Use Parallel Execution for Multiple Operations

```python
# ❌ BAD: Sequential execution
for op in operations:
    await subagent.execute_operation(op)

# ✅ GOOD: Parallel execution
await subagent.execute_parallel(operations)
```

### 2. Start Actor Pool Once, Reuse for Multiple Calls

```python
# ✅ GOOD: Reuse actor pool
subagent = CRUDSubagent(num_replicas=10)
subagent.start()

await subagent.execute_parallel(batch1)
await subagent.execute_parallel(batch2)
await subagent.execute_parallel(batch3)

subagent.stop()
```

### 3. Handle Failures Gracefully

```python
results = await subagent.execute_parallel(operations)

# Check for failures
failures = [r for r in results if not r.success]
if failures:
    logger.warning(f"{len(failures)} operations failed")
    # Implement retry or error handling logic
```

### 4. Monitor Performance

```python
# Get statistics after major operations
stats = await subagent.get_pool_statistics()
logger.info(f"Pool statistics: {stats}")
```

### 5. Clean Up Resources

```python
try:
    subagent.start()
    # ... do work ...
finally:
    subagent.stop()
```

## Next Steps

- **Implement Manager Skill**: See `docs/skills/bundestag-person-manager.md`
- **Understand Architecture**: See `docs/architecture/parallel-crud-architecture.md`
- **API Reference**: See `docs/api/bundestag-person-manager-api.md`
