"""Demo script for BundestagAktivitaet Manager Skill.

This script demonstrates the complete workflow:
1. MCP Server operations for Aktivitaet
2. CRUD Subagent parallel execution
3. Manager Skill intelligent sync

Run with: uv run python scripts/demo_bundestag_aktivitaet_manager.py
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
    """Demo 1: MCP Server direct operations for Aktivitaet."""
    print("\n" + "=" * 80)
    print("DEMO 1: MCP Server - Direct CRUD Operations for Aktivitaet")
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

            # Create Aktivitaet node
            print("\n2. Create Aktivitaet Node")
            create_payload = {
                "entity_type": "Aktivitaet",
                "properties": {
                    "aktivitaet_id": "demo_test_aktivitaet_001",
                    "titel": "Demo Rede zur Digitalisierung",
                    "aktivitaetsart": "Rede",
                    "datum": "2024-03-15",
                    "wahlperiode": 20,
                    "person_name": "Test Person",
                    "active": True,
                },
            }
            response = await client.post(f"{mcp_url}/create_node", json=create_payload)
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message')}")

            # Update Aktivitaet node
            print("\n3. Update Aktivitaet Node")
            update_payload = {
                "entity_type": "Aktivitaet",
                "node_id": "demo_test_aktivitaet_001",
                "properties": {"aktivitaetsart": "Abstimmung"},
            }
            response = await client.post(f"{mcp_url}/update_node", json=update_payload)
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(f"   Message: {result.get('message')}")

            # Query Aktivitaet nodes
            print("\n4. Query Aktivitaet Nodes")
            query_payload = {
                "entity_type": "Aktivitaet",
                "filters": {"aktivitaetsart": "Rede"},
                "limit": 10,
            }
            response = await client.post(f"{mcp_url}/query_nodes", json=query_payload)
            result = response.json()
            print(f"   Success: {result.get('success')}")
            print(
                f"   Found: {result.get('returned_count')} of {result.get('total_count')}"
            )

            # Delete node (soft)
            print("\n5. Delete Aktivitaet Node (Soft)")
            delete_payload = {
                "entity_type": "Aktivitaet",
                "node_id": "demo_test_aktivitaet_001",
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
    """Demo 2: CRUD Subagent parallel execution for Aktivitaet."""
    print("\n" + "=" * 80)
    print("DEMO 2: CRUD Subagent - Parallel Execution for Aktivitaet")
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
        print("\n2. Execute Single Aktivitaet Operation")
        single_op = {
            "operation": "create_node",
            "entity_type": "Aktivitaet",
            "properties": {
                "aktivitaet_id": "demo_single_aktivitaet_001",
                "titel": "Einzelner Test Aktivitaet",
                "aktivitaetsart": "Anfrage",
                "datum": "2024-02-20",
                "wahlperiode": 20,
                "active": True,
            },
        }
        result = await subagent.execute_operation(single_op)
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print(f"   Execution time: {result.execution_time_ms:.2f}ms")

        # Parallel execution (20 operations)
        print("\n3. Execute 20 Aktivitaet Operations in Parallel")
        parallel_ops = []
        for i in range(20):
            parallel_ops.append(
                {
                    "operation": "create_node",
                    "entity_type": "Aktivitaet",
                    "properties": {
                        "aktivitaet_id": f"demo_parallel_aktivitaet_{i:03d}",
                        "titel": f"Parallel Aktivitaet {i}",
                        "aktivitaetsart": "Rede",
                        "datum": "2024-03-10",
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
                    "entity_type": "Aktivitaet",
                    "node_id": f"demo_parallel_aktivitaet_{i:03d}",
                    "hard_delete": True,
                }
            )
        cleanup_ops.append(
            {
                "operation": "delete_node",
                "entity_type": "Aktivitaet",
                "node_id": "demo_single_aktivitaet_001",
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
    """Demo 3: Manager Skill intelligent sync for Aktivitaet."""
    print("\n" + "=" * 80)
    print("DEMO 3: Manager Skill - Intelligent Aktivitaet Sync")
    print("=" * 80)

    try:
        from src.skills.bundestag_aktivitaet_manager import BundestagAktivitaetManager

        # Initialize manager with mock DIP client
        print("\n1. Initialize Aktivitaet Manager (Mock DIP Client)")
        manager = BundestagAktivitaetManager(use_mock_dip=True)
        print("   ✅ Manager initialized")

        # Check sync status
        print("\n2. Check Aktivitaet Sync Status")
        status = await manager.check_sync_status()
        print(f"   Status: {status['status']}")
        print(f"   Total differences: {status['total_differences']}")
        print(f"   Missing Aktivitaetn: {status['missing_aktivitaeten']}")
        print(f"   Outdated Aktivitaetn: {status['outdated_aktivitaeten']}")

        if status["total_differences"] > 0:
            print(
                f"   Most changed fields: {status.get('most_changed_fields', {})}"
            )

            # Dry run to preview changes
            print("\n3. Dry Run (Preview Changes)")
            dry_result = await manager.sync_all_aktivitaeten(dry_run=True)
            print(f"   Would update: {dry_result.operations_attempted} operations")
            print(f"   Missing: {dry_result.diff_summary.get('missing_count', 0)}")
            print(f"   Outdated: {dry_result.diff_summary.get('outdated_count', 0)}")

            # Actual sync
            print("\n4. Perform Aktivitaet Sync")
            sync_result = await manager.sync_all_aktivitaeten()
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

        # Specific Aktivitaet sync
        print("\n5. Sync Specific Aktivitaetn")
        specific_result = await manager.sync_specific_aktivitaeten(
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
    print("BundestagAktivitaet Manager - Complete Demo")
    print("=" * 80)
    print(
        "\nThis demo will test the complete CRUD system for Aktivitaet:"
    )
    print("  1. MCP Server - Direct database operations for Aktivitaet")
    print("  2. CRUD Subagent - Parallel execution with Ray")
    print("  3. Manager Skill - Intelligent Aktivitaet data synchronization")
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
    print("  1. Review Aktivitaet documentation in docs/")
    print("  2. Check logs for detailed execution traces")
    print("  3. Monitor Neo4j at http://localhost:7474")
    print("  4. View Ray dashboard at http://localhost:8265")
    print("\n✅ All Aktivitaet demos completed successfully!")


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
