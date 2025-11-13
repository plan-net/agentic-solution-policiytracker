"""
Bundestag Data Ingestion Processor

Main business logic for collecting German parliamentary data from the Bundestag DIP API
and ingesting it into Neo4j knowledge graph following political schema v4.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List

import ray
from kodosumi.core import Tracer
from kodosumi import core
from neo4j import GraphDatabase

from src.config import Settings
from .collectors import (
    VorgangCollector,
    DrucksacheCollector,
    VorgangspositionCollector,
    AktivitaetCollector,
    PlenarprotokollCollector,
    PersonCollector,
    WahlperiodeBuilder,
    FraktionBuilder,
)
from .transformers import BundestagEntityBuilder, BundestagEdgeBuilder
from .utils.api_client import BundestagAPIClient
from .report_generator import generate_execution_report


async def process_bundestag_data(inputs: dict, tracer: Tracer):
    """
    Main entrypoint for Bundestag data ingestion.

    Orchestrates:
    1. Data collection from DIP API (8 endpoints)
    2. Entity transformation to political schema v4
    3. Edge/relationship building
    4. Neo4j ingestion
    5. Progress tracking and reporting

    Args:
        inputs: Form inputs from Kodosumi
        tracer: Kodosumi tracer for progress updates

    Returns:
        core.response.Markdown: Execution summary report
    """

    start_time = datetime.now()

    # Initialize settings
    settings = Settings()

    await tracer.markdown(f"# {inputs['job_name']}\n")
    await tracer.markdown("Starting Bundestag data ingestion pipeline...\n")
    await tracer.markdown(f"**Start Time:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize Neo4j connection
    await tracer.markdown("\n## Initialization\n")
    await tracer.markdown("Connecting to Neo4j database...")

    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )
        # Test connection
        driver.verify_connectivity()
        await tracer.markdown(f"✅ Neo4j connection established (database: {settings.NEO4J_DATABASE})\n")
    except Exception as e:
        await tracer.markdown(f"Failed to connect to Neo4j: {str(e)}\n")
        return core.response.Markdown(
            f"# Error: Neo4j Connection Failed\n\n{str(e)}\n\n"
            "Please ensure Neo4j is running and credentials are correct."
        )

    # Clear data if requested
    if inputs.get("clear_data", False):
        await tracer.markdown("\nClearing existing Bundestag data...")
        try:
            with driver.session(database=settings.NEO4J_DATABASE) as session:
                # Delete all German parliamentary nodes
                session.run("""
                    MATCH (n)
                    WHERE n:Vorgang OR n:Drucksache OR n:Vorgangsposition
                       OR n:Aktivitaet OR n:Plenarprotokoll OR n:Person
                       OR n:Wahlperiode OR n:Fraktion
                    DETACH DELETE n
                """)
            await tracer.markdown("Existing data cleared\n")
        except Exception as e:
            await tracer.markdown(f"Warning: Failed to clear data: {str(e)}\n")

    # Initialize API client and builders
    await tracer.markdown("\nInitializing API client and builders...")

    # Create API client
    api_client = BundestagAPIClient(
        api_key=settings.BUNDESTAG_API_KEY,
        base_url=settings.BUNDESTAG_API_URL
    )

    # Create entity and edge builders
    entity_builder = BundestagEntityBuilder()
    edge_builder = BundestagEdgeBuilder()

    # Store collection parameters for use in collect methods
    collection_params = {
        "wahlperiode": inputs.get("wahlperiode", "20"),
        "max_items": inputs.get("max_items_per_type", 100),
        "include_full_text": inputs.get("include_full_text", False),
        "start_date": inputs.get("start_date"),
        "end_date": inputs.get("end_date"),
    }
    await tracer.markdown(f"Configuration: {collection_params}\n")

    # Results tracking
    results = {
        "job_name": inputs["job_name"],
        "start_time": start_time,
        "collections": {},
        "entities_created": 0,
        "edges_created": 0,
        "errors": [],
    }

    # Stage 1: Collect Reference Data (if selected)
    if inputs.get("collect_reference_data", False):
        await tracer.markdown("\n## Stage 1: Collecting Reference Data\n")

        # Wahlperioden
        await tracer.markdown("Collecting Wahlperioden (election periods)...")
        try:
            wahlperiode_builder = WahlperiodeBuilder()
            wahlperioden_data = await wahlperiode_builder.build_all()
            results["collections"]["wahlperiode"] = {
                "collected": len(wahlperioden_data),
                "status": "success"
            }
            await tracer.markdown(f"Collected {len(wahlperioden_data)} Wahlperioden\n")
        except Exception as e:
            results["errors"].append(f"Wahlperioden collection failed: {str(e)}")
            await tracer.markdown(f"Error collecting Wahlperioden: {str(e)}\n")

        # Fraktionen
        await tracer.markdown("Collecting Fraktionen (parliamentary groups)...")
        try:
            fraktion_builder = FraktionBuilder()
            fraktionen_data = await fraktion_builder.build_all()
            results["collections"]["fraktion"] = {
                "collected": len(fraktionen_data),
                "status": "success"
            }
            await tracer.markdown(f"Collected {len(fraktionen_data)} Fraktionen\n")
        except Exception as e:
            results["errors"].append(f"Fraktionen collection failed: {str(e)}")
            await tracer.markdown(f"Error collecting Fraktionen: {str(e)}\n")

    # Stage 2: Collect Primary Data
    await tracer.markdown("\n## Stage 2: Collecting Primary Data\n")

    # Use Ray actors for parallel collection
    @ray.remote
    class CollectorActor:
        def __init__(self, collector_class, api_client, entity_builder, edge_builder, neo4j_uri, neo4j_username, neo4j_password, neo4j_database, collection_params):
            # Create Neo4j driver inside the actor (driver can't be serialized)
            from neo4j import GraphDatabase
            neo4j_driver = GraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_username, neo4j_password)
            )

            self.collector = collector_class(
                api_client,
                entity_builder,
                edge_builder,
                neo4j_driver=neo4j_driver,
                neo4j_database=neo4j_database
            )
            self.collection_params = collection_params
            self.neo4j_driver = neo4j_driver

        async def collect(self):
            # Pass collection parameters to the collect method
            return await self.collector.collect_and_transform(self.collection_params)

        def __del__(self):
            # Clean up driver when actor is destroyed
            if hasattr(self, 'neo4j_driver') and self.neo4j_driver:
                self.neo4j_driver.close()

    collection_tasks = []

    # Vorgänge
    if inputs.get("collect_vorgang", False):
        await tracer.markdown("Starting Vorgang collection...")
        collector = CollectorActor.remote(VorgangCollector, api_client, entity_builder, edge_builder, settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD, settings.NEO4J_DATABASE, collection_params)
        collection_tasks.append(("vorgang", collector.collect.remote()))

    # Drucksachen
    if inputs.get("collect_drucksache", False):
        await tracer.markdown("Starting Drucksache collection...")
        collector = CollectorActor.remote(DrucksacheCollector, api_client, entity_builder, edge_builder, settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD, settings.NEO4J_DATABASE, collection_params)
        collection_tasks.append(("drucksache", collector.collect.remote()))

    # Vorgangspositionen
    if inputs.get("collect_vorgangsposition", False):
        await tracer.markdown("Starting Vorgangsposition collection...")
        collector = CollectorActor.remote(VorgangspositionCollector, api_client, entity_builder, edge_builder, settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD, settings.NEO4J_DATABASE, collection_params)
        collection_tasks.append(("vorgangsposition", collector.collect.remote()))

    # Aktivitäten
    if inputs.get("collect_aktivitaet", False):
        await tracer.markdown("Starting Aktivitaet collection...")
        collector = CollectorActor.remote(AktivitaetCollector, api_client, entity_builder, edge_builder, settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD, settings.NEO4J_DATABASE, collection_params)
        collection_tasks.append(("aktivitaet", collector.collect.remote()))

    # Plenarprotokolle
    if inputs.get("collect_plenarprotokoll", False):
        await tracer.markdown("Starting Plenarprotokoll collection...")
        collector = CollectorActor.remote(PlenarprotokollCollector, api_client, entity_builder, edge_builder, settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD, settings.NEO4J_DATABASE, collection_params)
        collection_tasks.append(("plenarprotokoll", collector.collect.remote()))

    # Personen
    if inputs.get("collect_person", False):
        await tracer.markdown("Starting Person collection...")
        collector = CollectorActor.remote(PersonCollector, api_client, entity_builder, edge_builder, settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD, settings.NEO4J_DATABASE, collection_params)
        collection_tasks.append(("person", collector.collect.remote()))

    # Wait for collections to complete with progress updates
    await tracer.markdown(f"\nCollecting data from {len(collection_tasks)} sources in parallel...\n")

    for data_type, task_ref in collection_tasks:
        try:
            # Wait for task to complete - returns dict with statistics
            collection_stats = await task_ref

            # Extract statistics from collector result
            items_collected = collection_stats.get("items_collected", 0)
            entities_created = collection_stats.get("entities_created", 0)
            edges_created = collection_stats.get("edges_created", 0)

            results["collections"][data_type] = {
                "items_collected": items_collected,
                "entities_created": entities_created,
                "edges_created": edges_created,
                "status": "success"
            }

            # Update totals
            results["entities_created"] += entities_created
            results["edges_created"] += edges_created

            await tracer.markdown(
                f"✅ Completed {data_type}: {items_collected} items collected, "
                f"{entities_created} entities, {edges_created} edges created\n"
            )
        except Exception as e:
            results["errors"].append(f"{data_type} collection failed: {str(e)}")
            await tracer.markdown(f"❌ Error collecting {data_type}: {str(e)}\n")
            results["collections"][data_type] = {
                "items_collected": 0,
                "entities_created": 0,
                "edges_created": 0,
                "status": "failed",
                "error": str(e)
            }

    # Stage 3: Finalization
    await tracer.markdown("\n## Stage 3: Finalization\n")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    results["end_time"] = end_time
    results["duration_seconds"] = duration

    await tracer.markdown(f"**End Time:** {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    await tracer.markdown(f"**Duration:** {duration:.1f} seconds\n")

    # Close Neo4j connection
    driver.close()

    await tracer.markdown("\nIngestion pipeline complete!\n")

    # Generate final report
    report_content = generate_execution_report(results)

    return core.response.Markdown(report_content)
