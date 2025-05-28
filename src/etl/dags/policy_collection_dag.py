"""
Policy Collection DAG for Apache Airflow

Orchestrates collection of policy and regulatory documents using
targeted search queries based on client context.

Schedule: Weekly (Sundays at 2 AM UTC)
Purpose: Flow 1 - Policy Landscape Analysis
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable

# ETL imports
from src.etl.collectors.policy_landscape import PolicyLandscapeCollector
from src.etl.storage.local import LocalStorageClient
from src.etl.storage.azure import AzureStorageClient
from src.etl.utils.initialization_tracker import ETLInitializationTracker
from src.etl.utils.config_loader import load_etl_config

logger = logging.getLogger(__name__)

# DAG Configuration
DAG_ID = 'policy_collection_dag'
DESCRIPTION = 'Collect policy and regulatory documents for Flow 1 analysis'

# Default arguments
default_args = {
    'owner': 'political-monitoring-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
    'catchup': False,
}

# Create DAG
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule_interval='0 2 * * 0',  # Weekly: Sundays at 2 AM UTC
    max_active_runs=1,
    tags=['etl', 'policy', 'collection', 'flow1'],
)


def load_policy_config() -> Dict[str, Any]:
    """Load and validate policy collection configuration."""
    try:
        # Load base ETL config
        base_config = load_etl_config()
        
        # Policy-specific configuration
        policy_config = {
            'exa_api_key': os.getenv('EXA_API_KEY'),
            'client_context_path': os.getenv('CLIENT_CONTEXT_PATH', 'data/context/client.yaml'),
            'storage_type': os.getenv('STORAGE_TYPE', 'local'),
            'collection_days': int(os.getenv('POLICY_COLLECTION_DAYS', '7')),
            'max_results_per_query': int(os.getenv('POLICY_MAX_RESULTS_PER_QUERY', '10')),
            'max_concurrent_queries': int(os.getenv('POLICY_MAX_CONCURRENT_QUERIES', '3')),
            'initialization_days': int(os.getenv('POLICY_INITIALIZATION_DAYS', '90')),
        }
        
        # Merge configurations
        config = {**base_config, **policy_config}
        
        # Validate required fields
        required_fields = ['exa_api_key', 'client_context_path']
        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Missing required configuration: {field}")
        
        logger.info("Policy collection configuration loaded successfully")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load policy configuration: {e}")
        raise


def check_policy_initialization(**context) -> Dict[str, Any]:
    """Check if policy collection has been initialized."""
    try:
        config = load_policy_config()
        tracker = ETLInitializationTracker('policy_landscape')
        
        is_initialized = tracker.is_initialized()
        collection_days = tracker.get_collection_days(
            initialization_days=config['initialization_days'],
            daily_days=config['collection_days']
        )
        
        initialization_info = {
            'is_initialized': is_initialized,
            'collection_days': collection_days,
            'collection_type': 'initialization' if not is_initialized else 'regular',
            'config': config
        }
        
        logger.info(
            f"Policy initialization check: {'✅ Initialized' if is_initialized else '🚀 First run'} "
            f"(collecting {collection_days} days)"
        )
        
        # Store in XCom for downstream tasks
        context['task_instance'].xcom_push(
            key='initialization_info',
            value=initialization_info
        )
        
        return initialization_info
        
    except Exception as e:
        logger.error(f"Policy initialization check failed: {e}")
        raise


def collect_policy_documents(**context) -> Dict[str, Any]:
    """Main policy collection task."""
    try:
        # Get initialization info from upstream task
        initialization_info = context['task_instance'].xcom_pull(
            task_ids='check_policy_initialization',
            key='initialization_info'
        )
        
        config = initialization_info['config']
        collection_days = initialization_info['collection_days']
        
        logger.info(
            f"Starting policy collection: {collection_days} days "
            f"({initialization_info['collection_type']} mode)"
        )
        
        # Initialize storage client
        storage_client = None
        if config['storage_type'] == 'azure':
            storage_client = AzureStorageClient(
                connection_string=config.get('azure_connection_string'),
                container_prefix=config.get('azure_container_prefix', 'policytracker')
            )
        else:
            storage_client = LocalStorageClient(
                base_path=config.get('local_storage_path', 'data')
            )
        
        # Initialize policy collector
        collector = PolicyLandscapeCollector(
            exa_api_key=config['exa_api_key'],
            client_context_path=config['client_context_path'],
            storage_client=storage_client
        )
        
        # Execute collection
        collection_result = None
        
        async def run_collection():
            return await collector.collect_policy_documents(
                days_back=collection_days,
                max_results_per_query=config['max_results_per_query'],
                max_concurrent_queries=config['max_concurrent_queries']
            )
        
        import asyncio
        collection_result = asyncio.run(run_collection())
        
        # Enhance result with metadata
        collection_result.update({
            'dag_id': DAG_ID,
            'task_id': 'collect_policy_documents',
            'execution_date': context['execution_date'].isoformat(),
            'collection_days': collection_days,
            'collection_type': initialization_info['collection_type'],
            'is_initialization': not initialization_info['is_initialized']
        })
        
        logger.info(
            f"Policy collection completed: {collection_result['documents_saved']} documents "
            f"saved in {collection_result['processing_time_seconds']:.1f}s"
        )
        
        # Store result in XCom
        context['task_instance'].xcom_push(
            key='collection_result',
            value=collection_result
        )
        
        return collection_result
        
    except Exception as e:
        logger.error(f"Policy collection failed: {e}")
        raise


def mark_policy_initialization_complete(**context) -> Dict[str, Any]:
    """Mark policy collection as initialized if this was the first run."""
    try:
        # Get collection result
        collection_result = context['task_instance'].xcom_pull(
            task_ids='collect_policy_documents',
            key='collection_result'
        )
        
        if not collection_result:
            raise ValueError("No collection result found")
        
        # Mark as initialized if this was an initialization run
        if collection_result.get('is_initialization', False):
            tracker = ETLInitializationTracker('policy_landscape')
            tracker.mark_initialized()
            
            logger.info("✅ Policy collection initialization completed and marked")
            
            return {
                'action': 'marked_initialized',
                'collector': 'policy_landscape',
                'timestamp': datetime.now().isoformat(),
                'documents_collected': collection_result.get('documents_saved', 0)
            }
        else:
            logger.info("ℹ️ Regular collection run, no initialization marking needed")
            
            return {
                'action': 'no_action_needed',
                'collector': 'policy_landscape',
                'reason': 'already_initialized'
            }
    
    except Exception as e:
        logger.error(f"Failed to mark policy initialization: {e}")
        raise


def generate_policy_collection_summary(**context) -> Dict[str, Any]:
    """Generate summary of policy collection run."""
    try:
        # Get all task results
        initialization_info = context['task_instance'].xcom_pull(
            task_ids='check_policy_initialization',
            key='initialization_info'
        )
        
        collection_result = context['task_instance'].xcom_pull(
            task_ids='collect_policy_documents',
            key='collection_result'
        )
        
        if not collection_result:
            raise ValueError("No collection result found for summary")
        
        # Generate comprehensive summary
        summary = {
            'dag_run_summary': {
                'dag_id': DAG_ID,
                'execution_date': context['execution_date'].isoformat(),
                'run_type': initialization_info['collection_type'],
                'collection_days': initialization_info['collection_days'],
                'total_runtime_seconds': collection_result['processing_time_seconds']
            },
            'collection_metrics': {
                'queries_processed': collection_result['queries_processed'],
                'queries_failed': collection_result['queries_failed'],
                'total_articles_found': collection_result['total_articles_found'],
                'documents_saved': collection_result['documents_saved'],
                'categories_covered': collection_result['categories_covered']
            },
            'quality_indicators': {
                'success_rate': (
                    (collection_result['queries_processed'] - collection_result['queries_failed']) 
                    / max(collection_result['queries_processed'], 1)
                ),
                'documents_per_query': (
                    collection_result['documents_saved'] 
                    / max(collection_result['queries_processed'], 1)
                ),
                'processing_speed_docs_per_minute': (
                    collection_result['documents_saved'] * 60 
                    / max(collection_result['processing_time_seconds'], 1)
                )
            },
            'sample_data': {
                'failed_queries': collection_result.get('failed_queries', []),
                'sample_documents': collection_result.get('sample_documents', [])
            },
            'next_steps': {
                'next_scheduled_run': 'Next Sunday 2 AM UTC',
                'recommended_actions': _get_recommended_actions(collection_result)
            }
        }
        
        # Log summary
        logger.info(f"📊 Policy Collection Summary:")
        logger.info(f"  • Documents saved: {summary['collection_metrics']['documents_saved']}")
        logger.info(f"  • Success rate: {summary['quality_indicators']['success_rate']:.1%}")
        logger.info(f"  • Processing speed: {summary['quality_indicators']['processing_speed_docs_per_minute']:.1f} docs/min")
        
        # Store summary
        context['task_instance'].xcom_push(key='dag_summary', value=summary)
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to generate policy collection summary: {e}")
        raise


def _get_recommended_actions(collection_result: Dict[str, Any]) -> list:
    """Generate recommended actions based on collection results."""
    actions = []
    
    # Check for high failure rate
    queries_processed = collection_result.get('queries_processed', 0)
    queries_failed = collection_result.get('queries_failed', 0)
    
    if queries_processed > 0:
        failure_rate = queries_failed / queries_processed
        if failure_rate > 0.2:  # >20% failure rate
            actions.append(f"High query failure rate ({failure_rate:.1%}). Check API limits and query validity.")
    
    # Check for low document yield
    documents_saved = collection_result.get('documents_saved', 0)
    if documents_saved < 10:
        actions.append("Low document yield. Consider expanding search queries or increasing time range.")
    
    # Check processing speed
    processing_time = collection_result.get('processing_time_seconds', 0)
    if processing_time > 300:  # >5 minutes
        actions.append("Slow processing detected. Consider reducing concurrent queries or batch sizes.")
    
    if not actions:
        actions.append("Collection performed well. No immediate actions needed.")
    
    return actions


# Define tasks
check_initialization_task = PythonOperator(
    task_id='check_policy_initialization',
    python_callable=check_policy_initialization,
    dag=dag,
    doc_md="""
    **Check Policy Collection Initialization**
    
    Determines if this is the first run (initialization) or regular collection.
    Sets collection timeframe accordingly.
    """,
)

collect_documents_task = PythonOperator(
    task_id='collect_policy_documents',
    python_callable=collect_policy_documents,
    dag=dag,
    doc_md="""
    **Collect Policy Documents**
    
    Main collection task that:
    1. Generates targeted policy search queries from client context
    2. Executes searches via Exa API
    3. Transforms and saves documents to storage
    """,
)

mark_initialization_task = PythonOperator(
    task_id='mark_policy_initialization_complete',
    python_callable=mark_policy_initialization_complete,
    dag=dag,
    doc_md="""
    **Mark Initialization Complete**
    
    Marks the policy collector as initialized if this was the first run.
    Subsequent runs will use daily collection timeframe.
    """,
)

generate_summary_task = PythonOperator(
    task_id='generate_policy_collection_summary',
    python_callable=generate_policy_collection_summary,
    dag=dag,
    doc_md="""
    **Generate Collection Summary**
    
    Creates comprehensive summary of the collection run including:
    - Collection metrics and success rates
    - Quality indicators and recommendations
    - Sample data and next steps
    """,
)

# Set task dependencies
check_initialization_task >> collect_documents_task >> mark_initialization_task >> generate_summary_task

# Export DAG
globals()[DAG_ID] = dag