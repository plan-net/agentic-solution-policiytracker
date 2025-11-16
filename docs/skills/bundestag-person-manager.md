# BundestagPerson Manager Skill

## Overview

The BundestagPerson Manager Skill is an intelligent data synchronization system that automatically keeps Neo4j BundestagPerson data up to date with the Bundestag DIP (Dokumentations- und Informationssystem) API. It analyzes differences, plans optimal CRUD operations, and executes them in parallel for high performance.

**Key Capabilities:**
- **Intelligent Diff Analysis**: Identifies missing and outdated persons automatically
- **Batched Execution**: Plans operations into optimal batches
- **Parallel Processing**: Executes 10-100 operations simultaneously via CRUD Subagent
- **Dry Run Mode**: Preview changes without applying them
- **Selective Sync**: Sync all persons or specific subsets

**Architecture:**
```
BundestagPersonManager (Orchestrator)
    ├── DiffAnalyzer → Compares Neo4j vs DIP API
    ├── SyncPlanner → Converts diffs to batched CRUD operations
    └── CRUDSubagent → Executes operations in parallel (10 actors)
            ↓
        MCP Server → Updates Neo4j database
```

## Installation

The Manager Skill is part of the main project:

```bash
# Install dependencies
uv sync

# Ensure Ray is initialized
ray start --head

# Ensure MCP server is running
docker compose up neo4j-crud-mcp -d
```

## Configuration

### Environment Variables

```env
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_DATABASE=politicamonitoring.v2

# Bundestag DIP API
BUNDESTAG_DIP_API_KEY=your_api_key_here  # Optional

# CRUD Subagent
NEO4J_CRUD_MCP_URL=http://localhost:8002
CRUD_SUBAGENT_REPLICAS=10

# Manager Behavior
MANAGER_MAX_CONCURRENT_OPS=100
MANAGER_BATCH_SIZE=50
MANAGER_CHECK_INTERVAL_HOURS=6
```

## Usage

### Basic Usage - Full Sync

```python
import asyncio
from src.skills.bundestag_person_manager import BundestagPersonManager

async def full_sync():
    # Initialize manager (uses mock DIP client for testing)
    manager = BundestagPersonManager(use_mock_dip=True)

    # Perform full synchronization
    result = await manager.sync_all_persons()

    print(f"Sync Result:")
    print(f"  Success: {result.success}")
    print(f"  Operations: {result.operations_succeeded}/{result.operations_attempted}")
    print(f"  Time: {result.execution_time_seconds:.2f}s")
    print(f"  Differences: {result.diff_summary}")

    # Clean up
    manager.close()

asyncio.run(full_sync())
```

### Dry Run - Preview Changes

```python
async def preview_sync():
    manager = BundestagPersonManager(use_mock_dip=True)

    # Dry run to see what would be changed
    result = await manager.sync_all_persons(dry_run=True)

    print(f"Preview Results:")
    print(f"  Would update: {result.operations_attempted} persons")
    print(f"  Missing in Neo4j: {result.diff_summary['missing_count']}")
    print(f"  Outdated in Neo4j: {result.diff_summary['outdated_count']}")

    manager.close()

asyncio.run(preview_sync())
```

### Sync Specific Persons

```python
async def sync_specific():
    manager = BundestagPersonManager(use_mock_dip=True)

    # Sync only specific person IDs
    person_ids = ["11004809", "11003142"]  # Olaf Scholz, Angela Merkel
    result = await manager.sync_specific_persons(person_ids)

    print(f"Synced {result.operations_succeeded} persons")

    manager.close()

asyncio.run(sync_specific())
```

### Check Sync Status

```python
async def check_status():
    manager = BundestagPersonManager(use_mock_dip=True)

    # Check status without making changes
    status = await manager.check_sync_status()

    print(f"Sync Status: {status['status']}")
    print(f"Total differences: {status['total_differences']}")
    print(f"Missing persons: {status['missing_persons']}")
    print(f"Outdated persons: {status['outdated_persons']}")
    print(f"Most changed fields: {status['most_changed_fields']}")

    manager.close()

asyncio.run(check_status())
```

