"""
Airflow DAG for orchestrating Kodosumi flows.
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta

import requests

# Add project root to path for imports - Airflow container paths
sys.path.insert(0, "/opt/airflow")

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

from src.etl.storage import get_storage

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


async def get_unprocessed_documents_async():
    """Get list of documents that haven't been processed by Flow 2."""
    storage = get_storage("local")

    # Get all markdown documents
    all_docs = await storage.list_documents()

    # TODO: Implement tracking of processed documents
    # For now, return all documents from today
    today = datetime.now().strftime("%Y-%m")
    unprocessed = [doc for doc in all_docs if doc.startswith(today)]

    return unprocessed


def check_for_new_documents(**context):
    """Check for new documents that need processing."""
    unprocessed_docs = asyncio.run(get_unprocessed_documents_async())

    # Store in XCom
    context["task_instance"].xcom_push(key="unprocessed_docs", value=unprocessed_docs)

    print(f"Found {len(unprocessed_docs)} unprocessed documents")
    return len(unprocessed_docs)


def trigger_flow2_kodosumi(**context):
    """Trigger Flow 2 via Kodosumi HTTP API."""
    unprocessed_docs = context["task_instance"].xcom_pull(key="unprocessed_docs")

    if not unprocessed_docs:
        print("No documents to process")
        return 0

    # Kodosumi endpoint for Flow 2 (when implemented)
    kodosumi_url = "http://localhost:3370/api/v1/flow2/add_company_context"

    # Prepare request payload
    payload = {"document_paths": unprocessed_docs, "batch_size": 10, "clear_existing": False}

    try:
        # Make HTTP request to Kodosumi
        # NOTE: This is a placeholder - Flow 2 needs to be implemented first
        print(f"Would trigger Flow 2 with {len(unprocessed_docs)} documents")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        # Uncomment when Flow 2 is ready:
        # response = requests.post(kodosumi_url, json=payload, timeout=300)
        # response.raise_for_status()
        # result = response.json()
        # print(f"Flow 2 triggered successfully: {result}")

        return len(unprocessed_docs)

    except Exception as e:
        print(f"Failed to trigger Flow 2: {e}")
        raise


def trigger_flow1_kodosumi(**context):
    """Trigger Flow 1 for document ingestion."""
    # This could be used to trigger Flow 1 after news collection
    # instead of running it manually

    kodosumi_url = "http://localhost:3370/api/v1/enter"

    payload = {"document_limit": 50, "clear_data": False, "build_communities": True}

    try:
        print(f"Triggering Flow 1 with payload: {json.dumps(payload, indent=2)}")

        # Make request to Kodosumi
        response = requests.post(kodosumi_url, json=payload, timeout=600)
        response.raise_for_status()

        result = response.json()
        print(f"Flow 1 triggered successfully: {result}")

        return True

    except Exception as e:
        print(f"Failed to trigger Flow 1: {e}")
        # Don't raise - Flow 1 might not be running
        return False


def update_processing_status(**context):
    """Update status of processed documents."""
    # TODO: Implement document processing status tracking
    # This could use a database table or metadata files

    unprocessed_docs = context["task_instance"].xcom_pull(key="unprocessed_docs")

    print(f"Would update processing status for {len(unprocessed_docs)} documents")

    # Placeholder for status tracking implementation
    # Could write to a status file or database

    return True


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
