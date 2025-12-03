"""
Entity Deduplication DAG for Apache Airflow

Orchestrates automated entity deduplication and consolidation in the Neo4j
knowledge graph using fuzzy string matching and relationship merging.

Schedule: Weekly (Sundays at 3 AM UTC - after policy collection)
Purpose: Phase 1 Deduplication Strategy - Post-Processing Cleanup
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator

logger = logging.getLogger(__name__)

# DAG Configuration
DAG_ID = "entity_deduplication_weekly"
DESCRIPTION = "Weekly entity deduplication and consolidation for knowledge graph cleanup"

# Default arguments
default_args = {
    "owner": "political-monitoring-team",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "catchup": False,
}

# Create DAG
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description=DESCRIPTION,
    schedule_interval="0 3 * * 0",  # Weekly: Sundays at 3 AM UTC (1 hour after policy collection)
    max_active_runs=1,
    tags=["deduplication", "maintenance", "knowledge-graph", "weekly"],
)


def load_deduplication_config() -> dict[str, Any]:
    """Load and validate deduplication configuration."""
    try:
        config = {
            # Neo4j connection
            "neo4j_uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            "neo4j_user": os.getenv("NEO4J_USER", "neo4j"),
            "neo4j_password": os.getenv("NEO4J_PASSWORD", "password123"),
            "neo4j_database": os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3"),
            # Consolidation settings
            "similarity_threshold": float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.85")),
            "auto_confirm": os.getenv("DEDUP_AUTO_CONFIRM", "false").lower() == "true",
            "entity_types": os.getenv(
                "DEDUP_ENTITY_TYPES", "Policy,Regulation,Politician,Organization,Company"
            ).split(","),
            # Script paths
            "consolidation_script_path": os.path.join(
                os.getcwd(), "scripts", "consolidate_duplicate_entities.py"
            ),
            # Reporting
            "report_output_dir": os.getenv("DEDUP_REPORT_DIR", "data/reports/deduplication"),
        }

        # Validate required fields
        required_fields = ["neo4j_uri", "neo4j_user", "neo4j_password", "consolidation_script_path"]
        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Missing required configuration: {field}")

        logger.info("Deduplication configuration loaded successfully")
        return config

    except Exception as e:
        logger.error(f"Failed to load deduplication configuration: {e}")
        raise


def check_apoc_availability(**context) -> dict[str, Any]:
    """Check if APOC plugin is available in Neo4j."""
    try:
        from neo4j import GraphDatabase

        config = load_deduplication_config()

        driver = GraphDatabase.driver(
            config["neo4j_uri"], auth=(config["neo4j_user"], config["neo4j_password"])
        )

        with driver.session(database=config["neo4j_database"]) as session:
            # Test APOC availability
            result = session.run("RETURN apoc.version() AS version")
            apoc_info = result.single()

            if apoc_info:
                apoc_version = apoc_info["version"]
                logger.info(f"✅ APOC plugin available: version {apoc_version}")

                check_result = {
                    "apoc_available": True,
                    "apoc_version": apoc_version,
                    "neo4j_uri": config["neo4j_uri"],
                    "neo4j_database": config["neo4j_database"],
                    "config": config,
                }
            else:
                raise RuntimeError("APOC plugin returned no version")

        driver.close()

        # Store in XCom
        context["task_instance"].xcom_push(key="apoc_check", value=check_result)

        return check_result

    except Exception as e:
        logger.error(f"APOC availability check failed: {e}")
        logger.error(
            "APOC plugin is required for entity deduplication. "
            "Please install APOC in Neo4j before running this DAG."
        )
        raise


def run_dry_run_consolidation(**context) -> dict[str, Any]:
    """Run consolidation script in dry-run mode to preview duplicates."""
    try:
        # Get config from upstream task
        apoc_check = context["task_instance"].xcom_pull(
            task_ids="check_apoc_availability", key="apoc_check"
        )

        config = apoc_check["config"]

        logger.info(
            f"Starting dry-run consolidation with similarity threshold: {config['similarity_threshold']}"
        )

        # Build command
        cmd = [
            "python",
            config["consolidation_script_path"],
            "--dry-run",
            "--similarity",
            str(config["similarity_threshold"]),
        ]

        # Add entity type filter if specified
        if config.get("entity_types"):
            cmd.extend(["--entity-types", ",".join(config["entity_types"])])

        # Set environment variables for Neo4j connection
        env = os.environ.copy()
        env.update(
            {
                "NEO4J_URI": config["neo4j_uri"],
                "NEO4J_USER": config["neo4j_user"],
                "NEO4J_PASSWORD": config["neo4j_password"],
                "NEO4J_DATABASE": config["neo4j_database"],
            }
        )

        # Run dry-run
        logger.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=300)

        if result.returncode != 0:
            raise RuntimeError(f"Dry-run failed: {result.stderr}")

        # Parse output to extract statistics
        dry_run_output = result.stdout
        duplicates_found = _parse_duplicates_count(dry_run_output)

        dry_run_result = {
            "duplicates_found": duplicates_found,
            "output": dry_run_output,
            "similarity_threshold": config["similarity_threshold"],
            "entity_types": config["entity_types"],
            "execution_timestamp": datetime.now().isoformat(),
        }

        logger.info(f"✅ Dry-run completed: {duplicates_found} duplicate pairs found")

        # Store result
        context["task_instance"].xcom_push(key="dry_run_result", value=dry_run_result)

        # Save report to file
        _save_dry_run_report(dry_run_result, config)

        return dry_run_result

    except subprocess.TimeoutExpired:
        logger.error("Dry-run consolidation timed out after 5 minutes")
        raise
    except Exception as e:
        logger.error(f"Dry-run consolidation failed: {e}")
        raise


def _parse_duplicates_count(output: str) -> int:
    """Parse duplicate count from consolidation script output."""
    try:
        # Look for "Found N potential duplicate pairs"
        import re

        match = re.search(r"Found (\d+) potential duplicate pairs", output)
        if match:
            return int(match.group(1))

        # Look for "Would merge N duplicate entities"
        match = re.search(r"Would merge (\d+) duplicate entities", output)
        if match:
            return int(match.group(1))

        return 0
    except Exception:
        return 0


def _save_dry_run_report(dry_run_result: dict[str, Any], config: dict[str, Any]) -> None:
    """Save dry-run report to file."""
    try:
        from pathlib import Path

        # Ensure report directory exists
        report_dir = Path(config["report_output_dir"])
        report_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"deduplication_dry_run_{timestamp}.txt"

        # Write report
        with open(report_file, "w") as f:
            f.write("Entity Deduplication Dry-Run Report\n")
            f.write(f"{'=' * 60}\n\n")
            f.write(f"Execution Timestamp: {dry_run_result['execution_timestamp']}\n")
            f.write(f"Similarity Threshold: {dry_run_result['similarity_threshold']}\n")
            f.write(f"Entity Types: {', '.join(dry_run_result['entity_types'])}\n")
            f.write(f"Duplicates Found: {dry_run_result['duplicates_found']}\n\n")
            f.write(f"{'=' * 60}\n\n")
            f.write(dry_run_result["output"])

        logger.info(f"📄 Dry-run report saved: {report_file}")

    except Exception as e:
        logger.warning(f"Failed to save dry-run report: {e}")


def check_consolidation_threshold(**context) -> str:
    """Check if consolidation should proceed based on duplicates found."""
    try:
        # Get dry-run result
        dry_run_result = context["task_instance"].xcom_pull(
            task_ids="run_dry_run_consolidation", key="dry_run_result"
        )

        duplicates_found = dry_run_result.get("duplicates_found", 0)

        # Get config
        apoc_check = context["task_instance"].xcom_pull(
            task_ids="check_apoc_availability", key="apoc_check"
        )
        config = apoc_check["config"]

        # Decision logic
        if duplicates_found == 0:
            logger.info("✅ No duplicates found. Skipping live consolidation.")
            return "generate_summary_no_duplicates"

        elif config.get("auto_confirm", False):
            logger.info(
                f"✅ Auto-confirm enabled. Will consolidate {duplicates_found} duplicate pairs."
            )
            return "run_live_consolidation"

        else:
            logger.info(
                f"ℹ️  {duplicates_found} duplicates found, but auto-confirm disabled. "
                f"Skipping live consolidation. Review dry-run report and run manually if needed."
            )
            return "generate_summary_manual_review"

    except Exception as e:
        logger.error(f"Failed to check consolidation threshold: {e}")
        raise


def run_live_consolidation(**context) -> dict[str, Any]:
    """Run live consolidation to merge duplicate entities."""
    try:
        # Get config
        apoc_check = context["task_instance"].xcom_pull(
            task_ids="check_apoc_availability", key="apoc_check"
        )
        config = apoc_check["config"]

        # Get dry-run result for context
        dry_run_result = context["task_instance"].xcom_pull(
            task_ids="run_dry_run_consolidation", key="dry_run_result"
        )

        logger.info(
            f"Starting live consolidation of {dry_run_result['duplicates_found']} duplicates"
        )

        # Build command (no --dry-run flag)
        cmd = [
            "python",
            config["consolidation_script_path"],
            "--similarity",
            str(config["similarity_threshold"]),
        ]

        # Add entity type filter if specified
        if config.get("entity_types"):
            cmd.extend(["--entity-types", ",".join(config["entity_types"])])

        # Set environment variables
        env = os.environ.copy()
        env.update(
            {
                "NEO4J_URI": config["neo4j_uri"],
                "NEO4J_USER": config["neo4j_user"],
                "NEO4J_PASSWORD": config["neo4j_password"],
                "NEO4J_DATABASE": config["neo4j_database"],
                "AUTO_CONFIRM": "true",  # Auto-confirm for automated execution
            }
        )

        # Run live consolidation
        logger.info(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)

        if result.returncode != 0:
            raise RuntimeError(f"Live consolidation failed: {result.stderr}")

        # Parse output for statistics
        live_output = result.stdout
        consolidation_result = {
            "duplicates_found": dry_run_result["duplicates_found"],
            "duplicates_merged": _parse_merged_count(live_output),
            "relationships_transferred": _parse_relationships_transferred(live_output),
            "output": live_output,
            "execution_timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ Live consolidation completed: {consolidation_result['duplicates_merged']} "
            f"entities merged, {consolidation_result['relationships_transferred']} relationships transferred"
        )

        # Store result
        context["task_instance"].xcom_push(key="consolidation_result", value=consolidation_result)

        return consolidation_result

    except subprocess.TimeoutExpired:
        logger.error("Live consolidation timed out after 10 minutes")
        raise
    except Exception as e:
        logger.error(f"Live consolidation failed: {e}")
        raise


def _parse_merged_count(output: str) -> int:
    """Parse merged entities count from output."""
    try:
        import re

        match = re.search(r"Successfully Merged\s+│\s+(\d+)", output)
        if match:
            return int(match.group(1))
        return 0
    except Exception:
        return 0


def _parse_relationships_transferred(output: str) -> int:
    """Parse relationships transferred count from output."""
    try:
        import re

        match = re.search(r"Relationships Transferred\s+│\s+(\d+)", output)
        if match:
            return int(match.group(1))
        return 0
    except Exception:
        return 0


def generate_summary_no_duplicates(**context) -> dict[str, Any]:
    """Generate summary when no duplicates were found."""
    try:
        dry_run_result = context["task_instance"].xcom_pull(
            task_ids="run_dry_run_consolidation", key="dry_run_result"
        )

        summary = {
            "dag_run_summary": {
                "dag_id": DAG_ID,
                "execution_date": context["execution_date"].isoformat(),
                "result": "no_duplicates_found",
            },
            "deduplication_metrics": {
                "duplicates_found": 0,
                "duplicates_merged": 0,
                "relationships_transferred": 0,
                "similarity_threshold": dry_run_result["similarity_threshold"],
            },
            "next_steps": {
                "next_scheduled_run": "Next Sunday 3 AM UTC",
                "recommended_actions": [
                    "Knowledge graph entity quality is good - no duplicates detected",
                    "Continue monitoring entity normalization effectiveness",
                ],
            },
        }

        logger.info("📊 Deduplication Summary: No duplicates found - knowledge graph is clean")

        context["task_instance"].xcom_push(key="dag_summary", value=summary)

        return summary

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise


def generate_summary_manual_review(**context) -> dict[str, Any]:
    """Generate summary when duplicates found but manual review required."""
    try:
        dry_run_result = context["task_instance"].xcom_pull(
            task_ids="run_dry_run_consolidation", key="dry_run_result"
        )

        summary = {
            "dag_run_summary": {
                "dag_id": DAG_ID,
                "execution_date": context["execution_date"].isoformat(),
                "result": "manual_review_required",
            },
            "deduplication_metrics": {
                "duplicates_found": dry_run_result["duplicates_found"],
                "duplicates_merged": 0,
                "relationships_transferred": 0,
                "similarity_threshold": dry_run_result["similarity_threshold"],
            },
            "next_steps": {
                "next_scheduled_run": "Next Sunday 3 AM UTC",
                "recommended_actions": [
                    f"Review dry-run report: {dry_run_result.get('report_file', 'See Airflow logs')}",
                    f"{dry_run_result['duplicates_found']} potential duplicates require manual review",
                    "Run consolidation manually if duplicates are confirmed: "
                    "python scripts/consolidate_duplicate_entities.py",
                    "Consider enabling AUTO_CONFIRM for automated consolidation if confident in threshold",
                ],
            },
        }

        logger.info(
            f"📊 Deduplication Summary: {dry_run_result['duplicates_found']} duplicates found "
            f"- manual review required"
        )

        context["task_instance"].xcom_push(key="dag_summary", value=summary)

        return summary

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise


def generate_summary_consolidated(**context) -> dict[str, Any]:
    """Generate summary after successful consolidation."""
    try:
        consolidation_result = context["task_instance"].xcom_pull(
            task_ids="run_live_consolidation", key="consolidation_result"
        )

        duplicates_merged = consolidation_result["duplicates_merged"]
        relationships_transferred = consolidation_result["relationships_transferred"]

        summary = {
            "dag_run_summary": {
                "dag_id": DAG_ID,
                "execution_date": context["execution_date"].isoformat(),
                "result": "consolidation_successful",
            },
            "deduplication_metrics": {
                "duplicates_found": consolidation_result["duplicates_found"],
                "duplicates_merged": duplicates_merged,
                "relationships_transferred": relationships_transferred,
                "success_rate": (
                    duplicates_merged / max(consolidation_result["duplicates_found"], 1)
                ),
            },
            "quality_indicators": {
                "knowledge_graph_health": "improved",
                "entity_count_reduction": duplicates_merged,
                "relationships_per_duplicate": (
                    relationships_transferred / max(duplicates_merged, 1)
                ),
            },
            "next_steps": {
                "next_scheduled_run": "Next Sunday 3 AM UTC",
                "recommended_actions": [
                    f"Successfully consolidated {duplicates_merged} duplicate entities",
                    f"Transferred {relationships_transferred} relationships",
                    "Monitor entity extraction patterns to improve normalization",
                    "Consider adjusting similarity threshold if false positives detected",
                ],
            },
        }

        logger.info(
            f"📊 Deduplication Summary: Successfully merged {duplicates_merged} entities, "
            f"transferred {relationships_transferred} relationships"
        )

        context["task_instance"].xcom_push(key="dag_summary", value=summary)

        return summary

    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        raise


# Define tasks
check_apoc_task = PythonOperator(
    task_id="check_apoc_availability",
    python_callable=check_apoc_availability,
    dag=dag,
    doc_md="""
    **Check APOC Plugin Availability**

    Verifies that the APOC plugin is installed and available in Neo4j.
    APOC is required for fuzzy string matching (Levenshtein similarity).
    """,
)

dry_run_task = PythonOperator(
    task_id="run_dry_run_consolidation",
    python_callable=run_dry_run_consolidation,
    dag=dag,
    doc_md="""
    **Run Dry-Run Consolidation**

    Executes the consolidation script in dry-run mode to:
    1. Identify potential duplicate entity pairs using Levenshtein similarity
    2. Generate preview report of duplicates
    3. Save report for manual review
    """,
)

check_threshold_task = BranchPythonOperator(
    task_id="check_consolidation_threshold",
    python_callable=check_consolidation_threshold,
    dag=dag,
    doc_md="""
    **Check Consolidation Threshold**

    Determines next action based on:
    - Number of duplicates found
    - AUTO_CONFIRM configuration setting

    Routes to:
    - Live consolidation (if duplicates found and auto-confirm enabled)
    - Manual review summary (if duplicates found but auto-confirm disabled)
    - No duplicates summary (if no duplicates found)
    """,
)

live_consolidation_task = PythonOperator(
    task_id="run_live_consolidation",
    python_callable=run_live_consolidation,
    dag=dag,
    doc_md="""
    **Run Live Consolidation**

    Executes actual consolidation to:
    1. Transfer relationships from duplicates to canonical entities
    2. Merge entity properties
    3. Delete duplicate entities
    4. Log consolidation actions for audit trail
    """,
)

summary_no_duplicates_task = PythonOperator(
    task_id="generate_summary_no_duplicates",
    python_callable=generate_summary_no_duplicates,
    dag=dag,
    doc_md="""
    **Generate Summary - No Duplicates**

    Creates summary report indicating clean knowledge graph with no duplicates detected.
    """,
)

summary_manual_review_task = PythonOperator(
    task_id="generate_summary_manual_review",
    python_callable=generate_summary_manual_review,
    dag=dag,
    doc_md="""
    **Generate Summary - Manual Review Required**

    Creates summary report with:
    - Duplicate count and preview
    - Link to dry-run report
    - Instructions for manual consolidation
    """,
)

summary_consolidated_task = PythonOperator(
    task_id="generate_summary_consolidated",
    python_callable=generate_summary_consolidated,
    dag=dag,
    doc_md="""
    **Generate Summary - Consolidation Complete**

    Creates summary report with:
    - Consolidation metrics and success rate
    - Entities merged and relationships transferred
    - Knowledge graph health indicators
    """,
)

# Set task dependencies
check_apoc_task >> dry_run_task >> check_threshold_task

# Branch paths
check_threshold_task >> [
    live_consolidation_task,
    summary_no_duplicates_task,
    summary_manual_review_task,
]

# Live consolidation leads to its own summary
live_consolidation_task >> summary_consolidated_task

# Export DAG
globals()[DAG_ID] = dag
