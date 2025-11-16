"""Demo script for BundestagDrucksache Manager Skill.

This script demonstrates the complete workflow:
1. MCP Server operations for Drucksache
2. CRUD Subagent parallel execution
3. Manager Skill intelligent sync

Run with: uv run python scripts/demo_bundestag_drucksache_manager.py
"""
import asyncio
import logging
import sys
from datetime import datetime

import ray

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_mcp_server():
    """Demo 1: MCP Server direct operations for Drucksache."""
    print("\n" + "=" * 80)
    print("DEMO 1: MCP Server - Direct CRUD Operations for Drucksache")
    print("=" * 80)

    import httpx

    mcp_url = "http://localhost:8002"

    try:
        async with httpx.AsyncClient() as client:
            # Health check
            print("\n1. Health Check")
            response = await client.get(f"{mcp_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")

            # Create Drucksache node
            print("\n2. Create Drucksache Node")
            create_payload = {
                "entity_type": "Drucksache",
                "properties": {
                    "drucksache_nummer": "demo_test_drucksache_001",
                    "titel": "Demo Gesetz zur Digitalisierung",
                    "drucksachestyp": "Gesetzgebung",
                    "beratungsstand": "In Beratung",
                    "wahlperiode": 20,
                    "active": True,
                },
            }
            response = await client.post(f"{mcp_url}/create_node", json=create_payload)
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message')}")

            # Update Drucksache node
            print("\n3. Update Drucksache Node")
            update_payload = {
                "entity_type": "Drucksache",
                "node_id": "demo_test_drucksache_001",
                "properties": {"beratungsstand": "Abgeschlossen"},
            }
            response = await client.post(f"{mcp_url}/update_node", json=update_payload)
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message')}")

            # Query Drucksache nodes
            print("\n4. Query Drucksache Nodes")
            query_payload = {
                "entity_type": "Drucksache",
                "filters": {"drucksachestyp": "Gesetzgebung"},
                "limit": 10,
            }
            response = await client.post(f"{mcp_url}/query_nodes", json=query_payload)
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(
                f"   Found: {result.get('returned_count')} of {result.get('total_count')}"
            )

            # Delete node (soft)
            print("\n5. Delete Drucksache Node (Soft)")
            delete_payload = {
                "entity_type": "Drucksache",
                "node_id": "demo_test_drucksache_001",
                "hard_delete": False,
            }
            response = await client.post(f"{mcp_url}/delete_node", json=delete_payload)
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message')}")

            print("\n✅ MCP Server demo complete!")

    except Exception as e:
        print(f"\n❌ MCP Server demo failed: {e}")
        print("   Make sure MCP server is running: docker compose up neo4j-crud-mcp -d")


async def demo_crud_subagent():
    """Demo 2: CRUD Subagent parallel execution for Drucksache."""
    print("\n" + "=" * 80)
    print("DEMO 2: CRUD Subagent - Parallel Execution for Drucksache")
    print("=" * 80)

    try:
        from src.subagents.crud_subagent import CRUDSubagent

        # Initialize subagent with 5 actors for demo
        print("\n1. Initialize CRUD Subagent (5 actors)")
        subagent = CRUDSubagent(
            mcp_url="http://localhost:8002", num_replicas=5
        )
        subagent.start()
        print("   ✅ Subagent started with 5 actors")

        # Single operation
        print("\n2. Execute Single Drucksache Operation")
        single_op = {
            "operation": "create_node",
            "entity_type": "Drucksache",
            "properties": {
                "drucksache_nummer": "demo_single_drucksache_001",
                "titel": "Einzelner Test Drucksache",
                "drucksachestyp": "Antrag",
                "beratungsstand": "In Beratung",
                "wahlperiode": 20,
                "active": True,
            },
        }
        result = await subagent.execute_operation(single_op)
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print(f"   Execution time: {result.execution_time_ms:.2f}ms")

        # Parallel execution (20 operations)
        print("\n3. Execute 20 Drucksache Operations in Parallel")
        parallel_ops = []
        for i in range(20):
            parallel_ops.append(
                {
                    "operation": "create_node",
                    "entity_type": "Drucksache",
                    "properties": {
                        "drucksache_nummer": f"demo_parallel_drucksache_{i:03d}",
                        "titel": f"Parallel Drucksache {i}",
                        "drucksachestyp": "Gesetzgebung",
                        "beratungsstand": "In Beratung",
                        "wahlperiode": 20,
                        "active": True,
                    },
                }
            )

        start_time = datetime.now()
        results = await subagent.execute_parallel(parallel_ops)
        end_time = datetime.now()

        elapsed = (end_time - start_time).total_seconds()
        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        print(f"   Total operations: {len(results)}")
        print(f"   Succeeded: {succeeded}")
        print(f"   Failed: {failed}")
        print(f"   Total time: {elapsed:.2f}s")
        print(
            f"   Avg time per operation: {sum(r.execution_time_ms for r in results) / len(results):.2f}ms"
        )

        # Get statistics
        print("\n4. Pool Statistics")
        stats = await subagent.get_pool_statistics()
        print(f"   Total actors: {stats['total_actors']}")
        print(f"   Total operations: {stats['total_operations']}")
        print(f"   Success rate: {stats['overall_success_rate']:.1f}%")

        # Cleanup
        print("\n5. Cleanup Test Data")
        cleanup_ops = []
        for i in range(20):
            cleanup_ops.append(
                {
                    "operation": "delete_node",
                    "entity_type": "Drucksache",
                    "node_id": f"demo_parallel_drucksache_{i:03d}",
                    "hard_delete": True,
                }
            )
        cleanup_ops.append(
            {
                "operation": "delete_node",
                "entity_type": "Drucksache",
                "node_id": "demo_single_drucksache_001",
                "hard_delete": True,
            }
        )
        cleanup_results = await subagent.execute_parallel(cleanup_ops)
        cleaned = sum(1 for r in cleanup_results if r.success)
        print(f"   Cleaned up {cleaned} test nodes")

        subagent.stop()
        print("\n✅ CRUD Subagent demo complete!")

    except Exception as e:
        print(f"\n❌ CRUD Subagent demo failed: {e}")
        print("   Make sure Ray is running: ray start --head")