### Limited Sync (Testing)

```python
async def limited_sync():
    manager = BundestagPersonManager(use_mock_dip=True)

    # Sync only first 100 persons (useful for testing)
    result = await manager.sync_all_persons(limit=100)

    print(f"Synced {result.operations_succeeded} persons")

    manager.close()

asyncio.run(limited_sync())
```

## Real DIP API Usage

When you have access to the real Bundestag DIP API:

```python
# Set API key in environment
import os
os.environ["BUNDESTAG_DIP_API_KEY"] = "your_real_api_key"

# Initialize with real DIP client
manager = BundestagPersonManager(use_mock_dip=False)

# Perform full sync
result = await manager.sync_all_persons()
```

## Components

### 1. DiffAnalyzer

Compares Neo4j data with Bundestag DIP API data.

**Methods:**
- `analyze_all_persons(limit)`: Analyze all persons (with optional limit)
- `analyze_specific_persons(person_ids)`: Analyze specific persons
- `generate_summary(diffs)`: Create summary of differences

**Diff Types:**
- `missing`: Person exists in DIP API but not in Neo4j
- `outdated`: Person exists but has outdated fields

**Example:**
```python
from neo4j import GraphDatabase
from src.skills.bundestag_person_manager.diff_analyzer import DiffAnalyzer
from src.skills.bundestag_person_manager.dip_client import MockBundestagDIPClient

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))
dip_client = MockBundestagDIPClient()

analyzer = DiffAnalyzer(driver, dip_client)
diffs = await analyzer.analyze_all_persons(limit=10)

for diff in diffs:
    print(f"{diff.person_id}: {diff.diff_type}")
    if diff.diff_type == "outdated":
        print(f"  Changed fields: {diff.changed_fields}")
```

### 2. SyncPlanner

Converts differences into batched CRUD operations.

**Methods:**
- `create_sync_plan(diffs)`: Convert diffs to batched operations

**Output:**
- `SyncPlan` with:
  - `operations`: All CRUD operations
  - `batches`: Operations grouped for parallel execution
  - `summary`: Plan statistics

**Example:**
```python
from src.skills.bundestag_person_manager.sync_planner import SyncPlanner

planner = SyncPlanner(batch_size=50, max_concurrent=100)
sync_plan = planner.create_sync_plan(diffs)

print(f"Total operations: {len(sync_plan.operations)}")
print(f"Batches: {len(sync_plan.batches)}")
print(f"Estimated time: {sync_plan.summary['estimated_execution_time_seconds']}s")
```

### 3. CRUDSubagent Integration

Executes operations in parallel via Ray actors.

**Process:**
1. SyncPlan is passed to CRUDSubagent
2. Operations distributed across 10 Ray actors
3. Batches executed sequentially, operations within batch in parallel
4. Results aggregated and returned

## Performance

### Benchmarks

**Sequential Execution (Old Approach):**
- 100 persons: ~100-150 seconds
- 1000 persons: ~1000-1500 seconds

**Parallel Execution (Manager Skill):**
- 100 persons: ~5-10 seconds  (**10-20x faster**)
- 1000 persons: ~50-100 seconds (**10-15x faster**)

### Performance Factors

1. **Number of Actors** (default: 10)
   - More actors = higher throughput
   - Limited by MCP server and Neo4j capacity

2. **Batch Size** (default: 50)
   - Optimal for memory usage and parallelization
   - Too large: memory issues
   - Too small: overhead from many batches

3. **Network Latency**
   - Local deployment: minimal impact
   - Remote Neo4j: affects all operations

## Error Handling

### SyncResult

Every sync operation returns a `SyncResult` with detailed information:

```python
result = await manager.sync_all_persons()

if result.success:
    print("✅ Sync successful")
else:
    print("❌ Sync failed")
    for error in result.errors:
        print(f"  Error: {error}")

# Detailed metrics
print(f"Success rate: {result.operations_succeeded / result.operations_attempted * 100:.1f}%")
print(f"Execution time: {result.execution_time_seconds:.2f}s")
```

