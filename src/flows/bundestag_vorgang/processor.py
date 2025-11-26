"""
Processor for Bundestag Vorgang data from DIP API.

Maps vorgang data to Neo4j entities and creates relationships.
"""

import asyncio
import json
import os
import ssl
from typing import Any, Optional

import aiohttp
import structlog
from kodosumi import core
from neo4j import GraphDatabase

from src.flows.bundestag_common.graphiti_registration import GraphitiNodeRegistrar
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager

logger = structlog.get_logger()

# Bundestag API configuration
BUNDESTAG_API_URL = os.getenv("BUNDESTAG_API_URL", "https://search.dip.bundestag.de/api/v1")
BUNDESTAG_API_KEY = os.getenv("BUNDESTAG_API_KEY")


def safe_str(value: Any) -> str:
    """Safely convert value to string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def safe_list(value: Any) -> list[str]:
    """Safely convert value to list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)] if value else []


def safe_date(value: Any) -> Optional[str]:
    """Safely convert date value to ISO string."""
    if not value:
        return None
    if isinstance(value, str):
        # Handle ISO dates
        return value.split("T")[0] if "T" in value else value
    return str(value)


def map_vorgang_to_entity(api_data: dict[str, Any]) -> dict[str, Any]:
    """
    Map Bundestag API vorgang data to Neo4j entity structure.

    Args:
        api_data: Raw vorgang data from DIP API

    Returns:
        Dict with Neo4j entity properties
    """
    vorgang_id = safe_str(api_data.get("id"))
    vorgangstyp = safe_str(api_data.get("vorgangstyp", ""))

    # Base properties
    entity = {
        "vorgang_id": vorgang_id,
        "titel": safe_str(api_data.get("titel", "")),
        "abstract": safe_str(api_data.get("abstract", "")),
        "vorgangstyp": vorgangstyp,
        "beratungsstand": safe_str(api_data.get("beratungsstand", "")),
        "datum": safe_date(api_data.get("datum")),
        "aktualisiert": safe_date(api_data.get("aktualisiert")),
        "wahlperiode": api_data.get("wahlperiode"),
        "sachgebiet": safe_list(api_data.get("sachgebiet", [])),
        "initiative": safe_list(api_data.get("initiative", [])),
        "typ": safe_str(api_data.get("typ", "Vorgang")),
    }

    # Optional fields
    if api_data.get("gesta"):
        entity["gesta"] = safe_str(api_data["gesta"])

    if api_data.get("archiv"):
        entity["archiv"] = safe_str(api_data["archiv"])

    # Gesetzgebung-specific fields
    if vorgangstyp == "Gesetzgebung":
        if api_data.get("zustimmungsbeduerftigkeit"):
            entity["zustimmungsbeduerftigkeit"] = json.dumps(api_data["zustimmungsbeduerftigkeit"])

        if api_data.get("verkuendung"):
            entity["verkuendung"] = json.dumps(api_data["verkuendung"])

        if api_data.get("inkrafttreten"):
            entity["inkrafttreten"] = json.dumps(api_data["inkrafttreten"])

    # Store deskriptoren as JSON for later relationship creation
    if api_data.get("deskriptor"):
        entity["deskriptor_json"] = json.dumps(api_data["deskriptor"])

    return entity