async def demo_manager_skill():
    """Demo 3: Manager Skill intelligent sync for Drucksache."""
    print("\n" + "=" * 80)
    print("DEMO 3: Manager Skill - Intelligent Drucksache Sync")
    print("=" * 80)

    try:
        from src.skills.bundestag_drucksache_manager import BundestagDrucksacheManager

        # Initialize manager with mock DIP client
        print("\n1. Initialize Drucksache Manager (Mock DIP Client)")
        manager = BundestagDrucksacheManager(use_mock_dip=True)
        print("   ✅ Manager initialized")

        # Check sync status
        print("\n2. Check Drucksache Sync Status")
        status = await manager.check_sync_status()
        print(f"   Status: {status['status']}")
        print(f"   Total differences: {status['total_differences']}")
        print(f"   Missing Drucksachen: {status['missing_drucksachen']}")
        print(f"   Outdated Drucksachen: {status['outdated_drucksachen']}")

        if status["total_differences"] > 0:
            print(
                f"   Most changed fields: {status.get('most_changed_fields', {})}"
            )

            # Dry run to preview changes
            print("\n3. Dry Run (Preview Changes)")
            dry_result = await manager.sync_all_drucksachen(dry_run=True)
            print(f"   Would update: {dry_result.operations_attempted} operations")
            print(f"   Missing: {dry_result.diff_summary.get('missing_count', 0)}")
            print(f"   Outdated: {dry_result.diff_summary.get('outdated_count', 0)}")

            # Actual sync
            print("\n4. Perform Drucksache Sync")
            sync_result = await manager.sync_all_drucksachen()
            print(f"   Success: {sync_result.success}")
            print(
                f"   Operations: {sync_result.operations_succeeded}/{sync_result.operations_attempted}"
            )
            print(f"   Execution time: {sync_result.execution_time_seconds:.2f}s")
            if sync_result.operations_failed > 0:
                print(f"   Failed: {sync_result.operations_failed}")
                print(f"   Errors: {sync_result.errors}")

        else:
            print("\n   ✅ Database is already up to date!")

        # Specific Drucksache sync
        print("\n5. Sync Specific Drucksachen")
        specific_result = await manager.sync_specific_drucksachen(
            ["287654", "289123"]
        )
        print(f"   Operations: {specific_result.operations_succeeded}")
        print(f"   Time: {specific_result.execution_time_seconds:.2f}s")

        manager.close()
        print("\n✅ Manager Skill demo complete!")

    except Exception as e:
        print(f"\n❌ Manager Skill demo failed: {e}")
        import traceback

        traceback.print_exc()


async def run_all_demos():
    """Run all demos in sequence."""
    print("\n" + "=" * 80)
    print("BundestagDrucksache Manager - Complete Demo")
    print("=" * 80)
    print(
        "\nThis demo will test the complete CRUD system for Drucksache:"
    )
    print("  1. MCP Server - Direct database operations for Drucksache")
    print("  2. CRUD Subagent - Parallel execution with Ray")
    print("  3. Manager Skill - Intelligent Drucksache data synchronization")
    print("\n" + "=" * 80)

    # Initialize Ray
    if not ray.is_initialized():
        print("\nInitializing Ray...")
        ray.init(ignore_reinit_error=True)
        print("✅ Ray initialized")

    # Run demos
    await demo_mcp_server()
    await demo_crud_subagent()
    await demo_manager_skill()

    # Summary
    print("\n" + "=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("  1. Review Drucksache documentation in docs/")
    print("  2. Check logs for detailed execution traces")
    print("  3. Monitor Neo4j at http://localhost:7474")
    print("  4. View Ray dashboard at http://localhost:8265")
    print("\n✅ All Drucksache demos completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_demos())
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