### Handling Partial Failures

```python
result = await manager.sync_all_persons()

if result.operations_failed > 0:
    print(f"⚠️  {result.operations_failed} operations failed")
    print(f"✅  {result.operations_succeeded} operations succeeded")

    # Log errors
    for error in result.errors:
        logger.error(f"Operation error: {error}")

    # Optionally retry
    if result.operations_failed < 10:  # Only retry if few failures
        print("Retrying failed operations...")
        retry_result = await manager.sync_all_persons(limit=result.operations_failed)
```

## Advanced Usage

### Custom Configuration

```python
from src.skills.bundestag_person_manager.config import ManagerConfig

# Create custom config
config = ManagerConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password123",
    neo4j_database="politicamonitoring.v2",
    dip_api_key=None,
    crud_mcp_url="http://localhost:8002",
    crud_num_replicas=20,  # More replicas for higher throughput
    max_concurrent_operations=200,
    batch_size=100,
    check_interval_hours=6
)

manager = BundestagPersonManager(config=config, use_mock_dip=True)
```

### Scheduled Sync (Periodic Updates)

```python
import asyncio
from datetime import timedelta

async def scheduled_sync():
    manager = BundestagPersonManager(use_mock_dip=False)

    while True:
        try:
            print(f"Starting scheduled sync at {datetime.now()}")
            result = await manager.sync_all_persons()

            print(f"Sync complete: {result.operations_succeeded} operations succeeded")

            # Wait for next interval (6 hours)
            await asyncio.sleep(manager.config.check_interval_hours * 3600)

        except Exception as e:
            logger.error(f"Scheduled sync failed: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retry

asyncio.run(scheduled_sync())
```

### Integration with LangGraph

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class SyncState(TypedDict):
    sync_needed: bool
    result: Optional[Dict]

async def check_sync_needed(state: SyncState) -> SyncState:
    manager = BundestagPersonManager(use_mock_dip=True)
    status = await manager.check_sync_status()

    state["sync_needed"] = status["total_differences"] > 0
    return state

async def perform_sync(state: SyncState) -> SyncState:
    manager = BundestagPersonManager(use_mock_dip=True)
    result = await manager.sync_all_persons()

    state["result"] = result.to_dict()
    return state

# Build graph
workflow = StateGraph(SyncState)
workflow.add_node("check", check_sync_needed)
workflow.add_node("sync", perform_sync)
workflow.add_conditional_edges(
    "check",
    lambda s: "sync" if s["sync_needed"] else END
)
workflow.set_entry_point("check")

app = workflow.compile()
```

## Monitoring and Logging

### Structured Logging

The Manager Skill uses Python's logging module:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific log levels
logging.getLogger('src.skills.bundestag_person_manager').setLevel(logging.DEBUG)
```

### Key Log Messages

```
INFO: BundestagPersonManager initialized
INFO: Starting full sync (limit=None, dry_run=False)
INFO: Step 1: Analyzing differences...
INFO: Analysis complete: 50 differences found
INFO:   - Missing: 10
INFO:   - Outdated: 40
INFO: Step 2: Creating sync plan...
INFO: Sync plan created: 50 operations in 1 batches
INFO: Estimated execution time: 2.50s
INFO: Step 3: Executing operations...
INFO: Sync complete in 2.34s: 50 succeeded, 0 failed
```

## Testing

### Unit Tests

```python
# tests/unit/test_bundestag_person_manager.py
import pytest
from src.skills.bundestag_person_manager import BundestagPersonManager

@pytest.mark.asyncio
async def test_sync_with_mock_data():
    manager = BundestagPersonManager(use_mock_dip=True)

    result = await manager.sync_all_persons(dry_run=True)

    assert result.success
    assert result.operations_attempted >= 0

    manager.close()

@pytest.mark.asyncio
async def test_check_sync_status():
    manager = BundestagPersonManager(use_mock_dip=True)

    status = await manager.check_sync_status()

    assert "status" in status
    assert status["status"] in ["up_to_date", "out_of_sync"]

    manager.close()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_sync_integration():
    """Test complete sync workflow."""
    manager = BundestagPersonManager(use_mock_dip=True)

    # Perform sync
    result = await manager.sync_all_persons(limit=10)

    # Verify results
    assert result.success or result.operations_succeeded > 0
    assert result.execution_time_seconds < 30  # Should complete quickly

    # Verify Neo4j was updated
    status = await manager.check_sync_status()
    assert status["total_differences"] <= result.operations_attempted

    manager.close()
```

