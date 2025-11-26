"""
Processor for Bundestag Plenarprotokoll data from DIP API (Flow 5d).

Uses the PlenarprotokollCollector from bundestag_ingestion to fetch and
process plenary session protocols.
"""

import os
import time
from datetime import datetime
from typing import Any

import structlog
from kodosumi import core
from neo4j import GraphDatabase

from src.flows.bundestag_common.api_client import BundestagAPIClient
from src.flows.bundestag_common.graphiti_registration import GraphitiNodeRegistrar
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager
from src.flows.bundestag_ingestion.collectors.plenarprotokoll_collector import (
    PlenarprotokollCollector,
)

logger = structlog.get_logger()


async def process_plenarprotokoll_batch(inputs: dict[str, Any], tracer):
    """
    Process Bundestag Plenarprotokoll collection batch.

    Args:
        inputs: Dictionary containing:
            - wahlperioden: List of Wahlperiode numbers
            - start_date: Optional start date filter
            - end_date: Optional end date filter
            - batch_size: Number of protocols per batch
            - max_protocols: Maximum total protocols (None for unlimited)
            - fetch_full_text: Whether to fetch complete transcripts
            - create_relationships: Whether to create graph relationships
        tracer: Kodosumi tracer for progress updates

    Returns:
        Markdown response with collection results
    """
    start_time = time.time()

    await tracer.markdown("# 📋 Bundestag Plenarprotokoll Collection\n")
    await tracer.markdown(f"**Start Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    # Extract inputs
    wahlperioden = inputs.get("wahlperioden", ["20"])
    start_date = inputs.get("start_date")
    end_date = inputs.get("end_date")
    batch_size = inputs.get("batch_size", 50)
    max_protocols = inputs.get("max_protocols")  # Can be None for unlimited
    fetch_full_text = inputs.get("fetch_full_text", False)
    create_relationships = inputs.get("create_relationships", True)
    # Enable Graphiti registration by default for search compatibility
    enable_graphiti_registration = inputs.get("enable_graphiti_registration", True)

    await tracer.markdown("## Configuration\n")
    await tracer.markdown(f"- **Wahlperioden**: {', '.join(map(str, wahlperioden))}\n")
    await tracer.markdown(
        f"- **Max protocols**: {max_protocols if max_protocols else 'Unlimited'}\n"
    )
    await tracer.markdown(f"- **Batch size**: {batch_size}\n")
    await tracer.markdown(f"- **Fetch full text**: {'✅ Yes' if fetch_full_text else '❌ No'}\n")
    await tracer.markdown(
        f"- **Graphiti registration**: {'✅ Enabled' if enable_graphiti_registration else '❌ Disabled'}\n"
    )
    await tracer.markdown(f"- **Date range**: {start_date or 'Any'} to {end_date or 'Any'}\n\n")

    if fetch_full_text:
        await tracer.markdown("⚠️ **Full-text extraction enabled** - this will be slow!\n\n")

    # Initialize components
    await tracer.markdown("## Stage 1: Initializing Components\n")

    try:
        # Neo4j connection
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))

        # API client
        api_client = BundestagAPIClient()

        # Upsert manager
        upsert_manager = Neo4jUpsertManager(driver, "politicalmonitoring.v3")

        # Graphiti registrar (optional)
        graphiti_registrar = None
        if enable_graphiti_registration:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                await tracer.markdown(
                    "⚠️ OPENAI_API_KEY not found, Graphiti registration disabled\n"
                )
                enable_graphiti_registration = False
            else:
                graphiti_registrar = GraphitiNodeRegistrar(
                    neo4j_driver=driver,
                    neo4j_database="politicalmonitoring.v3",
                    openai_api_key=openai_api_key,
                )
                await tracer.markdown("✅ Graphiti registrar initialized\n")

        await tracer.markdown("✅ All components initialized\n\n")

    except Exception as e:
        error_msg = f"❌ Initialization failed: {str(e)}"
        await tracer.markdown(f"{error_msg}\n")
        from .report_generator import generate_error_report

        return core.response.Markdown(generate_error_report(str(e)))

    # Process each Wahlperiode
    await tracer.markdown("## Stage 2: Collecting Plenarprotokolle\n")

    total_protocols = 0
    total_entities = 0
    total_edges = 0
    total_errors = 0
    total_graphiti_registered = 0
    total_graphiti_failed = 0

    for wahlperiode in wahlperioden:
        await tracer.markdown(f"\n### Processing Wahlperiode {wahlperiode}\n")

        # Create collector with neo4j_driver for automatic saving
        collector = PlenarprotokollCollector(
            api_client=api_client, neo4j_driver=driver, neo4j_database="politicalmonitoring.v3"
        )

        # Build filters
        filters = {
            "f.wahlperiode": wahlperiode
            # Note: No herausgeber filter - collect both Bundestag (BT) and Bundesrat (BR)
        }
        if start_date:
            filters["f.datum_von"] = start_date
        if end_date:
            filters["f.datum_bis"] = end_date

        # Calculate limit for this WP
        wp_limit = None
        if max_protocols:
            remaining = max_protocols - total_protocols
            if remaining <= 0:
                await tracer.markdown("⏭️  Skipping (max protocols reached)\n")
                continue
            wp_limit = remaining

        try:
            # Collect and transform
            collection_inputs = {
                "filters": filters,
                "limit": wp_limit,
                "fetch_full_text": fetch_full_text,
            }

            result = await collector.collect_and_transform(collection_inputs)

            # Debug: Report raw result
            await tracer.markdown(f"\n**DEBUG: Collector result keys**: {list(result.keys())}\n")
            await tracer.markdown(
                f"**DEBUG: entities_created**: {result.get('entities_created')}\n"
            )
            await tracer.markdown(f"**DEBUG: items_collected**: {result.get('items_collected')}\n")

            # Report results
            protocols_collected = result.get("items_collected", 0)
            entities_created = result.get("entities_created", 0)
            edges_created = result.get("edges_created", 0)
            errors = result.get("errors", [])

            await tracer.markdown(f"- Collected: **{protocols_collected}** protocols\n")
            await tracer.markdown(f"- Entities: **{entities_created}**\n")
            await tracer.markdown(f"- Edges: **{edges_created}**\n")

            if errors:
                await tracer.markdown(f"- ⚠️  Errors: **{len(errors)}**\n")
                total_errors += len(errors)

            total_protocols += protocols_collected
            total_entities += entities_created
            total_edges += edges_created

            # Upsert to Neo4j if we have entities
            if result.get("entities") and len(result["entities"]) > 0:
                await tracer.markdown("\n### Upserting to Neo4j\n")

                entities = result["entities"]

                # Upsert in batches
                successful = 0
                for i in range(0, len(entities), batch_size):
                    batch = entities[i : i + batch_size]
                    upsert_result = upsert_manager.upsert_entities_batch(
                        entity_type="Plenarprotokoll", entities=batch, batch_size=batch_size
                    )
                    successful += upsert_result.get("successful", 0)
                    await tracer.markdown(f"- Batch {i//batch_size + 1}: {len(batch)} protocols\n")

                await tracer.markdown(f"✅ Upserted **{successful}** protocols\n\n")

                # Register with Graphiti if enabled
                if enable_graphiti_registration and graphiti_registrar and successful > 0:
                    await tracer.markdown("### Registering with Graphiti\n")

                    registered = 0
                    failed = 0

                    for entity in entities:
                        try:
                            # Extract Plenarprotokoll identifiers
                            sitzungsnummer = entity.get("sitzungsnummer")
                            entity_wahlperiode = entity.get("wahlperiode")

                            if not sitzungsnummer or not entity_wahlperiode:
                                logger.warning(
                                    f"Skipping Graphiti registration for entity missing keys: {entity.get('id')}"
                                )
                                failed += 1
                                continue

                            # Generate entity name for embedding
                            plenarprotokoll_name = (
                                f"Plenarprotokoll {entity_wahlperiode}/{sitzungsnummer}"
                            )
                            if entity.get("titel"):
                                plenarprotokoll_name = entity["titel"]

                            # Register with Graphiti
                            result_graphiti = await graphiti_registrar.register_plenarprotokoll(
                                sitzungsnummer=sitzungsnummer,
                                wahlperiode=entity_wahlperiode,
                                plenarprotokoll_name=plenarprotokoll_name,
                                additional_properties=None,
                            )

                            if result_graphiti.get("success"):
                                registered += 1
                            else:
                                failed += 1
                                logger.warning(
                                    f"Failed to register Plenarprotokoll {entity_wahlperiode}/{sitzungsnummer}: "
                                    f"{result_graphiti.get('reason')}"
                                )

                        except Exception as e:
                            failed += 1
                            logger.error(
                                f"Error registering Plenarprotokoll with Graphiti: {e}",
                                exc_info=True,
                            )

                    total_graphiti_registered += registered
                    total_graphiti_failed += failed

                    await tracer.markdown(
                        f"✅ Registered **{registered}** protocols with Graphiti "
                        f"({failed} failed)\n\n"
                    )

                # Create relationships if requested
                if create_relationships and result.get("edges"):
                    await tracer.markdown("### Creating Relationships\n")
                    edges = result["edges"]
                    # Edges are already created by the collector
                    await tracer.markdown(f"✅ Created **{len(edges)}** relationships\n\n")

        except Exception as e:
            error_msg = f"❌ Error processing WP {wahlperiode}: {str(e)}"
            await tracer.markdown(f"{error_msg}\n")
            logger.error(error_msg, error=str(e), exc_info=True)
            total_errors += 1

    # Generate final report
    duration = time.time() - start_time

    await tracer.markdown("## Summary\n")
    await tracer.markdown(f"- **Total protocols**: {total_protocols}\n")
    await tracer.markdown(f"- **Total entities**: {total_entities}\n")
    await tracer.markdown(f"- **Total edges**: {total_edges}\n")
    if enable_graphiti_registration:
        await tracer.markdown(
            f"- **Graphiti registered**: {total_graphiti_registered} "
            f"({total_graphiti_failed} failed)\n"
        )
    await tracer.markdown(f"- **Errors**: {total_errors}\n")
    await tracer.markdown(f"- **Duration**: {duration:.1f} seconds\n")
    await tracer.markdown(f"**End Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Close connections
    driver.close()
    await api_client.close()

    # Generate detailed report
    from .report_generator import generate_collection_report

    report = generate_collection_report(
        {
            "total_protocols": total_protocols,
            "wahlperioden_processed": wahlperioden,
            "errors": total_errors,
            "duration": duration,
            "fetch_full_text": fetch_full_text,
        }
    )

    return core.response.Markdown(report)


def generate_error_report(error: str) -> str:
    """Generate error report markdown."""
    return f"""# ❌ Plenarprotokoll Collection Failed

## Error Details

{error}

## Troubleshooting

1. Check that Neo4j is running: `docker ps | grep neo4j`
2. Verify Bundestag API is accessible
3. Check environment variables are set correctly
4. Review logs for detailed error messages

## Next Steps

- Fix the error and retry the collection
- Contact support if the issue persists
"""
