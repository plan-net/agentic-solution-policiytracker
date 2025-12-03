"""
Airflow DAG for orchestrating Kodosumi flows.
"""

import json
import os
import sys
from datetime import timedelta

import requests

# Add project root to path for imports - Airflow container paths
sys.path.insert(0, "/opt/airflow")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Configuration from environment variables
FLOW1B_MAX_DOCUMENTS = int(os.getenv("FLOW1B_MAX_DOCUMENTS", "500"))

# Default arguments for the DAG
default_args = {
    "owner": "political-monitoring",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

# Create the DAG
dag = DAG(
    "flow_orchestration",
    default_args=default_args,
    description="Orchestrate Kodosumi flows for document processing",
    schedule_interval=None,  # Triggered by news_collection DAG
    catchup=False,
    tags=["etl", "flows", "kodosumi"],
)


def get_unprocessed_documents():
    """Get list of documents that haven't been processed by Flow 1."""
    import json
    from pathlib import Path

    # Read processed_documents.json directly without DocumentTracker
    tracking_file = Path("/opt/airflow/data/processed_documents.json")
    processed_docs = {}

    if tracking_file.exists():
        try:
            with open(tracking_file, encoding="utf-8") as f:
                processed_docs = json.load(f)
            print(f"Loaded {len(processed_docs)} processed documents from tracker")
        except Exception as e:
            print(f"Warning: Could not load tracking file: {e}")
            processed_docs = {}
    else:
        print("No tracking file found, treating all documents as unprocessed")

    # Get all markdown documents from news, policy, and website directories
    all_docs = []
    base_paths = [
        Path("/opt/airflow/data/input/news"),
        Path("/opt/airflow/data/input/policy"),
        Path("/opt/airflow/data/input/website"),
    ]

    for base_path in base_paths:
        if not base_path.exists():
            print(f"Warning: Base path {base_path} does not exist, skipping")
            continue

        # Find all markdown files in this directory
        for md_file in base_path.rglob("*.md"):
            # Get relative path from data/input (stored paths in tracker are relative)
            try:
                relative_path = str(md_file.relative_to(Path("/opt/airflow/data/input")))
                all_docs.append(relative_path)
            except ValueError:
                # Skip if file is not under data/input
                continue

    print(f"Found {len(all_docs)} total documents in storage")

    # Filter to only unprocessed documents
    unprocessed = [doc for doc in all_docs if doc not in processed_docs]

    print(f"Found {len(unprocessed)} unprocessed documents")
    return unprocessed


def check_for_new_documents(**context):
    """Check for new documents that need processing."""
    try:
        unprocessed_docs = get_unprocessed_documents()

        # Store COUNT only (Flow 1B will auto-detect files)
        context["task_instance"].xcom_push(key="unprocessed_count", value=len(unprocessed_docs))

        print(f"Found {len(unprocessed_docs)} unprocessed documents")
        if len(unprocessed_docs) > 500:
            print("⚠️  Exceeds 500 limit - Flow 1B will process first 500")

        return len(unprocessed_docs)
    except Exception as e:
        print(f"Error in check_for_new_documents: {e}")
        import traceback

        traceback.print_exc()
        # Return 0 on error
        context["task_instance"].xcom_push(key="unprocessed_count", value=0)
        return 0


def trigger_flow2_kodosumi(**context):
    """Trigger Flow 2 via Kodosumi HTTP API."""
    unprocessed_count = context["task_instance"].xcom_pull(key="unprocessed_count")

    if not unprocessed_count or unprocessed_count == 0:
        print("No documents to process")
        return 0

    # Kodosumi endpoint for Flow 2 (when implemented)
    kodosumi_url = "http://host.docker.internal:3370/api/v1/flow2/add_company_context"

    # Prepare request payload
    payload = {"max_documents": 500, "batch_size": 10, "clear_existing": False}

    try:
        # Make HTTP request to Kodosumi
        # NOTE: This is a placeholder - Flow 2 needs to be implemented first
        print(f"Would trigger Flow 2 with up to 500 documents (found {unprocessed_count})")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        # Uncomment when Flow 2 is ready:
        # response = requests.post(kodosumi_url, json=payload, timeout=300)
        # response.raise_for_status()
        # result = response.json()
        # print(f"Flow 2 triggered successfully: {result}")

        return min(unprocessed_count, 500)

    except Exception as e:
        print(f"Failed to trigger Flow 2: {e}")
        raise


def trigger_flow1_kodosumi(**context):
    """Trigger Flow 1B for auto-delta bulk document processing."""
    unprocessed_count = context["task_instance"].xcom_pull(key="unprocessed_count")

    if not unprocessed_count or unprocessed_count == 0:
        print("No unprocessed documents to trigger Flow 1B with")
        return False

    # Ray Serve endpoint for Flow 1B (via host.docker.internal for Docker networking)
    flow1b_url = "http://host.docker.internal:8001/data-ingestion-bulk-auto/"

    # Kodosumi-style payload - Flow 1B auto-detects files, no need to pass list
    payload = {
        "job_name": f"Airflow Auto Orchestration - {context['execution_date']}",
        "clear_data": False,
        "max_documents": FLOW1B_MAX_DOCUMENTS,  # Safety limit from environment variable
    }

    if unprocessed_count > FLOW1B_MAX_DOCUMENTS:
        print(
            f"⚠️  Found {unprocessed_count} unprocessed documents, will process first {FLOW1B_MAX_DOCUMENTS}"
        )

    try:
        print("Triggering Flow 1B with auto-delta detection")
        print(f"URL: {flow1b_url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        # Step 1: Get the form/result ID
        response1 = requests.post(flow1b_url, json=payload, timeout=30)
        response1.raise_for_status()
        result1 = response1.json()

        if "result" in result1:
            result_id = result1["result"]
            print(f"Got result ID: {result_id}")

            # Step 2: Submit to execute the job
            execute_url = f"{flow1b_url}{result_id}"
            print(f"Executing job at: {execute_url}")

            response2 = requests.post(execute_url, json=payload, timeout=600)
            response2.raise_for_status()
            result2 = response2.json()

            print(f"Flow 1B execution response: {result2}")
            return True
        else:
            print(f"Unexpected response format: {result1}")
            return False

    except Exception as e:
        print(f"Failed to trigger Flow 1B: {e}")
        import traceback

        traceback.print_exc()
        # Don't raise - Flow 1B might not be running
        return False


def update_processing_status(**context):
    """Update status of processed documents and report statistics."""
    import json
    from pathlib import Path

    # Read processed_documents.json directly (same fix as get_unprocessed_documents)
    tracking_file = Path("/opt/airflow/data/processed_documents.json")
    processed_docs = {}

    if tracking_file.exists():
        try:
            with open(tracking_file, encoding="utf-8") as f:
                processed_docs = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load tracking file: {e}")

    # Calculate statistics manually
    total_processed = len(processed_docs)
    completed = sum(1 for doc in processed_docs.values() if doc.get("status") == "completed")
    failed = sum(1 for doc in processed_docs.values() if doc.get("status") == "failed")
    total_entities = sum(doc.get("entity_count", 0) for doc in processed_docs.values())
    total_relationships = sum(doc.get("relationship_count", 0) for doc in processed_docs.values())
    success_rate = (completed / total_processed * 100) if total_processed > 0 else 0

    stats = {
        "total_processed": total_processed,
        "completed": completed,
        "failed": failed,
        "success_rate": success_rate,
        "total_entities": total_entities,
        "total_relationships": total_relationships,
    }

    print("=" * 80)
    print("Flow 1 Processing Status Report")
    print("=" * 80)
    print(f"Total processed documents: {stats['total_processed']}")
    print(f"Successfully completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    print(f"Total entities extracted: {stats['total_entities']}")
    print(f"Total relationships: {stats['total_relationships']}")

    # Report failed documents if any
    if stats["failed"] > 0:
        failed_docs = [
            {"path": path, "error": data.get("error", "Unknown error")}
            for path, data in processed_docs.items()
            if data.get("status") == "failed"
        ]
        print("\nFailed Documents:")
        for doc in failed_docs[:10]:  # Show first 10
            print(f"  - {doc['path']}: {doc['error']}")

    print("=" * 80)

    # Store stats in XCom for downstream tasks
    context["task_instance"].xcom_push(key="processing_stats", value=stats)

    return stats


# Define tasks
check_docs_task = PythonOperator(
    task_id="check_for_new_documents",
    python_callable=check_for_new_documents,
    dag=dag,
)

trigger_flow1_task = PythonOperator(
    task_id="trigger_flow1",
    python_callable=trigger_flow1_kodosumi,
    dag=dag,
)

trigger_flow2_task = PythonOperator(
    task_id="trigger_flow2",
    python_callable=trigger_flow2_kodosumi,
    dag=dag,
)

update_status_task = PythonOperator(
    task_id="update_processing_status",
    python_callable=update_processing_status,
    dag=dag,
)

# Set task dependencies
# Check for documents, then trigger flows in parallel, then update status
check_docs_task >> [trigger_flow1_task, trigger_flow2_task] >> update_status_task