## Troubleshooting

### No Differences Found

**Problem**: `sync_all_persons()` reports 0 differences but you know data is outdated

**Solutions**:
1. Check Neo4j connection:
```python
with manager.neo4j_driver.session() as session:
    result = session.run("MATCH (p:BundestagPerson) RETURN count(p) as count")
    print(f"Persons in Neo4j: {result.single()['count']}")
```

2. Check DIP client is returning data:
```python
person_ids = await manager.dip_client.get_all_person_ids(limit=5)
print(f"DIP API returned {len(person_ids)} person IDs")
```

3. Verify field comparison logic in DiffAnalyzer

### Slow Performance

**Problem**: Sync takes longer than expected

**Solutions**:
1. Increase number of actors:
```python
config = ManagerConfig.from_env()
config.crud_num_replicas = 20  # Increase from default 10
manager = BundestagPersonManager(config=config)
```

2. Check MCP server performance:
```bash
docker logs policiytracker-neo4j-crud-mcp | tail -50
```

3. Check Neo4j query performance:
```cypher
// In Neo4j Browser
CALL db.index.fulltext.listAvailableAnalyzers()
```

### Partial Failures

**Problem**: Some operations fail during sync

**Solutions**:
1. Check specific errors:
```python
result = await manager.sync_all_persons()
for error in result.errors:
    print(f"Error: {error}")
```

2. Retry with smaller batches:
```python
config.batch_size = 10  # Reduce from default 50
```

3. Sync failed persons individually:
```python
# Get failed person IDs from logs
failed_ids = ["person1", "person2"]
await manager.sync_specific_persons(failed_ids)
```

## Best Practices

### 1. Always Use Dry Run First

```python
# Preview changes
dry_result = await manager.sync_all_persons(dry_run=True)
print(f"Will update {dry_result.operations_attempted} persons")

# Proceed if reasonable
if dry_result.operations_attempted < 1000:
    real_result = await manager.sync_all_persons()
```

### 2. Start with Limited Sync

```python
# Test with small subset first
test_result = await manager.sync_all_persons(limit=10)

if test_result.success:
    # Scale up to full sync
    full_result = await manager.sync_all_persons()
```

### 3. Monitor Performance

```python
result = await manager.sync_all_persons()

# Log performance metrics
logger.info(f"Sync performance:")
logger.info(f"  Operations/second: {result.operations_succeeded / result.execution_time_seconds:.2f}")
logger.info(f"  Success rate: {result.operations_succeeded / result.operations_attempted * 100:.1f}%")
```

### 4. Handle Errors Gracefully

```python
try:
    result = await manager.sync_all_persons()

    if not result.success:
        # Alert monitoring system
        send_alert(f"Sync failed: {result.errors}")

except Exception as e:
    logger.error(f"Fatal sync error: {e}")
    # Implement fallback or retry logic
```

### 5. Clean Up Resources

```python
try:
    manager = BundestagPersonManager(use_mock_dip=True)
    result = await manager.sync_all_persons()
finally:
    manager.close()  # Always clean up
```

## Next Steps

- **Architecture Overview**: See `docs/architecture/parallel-crud-architecture.md`
- **API Reference**: See `docs/api/bundestag-person-manager-api.md`
- **User Guide**: See `docs/guides/using-bundestag-person-manager.md`
- **CRUD Subagent**: See `docs/subagents/crud-subagent.md`
- **MCP Server**: See `docs/mcp/neo4j-crud-server.md`