def extract_deskriptoren(api_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract deskriptor entities from vorgang data."""
    deskriptoren = []

    for desk in api_data.get("deskriptor", []):
        deskriptor_id = f"{desk.get('name', '')}_{desk.get('typ', 'Sachbegriffe')}"
        deskriptoren.append(
            {
                "deskriptor_id": deskriptor_id,
                "name": safe_str(desk.get("name", "")),
                "typ": safe_str(desk.get("typ", "Sachbegriffe")),
                "fundstelle": desk.get("fundstelle", False),
            }
        )

    return deskriptoren


def extract_sachgebiete(api_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract sachgebiet entities from vorgang data."""
    sachgebiete = []

    for sg in api_data.get("sachgebiet", []):
        if sg:
            sachgebiete.append(
                {
                    "sachgebiet_name": safe_str(sg),
                    "name": safe_str(sg),
                }
            )

    return sachgebiete


async def fetch_vorgaenge_from_api(
    wahlperiode: int,
    vorgangstyp: Optional[str] = None,
    cursor: Optional[str] = None,
    batch_size: int = 100,
) -> tuple[list[dict], Optional[str]]:
    """
    Fetch vorgänge from Bundestag DIP API.

    Args:
        wahlperiode: Wahlperiode number
        vorgangstyp: Filter by vorgangstyp (None for all)
        cursor: Pagination cursor
        batch_size: Number of results per request

    Returns:
        Tuple of (documents list, next cursor)
    """
    url = f"{BUNDESTAG_API_URL}/vorgang"

    params = {
        "f.wahlperiode": wahlperiode,
        "format": "json",
        "num": batch_size,  # API parameter for page size
    }

    if vorgangstyp and vorgangstyp != "Alle":
        params["f.vorgangstyp"] = vorgangstyp

    if cursor:
        params["cursor"] = cursor

    headers = {"Authorization": f"ApiKey {BUNDESTAG_API_KEY}"} if BUNDESTAG_API_KEY else {}

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    connector = aiohttp.TCPConnector(ssl=ssl_context)

    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                logger.error(f"API error: {response.status}")
                return [], None

            data = await response.json()
            documents = data.get("documents", [])
            next_cursor = data.get("cursor")

            return documents, next_cursor


async def process_vorgang_batch(inputs: dict[str, Any], tracer):
    """
    Process vorgänge in batches for selected wahlperioden.

    Args:
        inputs: Dictionary with job configuration
        tracer: Kodosumi tracer for progress updates

    Returns:
        Markdown report of execution
    """
    # Extract inputs
    wahlperioden = inputs.get("wahlperioden", ["20"])
    vorgangstyp = inputs.get("vorgangstyp", "Alle")
    batch_size = inputs.get("batch_size", 100)
    max_vorgaenge = inputs.get("max_vorgaenge", 1000)
    create_relationships = inputs.get("create_relationships", True)
    # Enable Graphiti registration by default for search compatibility
    enable_graphiti_registration = inputs.get("enable_graphiti_registration", True)

    # Initialize Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    neo4j_database = os.getenv("NEO4J_DATABASE", "politicalmonitoring.v3")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    upsert_manager = Neo4jUpsertManager(driver=driver, database=neo4j_database)

    # Initialize Graphiti registrar (optional)
    graphiti_registrar = None
    if enable_graphiti_registration:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            graphiti_registrar = GraphitiNodeRegistrar(
                neo4j_driver=driver,
                neo4j_database=neo4j_database,
                openai_api_key=openai_api_key,
            )
            logger.info("✅ Graphiti registrar initialized")
        else:
            logger.warning("⚠️ OPENAI_API_KEY not found, Graphiti registration disabled")
            enable_graphiti_registration = False

    stats = {
        "total_fetched": 0,
        "total_processed": 0,
        "vorgaenge_created": 0,
        "deskriptoren_created": 0,
        "sachgebiete_created": 0,
        "relationships_created": 0,
        "graphiti_registered": 0,
        "graphiti_failed": 0,
        "errors": [],
    }

    # Display configuration
    await tracer.markdown("## Configuration\n")
    await tracer.markdown(f"- **Wahlperioden**: {', '.join(wahlperioden)}\n")
    await tracer.markdown(f"- **Vorgangstyp**: {vorgangstyp}\n")
    await tracer.markdown(f"- **Batch Size**: {batch_size}\n")
    await tracer.markdown(
        f"- **Max Vorgänge**: {'All (no limit)' if max_vorgaenge is None else max_vorgaenge}\n"
    )
    await tracer.markdown(
        f"- **Create Relationships**: {'✅ Yes' if create_relationships else '❌ No'}\n"
    )
    await tracer.markdown(
        f"- **Graphiti Registration**: {'✅ Enabled' if enable_graphiti_registration else '❌ Disabled'}\n\n"
    )

    try:
        for wp in wahlperioden:
            await tracer.markdown(f"\n## Processing Wahlperiode {wp}\n")

            wp_int = int(wp)
            cursor = None
            wp_count = 0

            while max_vorgaenge is None or wp_count < max_vorgaenge:
                # Fetch batch from API
                documents, next_cursor = await fetch_vorgaenge_from_api(
                    wahlperiode=wp_int,
                    vorgangstyp=vorgangstyp,
                    cursor=cursor,
                    batch_size=batch_size,
                )

                if not documents:
                    await tracer.markdown(f"✅ No more vorgänge for WP {wp}\n")
                    break

                stats["total_fetched"] += len(documents)
                wp_count += len(documents)

                await tracer.markdown(f"📥 Fetched {len(documents)} vorgänge (total: {wp_count})\n")

                # Map to entities
                vorgang_entities = []
                all_deskriptoren = []
                all_sachgebiete = []

                for doc in documents:
                    try:
                        # Map vorgang
                        vorgang_entity = map_vorgang_to_entity(doc)
                        vorgang_entities.append(vorgang_entity)

                        # Extract related entities
                        if create_relationships:
                            deskriptoren = extract_deskriptoren(doc)
                            all_deskriptoren.extend(deskriptoren)

                            sachgebiete = extract_sachgebiete(doc)
                            all_sachgebiete.extend(sachgebiete)

                    except Exception as e:
                        logger.error(f"Error mapping vorgang {doc.get('id')}: {e}")
                        stats["errors"].append(str(e))

                # Upsert vorgang entities
                await tracer.markdown(f"💾 Upserting {len(vorgang_entities)} vorgänge...\n")
                vorgang_results = upsert_manager.upsert_entities_batch(
                    entity_type="Vorgang", entities=vorgang_entities, batch_size=batch_size
                )
                stats["vorgaenge_created"] += vorgang_results["successful"]
                stats["total_processed"] += len(vorgang_entities)

                # Register with Graphiti if enabled
                if (
                    enable_graphiti_registration
                    and graphiti_registrar
                    and vorgang_results["successful"] > 0
                ):
                    await tracer.markdown("\n📝 Registering with Graphiti...\n")

                    registered = 0
                    failed = 0

                    for entity in vorgang_entities:
                        try:
                            # Extract Vorgang identifiers
                            vorgang_id = entity.get("vorgang_id")

                            if not vorgang_id:
                                logger.warning(
                                    f"Skipping Graphiti registration for entity missing vorgang_id: {entity}"
                                )
                                failed += 1
                                continue

                            # Generate entity name for embedding
                            vorgang_name = vorgang_id
                            if entity.get("titel"):
                                vorgang_name = f"{vorgang_id}: {entity['titel']}"

                            # Register with Graphiti
                            result_graphiti = await graphiti_registrar.register_vorgang(
                                vorgang_id=vorgang_id,
                                vorgang_name=vorgang_name,
                                additional_properties=None,
                            )

                            if result_graphiti.get("success"):
                                registered += 1
                            else:
                                failed += 1
                                logger.warning(
                                    f"Failed to register Vorgang {vorgang_id}: "
                                    f"{result_graphiti.get('reason')}"
                                )

                        except Exception as e:
                            failed += 1
                            logger.error(
                                f"Error registering Vorgang with Graphiti: {e}", exc_info=True
                            )

                    stats["graphiti_registered"] += registered
                    stats["graphiti_failed"] += failed

                    await tracer.markdown(
                        f"✅ Registered {registered} vorgänge with Graphiti ({failed} failed)\n\n"
                    )

                # Create related entities and relationships
                if create_relationships:
                    # Upsert deskriptoren
                    if all_deskriptoren:
                        # Deduplicate
                        unique_deskriptoren = {
                            d["deskriptor_id"]: d for d in all_deskriptoren
                        }.values()
                        desk_results = upsert_manager.upsert_entities_batch(
                            entity_type="Deskriptor",
                            entities=list(unique_deskriptoren),
                            batch_size=batch_size,
                        )
                        stats["deskriptoren_created"] += desk_results["successful"]

                    # Upsert sachgebiete
                    if all_sachgebiete:
                        # Deduplicate
                        unique_sachgebiete = {
                            s["sachgebiet_name"]: s for s in all_sachgebiete
                        }.values()
                        sg_results = upsert_manager.upsert_entities_batch(
                            entity_type="Sachgebiet",
                            entities=list(unique_sachgebiete),
                            batch_size=batch_size,
                        )
                        stats["sachgebiete_created"] += sg_results["successful"]

                    # Create relationships (in next iteration after testing nodes)
                    await tracer.markdown("🔗 Creating relationships...\n")
                    rel_count = await create_vorgang_relationships(
                        driver, neo4j_database, [v["vorgang_id"] for v in vorgang_entities]
                    )
                    stats["relationships_created"] += rel_count

                await tracer.markdown(
                    f"✅ Batch complete: {vorgang_results['successful']} vorgänge, "
                    f"{stats.get('deskriptoren_created', 0)} deskriptoren, "
                    f"{stats.get('sachgebiete_created', 0)} sachgebiete\n"
                )

                # Check if we've reached max (if set)
                if max_vorgaenge is not None and wp_count >= max_vorgaenge:
                    await tracer.markdown(f"⚠️ Reached max limit of {max_vorgaenge} for WP {wp}\n")
                    break

                # Move to next page
                cursor = next_cursor
                if not cursor:
                    break

                # Small delay between batches
                await asyncio.sleep(0.5)

    finally:
        driver.close()

    # Generate final report
    report = f"""# Bundestag Vorgang Ingestion Complete

## Summary
- **Total Fetched**: {stats['total_fetched']} vorgänge
- **Total Processed**: {stats['total_processed']} vorgänge
- **Vorgänge Created**: {stats['vorgaenge_created']}
- **Deskriptoren Created**: {stats['deskriptoren_created']}
- **Sachgebiete Created**: {stats['sachgebiete_created']}
- **Relationships Created**: {stats['relationships_created']}
"""

    # Add Graphiti stats if enabled
    if enable_graphiti_registration:
        report += f"- **Graphiti Registered**: {stats['graphiti_registered']} ({stats['graphiti_failed']} failed)\n"

    report += """
## Configuration
- **Wahlperioden**: {', '.join(wahlperioden)}
- **Vorgangstyp**: {vorgangstyp}
- **Batch Size**: {batch_size}
- **Max Vorgänge**: {'All (no limit)' if max_vorgaenge is None else max_vorgaenge}
- **Create Relationships**: {'Yes' if create_relationships else 'No'}

## Errors
{len(stats['errors'])} errors occurred during processing.
"""

    if stats["errors"]:
        report += "\n### Error Details\n"
        for error in stats["errors"][:10]:  # Show first 10 errors
            report += f"- {error}\n"

    return core.response.Markdown(report)


async def create_vorgang_relationships(driver, database: str, vorgang_ids: list[str]) -> int:
    """Create relationships for vorgänge."""
    rel_count = 0

    with driver.session(database=database) as session:
        # Create BELONGS_TO relationships to Wahlperiode
        query = """
        MATCH (v:Vorgang)
        WHERE v.vorgang_id IN $vorgang_ids AND v.wahlperiode IS NOT NULL
        MATCH (w:Wahlperiode {wahlperiode_nummer: v.wahlperiode})
        MERGE (v)-[:BELONGS_TO]->(w)
        RETURN count(*) as count
        """
        result = session.run(query, vorgang_ids=vorgang_ids)
        record = result.single()
        rel_count += record["count"] if record else 0

        # Create TAGGED_WITH relationships to Deskriptor
        # Note: This requires parsing deskriptor_json stored in Vorgang nodes
        query = """
        MATCH (v:Vorgang)
        WHERE v.vorgang_id IN $vorgang_ids AND v.deskriptor_json IS NOT NULL
        WITH v, v.deskriptor_json as desk_json
        UNWIND apoc.convert.fromJsonList(desk_json) as desk
        WITH v, desk.name as name, desk.typ as typ, desk.fundstelle as fundstelle
        WHERE name IS NOT NULL AND typ IS NOT NULL
        MATCH (d:Deskriptor {name: name, typ: typ})
        MERGE (v)-[r:TAGGED_WITH]->(d)
        ON CREATE SET r.fundstelle = fundstelle
        RETURN count(*) as count
        """
        try:
            result = session.run(query, vorgang_ids=vorgang_ids)
            record = result.single()
            rel_count += record["count"] if record else 0
        except Exception as e:
            logger.warning(f"Deskriptor relationship creation requires APOC: {e}")

        # Create SUBJECT_AREA relationships to Sachgebiet
        query = """
        MATCH (v:Vorgang)
        WHERE v.vorgang_id IN $vorgang_ids AND v.sachgebiet IS NOT NULL
        UNWIND v.sachgebiet AS sg_name
        MATCH (s:Sachgebiet {sachgebiet_name: sg_name})
        MERGE (v)-[:SUBJECT_AREA]->(s)
        RETURN count(*) as count
        """
        result = session.run(query, vorgang_ids=vorgang_ids)
        record = result.single()
        rel_count += record["count"] if record else 0

    return rel_count
