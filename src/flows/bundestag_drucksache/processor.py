"""
Processor for Bundestag Drucksache data from DIP API (Flow 5c).

Maps drucksache data to Neo4j entities, optionally downloads PDFs,
extracts full text, and creates relationships.
"""

# CRITICAL DEBUG: This should print when module is imported
print("=" * 100, flush=True)
print("🚨 MODULE IMPORTED: processor.py with DEBUG CODE VERSION 2.0", flush=True)
print("=" * 100, flush=True)

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiohttp
import structlog
from kodosumi import core
from langchain_openai import OpenAIEmbeddings
from neo4j import Driver, GraphDatabase

from src.config import graphrag_settings
from src.flows.bundestag_common.api_client import BundestagAPIClient
from src.flows.bundestag_common.field_extractors import (
    extract_related_vorgang_ids,
    safe_date,
    safe_int,
    safe_list,
    safe_str,
)
from src.flows.bundestag_common.graphiti_registration import GraphitiNodeRegistrar
from src.flows.bundestag_common.neo4j_upsert import Neo4jUpsertManager

logger = structlog.get_logger()

# Storage configuration
DRUCKSACHE_STORAGE_PATH = Path(os.getenv("DRUCKSACHE_STORAGE_PATH", "./data/drucksachen"))
DRUCKSACHE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


def map_drucksache_to_entity(api_data: dict[str, Any]) -> dict[str, Any]:
    """
    Map Bundestag API drucksache data to Neo4j entity structure.

    Args:
        api_data: Raw drucksache data from DIP API

    Returns:
        Dict with Neo4j entity properties
    """
    drucksache_id = safe_str(api_data.get("id"))
    # FIX: Use dokumentnummer (the actual drucksache number like "20/12345")
    # instead of drucksachetyp (document type like "Antrag")
    drucksache_nummer = safe_str(api_data.get("dokumentnummer", ""))
    drucksachetyp = safe_str(api_data.get("drucksachetyp", ""))

    # Base properties
    entity = {
        "drucksache_id": drucksache_id,
        "drucksache_nummer": drucksache_nummer,  # Unique ID: "20/12345"
        "drucksachetyp": drucksachetyp,  # Document type: "Antrag", "Antwort", etc.
        "titel": safe_str(api_data.get("titel", "")),
        "dokumentart": safe_str(api_data.get("dokumentart", "")),
        "dokumentnummer": safe_str(api_data.get("dokumentnummer", "")),  # Same as drucksache_nummer
        "wahlperiode": safe_int(api_data.get("wahlperiode")),
        "datum": safe_date(api_data.get("datum")),
        "aktualisiert": safe_date(api_data.get("aktualisiert")),
        "herausgeber": safe_str(api_data.get("herausgeber", "")),
        "typ": safe_str(api_data.get("typ", "Drucksache")),
    }

    # Optional fields
    if api_data.get("abstract"):
        entity["abstract"] = safe_str(api_data["abstract"])

    if api_data.get("fundstelle"):
        # Store complete fundstelle as JSON
        entity["fundstelle"] = json.dumps(api_data["fundstelle"])

        # Extract individual fundstelle fields as separate properties
        fundstelle = api_data["fundstelle"]
        if isinstance(fundstelle, dict):
            # PDF URL - critical for full-text extraction
            if fundstelle.get("pdf_url"):
                entity["dokument_url"] = safe_str(fundstelle["pdf_url"])

            # Distribution date (Verteildatum) - when document was distributed
            if fundstelle.get("verteildatum"):
                entity["verteildatum"] = safe_date(fundstelle["verteildatum"])

            # Fundstelle ID (may differ from main drucksache_id)
            if fundstelle.get("id"):
                entity["fundstelle_id"] = safe_str(fundstelle["id"])

            # Additional fundstelle-specific metadata
            if fundstelle.get("seiten"):
                entity["seiten"] = safe_str(fundstelle["seiten"])  # Page numbers

            if fundstelle.get("anlagetyp"):
                entity["anlagetyp"] = safe_str(fundstelle["anlagetyp"])  # Attachment type

    if api_data.get("ressort"):
        # Serialize to JSON to handle nested dict/list structures
        entity["ressort_json"] = json.dumps(safe_list(api_data["ressort"]))

    if api_data.get("initiative"):
        # Serialize to JSON to handle nested dict/list structures
        entity["initiative_json"] = json.dumps(safe_list(api_data["initiative"]))

    # Urheber (originators)
    if api_data.get("urheber"):
        entity["urheber"] = json.dumps(api_data["urheber"])

    # PDF document URL (fallback to top-level dokumentUrl if not in fundstelle)
    if not entity.get("dokument_url") and api_data.get("dokumentUrl"):
        entity["dokument_url"] = safe_str(api_data["dokumentUrl"])

    # Autoren (authors)
    if api_data.get("autoren_anzahl"):
        entity["autoren_anzahl"] = safe_int(api_data["autoren_anzahl"])

    if api_data.get("autoren_anzeige"):
        entity["autoren_anzeige"] = safe_str(api_data["autoren_anzeige"])

    # Store related Vorgang IDs as JSON for relationship creation
    vorgang_ids_json = extract_related_vorgang_ids(api_data)
    if vorgang_ids_json:
        entity["vorgang_ids_json"] = vorgang_ids_json

    return entity


async def fetch_drucksachen_from_api(
    client: BundestagAPIClient,
    wahlperiode: int,
    dokumentart: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    cursor: Optional[str] = None,
) -> tuple[list[dict], Optional[str]]:
    """
    Fetch drucksachen from Bundestag DIP API with pagination.

    Args:
        client: Bundestag API client instance
        wahlperiode: Wahlperiode number
        dokumentart: Document type filter (None for all)
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
        cursor: Pagination cursor

    Returns:
        Tuple of (documents list, next cursor)
    """
    params = {
        "f.wahlperiode": wahlperiode,
        "format": "json",
    }

    if dokumentart and dokumentart != "Alle":
        params["f.dokumentart"] = dokumentart

    if start_date:
        params["f.datum.start"] = start_date

    if end_date:
        params["f.datum.end"] = end_date

    if cursor:
        params["cursor"] = cursor

    try:
        data = await client.get("drucksache", params=params)
        documents = data.get("documents", [])
        next_cursor = data.get("cursor")

        logger.info(
            "Fetched drucksachen from API",
            wahlperiode=wahlperiode,
            count=len(documents),
            has_next=bool(next_cursor),
        )

        return documents, next_cursor

    except Exception as e:
        logger.error(f"Failed to fetch drucksachen: {e}")
        return [], None


async def download_pdf(
    session: aiohttp.ClientSession, url: str, save_path: Path, semaphore: asyncio.Semaphore
) -> bool:
    """
    Download PDF document with concurrency control.

    Args:
        session: Aiohttp client session
        url: PDF URL to download
        save_path: Local path to save PDF
        semaphore: Asyncio semaphore for concurrency control

    Returns:
        True if download successful, False otherwise
    """
    logger.info(f"🌐 Entered download_pdf for {url}")
    print(f"🌐 Entered download_pdf for {url}", flush=True)

    async with semaphore:
        try:
            logger.info(f"📡 Making HTTP GET request to {url}")
            print(f"📡 Making HTTP GET request to {url}", flush=True)

            # Disable SSL verification for Bundestag server (certificate issues)
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=60), ssl=False
            ) as response:
                logger.info(f"✅ Got response with status {response.status}")
                print(f"✅ Got response with status {response.status}", flush=True)

                if response.status != 200:
                    logger.warning(f"PDF download failed with status {response.status}", url=url)
                    print(f"⚠️ Non-200 status: {response.status}", flush=True)
                    return False

                # Ensure directory exists
                logger.info(f"📁 Creating directory: {save_path.parent}")
                print(f"📁 Creating directory: {save_path.parent}", flush=True)
                save_path.parent.mkdir(parents=True, exist_ok=True)

                # Save PDF content
                logger.info(f"💾 Saving to {save_path}")
                print(f"💾 Saving to {save_path}", flush=True)
                with open(save_path, "wb") as f:
                    f.write(await response.read())

                logger.info("PDF downloaded successfully", url=url, size=save_path.stat().st_size)
                print(f"✅ Download complete: {save_path.stat().st_size} bytes", flush=True)
                return True

        except Exception as e:
            logger.error(f"Failed to download PDF: {e}", url=url)
            print(f"❌ Download exception: {e}", flush=True)
            import traceback

            traceback.print_exc()
            return False


def check_drucksache_exists(driver: Driver, database: str, drucksache_nummer: str) -> bool:
    """
    Check if Drucksache node already exists in Neo4j.

    Args:
        driver: Neo4j driver instance
        database: Database name
        drucksache_nummer: Drucksache identifier to check

    Returns:
        True if exists, False if new
    """
    try:
        with driver.session(database=database) as session:
            result = session.run(
                """
                MATCH (d:Drucksache {drucksache_nummer: $drucksache_nummer})
                RETURN count(d) > 0 as exists
                """,
                drucksache_nummer=drucksache_nummer,
            )

            record = result.single()
            return record["exists"] if record else False
    except Exception as e:
        logger.warning(f"Error checking if Drucksache exists: {e}")
        # On error, assume it doesn't exist (safe fallback - will process)
        return False


async def extract_pdf_text(pdf_path: Path) -> list[str]:
    """
    Extract text from PDF page by page using PyPDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of text strings, one per page
    """
    try:
        import pypdf

        pages = []

        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)

            for i, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    pages.append(text)
                    logger.debug(f"Extracted text from page {i}", pdf_path=str(pdf_path))
                except Exception as e:
                    logger.warning(f"Failed to extract page {i}: {e}", pdf_path=str(pdf_path))
                    pages.append("")  # Empty page on error

        logger.info("Extracted PDF text", pdf_path=str(pdf_path), pages=len(pages))
        return pages

    except Exception as e:
        logger.error(f"Failed to extract PDF text: {e}", pdf_path=str(pdf_path))
        return []


def create_page_embedding(page_text: str) -> list[float]:
    """
    Create embedding for page text using OpenAI.

    Args:
        page_text: Text content of the page

    Returns:
        List of floats representing the embedding vector (1536 dimensions)
    """
    try:
        # Initialize embeddings using config
        embeddings = OpenAIEmbeddings(
            model=graphrag_settings.GRAPHRAG_EMBEDDING_MODEL,
            dimensions=graphrag_settings.GRAPHRAG_EMBEDDING_DIMS,
        )

        # Create embedding
        embedding_vector = embeddings.embed_query(page_text)

        return embedding_vector

    except Exception as e:
        logger.error(f"Failed to create embedding: {e}")
        # Return zero vector as fallback
        return [0.0] * graphrag_settings.GRAPHRAG_EMBEDDING_DIMS


async def create_page_nodes(
    driver: Driver,
    database: str,
    drucksache_nummer: str,
    pages: list[str],
    wahlperiode: int,
) -> int:
    """
    Create DrucksachePage nodes in Neo4j with embeddings and relationships.

    Args:
        driver: Neo4j driver instance
        database: Database name
        drucksache_nummer: Parent Drucksache identifier
        pages: List of page texts
        wahlperiode: Wahlperiode number

    Returns:
        Number of page nodes created
    """
    if not pages:
        return 0

    pages_created = 0
    upsert_manager = Neo4jUpsertManager(driver, database)

    try:
        for page_num, page_text in enumerate(pages, start=1):
            # Skip empty pages
            if not page_text or not page_text.strip():
                logger.warning(f"Skipping empty page {page_num} for {drucksache_nummer}")
                continue

            # Generate page ID
            page_id = f"{drucksache_nummer}_page_{page_num}"

            # Create embedding
            logger.info(f"Creating embedding for page {page_num} of {drucksache_nummer}")
            embedding = create_page_embedding(page_text)

            # Prepare page entity data
            page_entity = {
                "page_id": page_id,
                "page_number": page_num,
                "drucksache_nummer": drucksache_nummer,
                "wahlperiode": wahlperiode,
                "content": page_text,
                "embedding": embedding,
            }

            # Upsert page node
            success = upsert_manager.upsert_entity("DrucksachePage", page_entity)

            if success:
                pages_created += 1

                # Create relationships in a single session
                with driver.session(database=database) as session:
                    # Create HAS_PAGE relationship from Drucksache to Page
                    session.run(
                        """
                        MATCH (d:Drucksache {drucksache_nummer: $drucksache_nummer})
                        MATCH (p:DrucksachePage {page_id: $page_id})
                        MERGE (d)-[:HAS_PAGE]->(p)
                        """,
                        drucksache_nummer=drucksache_nummer,
                        page_id=page_id,
                    )

                    # Create NEXT_PAGE relationship to previous page
                    if page_num > 1:
                        prev_page_id = f"{drucksache_nummer}_page_{page_num - 1}"
                        session.run(
                            """
                            MATCH (p1:DrucksachePage {page_id: $prev_page_id})
                            MATCH (p2:DrucksachePage {page_id: $curr_page_id})
                            MERGE (p1)-[:NEXT_PAGE]->(p2)
                            """,
                            prev_page_id=prev_page_id,
                            curr_page_id=page_id,
                        )

                logger.info(f"Created page node {page_id}")
            else:
                logger.error(f"Failed to create page node {page_id}")

        logger.info(
            f"Created {pages_created} page nodes for {drucksache_nummer}",
            drucksache_nummer=drucksache_nummer,
            pages_created=pages_created,
        )

        return pages_created

    except Exception as e:
        logger.error(f"Failed to create page nodes: {e}", drucksache_nummer=drucksache_nummer)
        return pages_created


async def create_drucksache_relationships(
    driver, database: str, drucksache_nummern: list[str]
) -> int:
    """
    Create relationships for drucksachen.

    Creates:
    - BELONGS_TO → Wahlperiode
    - DOCUMENT_FOR → Vorgang (if vorgang_ids_json present)

    Args:
        driver: Neo4j driver instance
        database: Database name
        drucksache_nummern: List of drucksache numbers to process

    Returns:
        Number of relationships created
    """
    rel_count = 0

    with driver.session(database=database) as session:
        # Create BELONGS_TO relationships to Wahlperiode
        query = """
        MATCH (d:Drucksache)
        WHERE d.drucksache_nummer IN $drucksache_nummern AND d.wahlperiode IS NOT NULL
        MATCH (w:Wahlperiode {wahlperiode_nummer: d.wahlperiode})
        MERGE (d)-[:BELONGS_TO]->(w)
        RETURN count(*) as count
        """
        result = session.run(query, drucksache_nummern=drucksache_nummern)
        record = result.single()
        rel_count += record["count"] if record else 0

        # Create DOCUMENT_FOR relationships to Vorgang
        query = """
        MATCH (d:Drucksache)
        WHERE d.drucksache_nummer IN $drucksache_nummern AND d.vorgang_ids_json IS NOT NULL
        WITH d, d.vorgang_ids_json as vorgang_json
        UNWIND apoc.convert.fromJsonList(vorgang_json) as vorgang_id
        MATCH (v:Vorgang {vorgang_id: vorgang_id})
        MERGE (d)-[:DOCUMENT_FOR]->(v)
        RETURN count(*) as count
        """
        try:
            result = session.run(query, drucksache_nummern=drucksache_nummern)
            record = result.single()
            rel_count += record["count"] if record else 0
        except Exception as e:
            logger.warning(f"Vorgang relationship creation requires APOC: {e}")

    return rel_count


async def process_drucksache_batch(inputs: dict[str, Any], tracer):
    """
    Process drucksachen in batches for selected wahlperioden.

    Main entrypoint for Flow 5c: Bundestag Drucksache ingestion.

    Args:
        inputs: Dictionary with job configuration
        tracer: Kodosumi tracer for progress updates

    Returns:
        Markdown report of execution
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    logger.info("=== PROCESSOR STARTED === process_drucksache_batch called")
    print("=== PROCESSOR STARTED === process_drucksache_batch called", flush=True)

    # DEBUG: Log ALL inputs received by processor
    logger.info(f"📦 PROCESSOR RECEIVED INPUTS: {json.dumps(inputs, indent=2, default=str)}")
    print(f"📦 PROCESSOR RECEIVED INPUTS: {json.dumps(inputs, indent=2, default=str)}", flush=True)

    start_time = datetime.now()

    # Parse inputs
    wahlperioden_input = inputs.get("wahlperioden", "20")
    # Handle both list and string inputs
    if isinstance(wahlperioden_input, list):
        wahlperioden = wahlperioden_input
    else:
        wahlperioden = [wp.strip() for wp in wahlperioden_input.split(",")]
    dokumentart = inputs.get("dokumentart", "Alle")
    batch_size = inputs.get("batch_size", 100)
    max_drucksachen = inputs.get("max_drucksachen", 100)
    extract_full_text = inputs.get("extract_full_text", False)
    max_concurrent_downloads = inputs.get("max_concurrent_downloads", 5)
    create_relationships = inputs.get("create_relationships", True)
    # Enable Graphiti registration by default for search compatibility
    enable_graphiti_registration = inputs.get("enable_graphiti_registration", True)
    start_date = inputs.get("start_date")
    end_date = inputs.get("end_date")

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

    # Initialize API client
    api_client = BundestagAPIClient()

    # Initialize aiohttp session for PDF downloads
    pdf_session = None
    if extract_full_text:
        logger.info(
            f"🔍 PDF EXTRACTION ENABLED: Creating aiohttp session with {max_concurrent_downloads} concurrent downloads"
        )
        print(
            f"🔍 PDF EXTRACTION ENABLED: Creating aiohttp session with {max_concurrent_downloads} concurrent downloads",
            flush=True,
        )
        # Create session with SSL verification disabled for Bundestag server
        connector = aiohttp.TCPConnector(ssl=False)
        pdf_session = aiohttp.ClientSession(connector=connector)
        semaphore = asyncio.Semaphore(max_concurrent_downloads)
    else:
        logger.info(f"⚠️ PDF EXTRACTION DISABLED: extract_full_text={extract_full_text}")
        print(f"⚠️ PDF EXTRACTION DISABLED: extract_full_text={extract_full_text}", flush=True)

    # Statistics
    stats = {
        "total_fetched": 0,
        "total_processed": 0,
        "drucksachen_created": 0,
        "drucksachen_skipped": 0,
        "pdfs_downloaded": 0,
        "pages_created": 0,
        "relationships_created": 0,
        "graphiti_registered": 0,
        "graphiti_failed": 0,
        "errors": [],
    }

    try:
        await tracer.markdown("# Bundestag Drucksache Ingestion\n")
        await tracer.markdown(f"**Wahlperioden:** {', '.join(wahlperioden)}\n")
        await tracer.markdown(f"**Dokumentart:** {dokumentart}\n")
        await tracer.markdown(f"**Extract Full Text:** {'Yes' if extract_full_text else 'No'}\n")
        await tracer.markdown(
            f"**Graphiti Registration:** {'✅ Enabled' if enable_graphiti_registration else '❌ Disabled'}\n"
        )
        await tracer.markdown("\n---\n\n")

        for wp in wahlperioden:
            await tracer.markdown(f"## Processing Wahlperiode {wp}\n\n")

            wp_int = int(wp)
            cursor = None
            wp_count = 0

            while max_drucksachen is None or wp_count < max_drucksachen:
                # Fetch batch from API
                await tracer.markdown(
                    f"Fetching drucksachen (batch {wp_count // batch_size + 1})...\n"
                )

                documents, next_cursor = await fetch_drucksachen_from_api(
                    client=api_client,
                    wahlperiode=wp_int,
                    dokumentart=dokumentart,
                    start_date=start_date,
                    end_date=end_date,
                    cursor=cursor,
                )

                if not documents:
                    await tracer.markdown(f"No more drucksachen for WP {wp}\n\n")
                    break

                # Limit documents to respect max_drucksachen (if set)
                if max_drucksachen is not None:
                    remaining = max_drucksachen - wp_count
                    if remaining < len(documents):
                        documents = documents[:remaining]

                stats["total_fetched"] += len(documents)
                wp_count += len(documents)

                await tracer.markdown(f"Fetched {len(documents)} drucksachen (total: {wp_count})\n")

                # Map to entities
                drucksache_entities = []
                pdf_download_tasks = []

                logger.info(
                    f"🔍 BEFORE MAPPING LOOP: extract_full_text={extract_full_text}, type={type(extract_full_text)}"
                )
                print(
                    f"🔍 BEFORE MAPPING LOOP: extract_full_text={extract_full_text}, type={type(extract_full_text)}",
                    flush=True,
                )

                for doc in documents:
                    try:
                        # Map drucksache
                        drucksache_entity = map_drucksache_to_entity(doc)
                        drucksache_entities.append(drucksache_entity)

                        has_url = (
                            drucksache_entity.get("dokument_url") is not None
                            and drucksache_entity.get("dokument_url") != ""
                        )
                        logger.debug(
                            f"Entity {drucksache_entity.get('drucksache_nummer')}: has_url={has_url}, extract_full_text={extract_full_text}"
                        )

                        # Queue PDF download if enabled AND document doesn't exist
                        if extract_full_text and drucksache_entity.get("dokument_url"):
                            pdf_url = drucksache_entity["dokument_url"]
                            drucksache_nummer = drucksache_entity["drucksache_nummer"]

                            # CHECK: Only download PDF if this is a NEW document
                            exists = check_drucksache_exists(
                                driver, neo4j_database, drucksache_nummer
                            )

                            if not exists:
                                # Document is NEW - queue for download
                                safe_filename = drucksache_nummer.replace("/", "-").replace(
                                    " ", "_"
                                )
                                pdf_path = (
                                    DRUCKSACHE_STORAGE_PATH
                                    / f"wp{wp_int}"
                                    / "pdfs"
                                    / f"{safe_filename}.pdf"
                                )

                                pdf_download_tasks.append(
                                    {
                                        "url": pdf_url,
                                        "path": pdf_path,
                                        "nummer": drucksache_nummer,
                                        "wahlperiode": wp_int,
                                    }
                                )
                                logger.info(
                                    f"📥 Queued NEW document for PDF download: {drucksache_nummer}"
                                )
                                print(
                                    f"📥 Queued NEW document for PDF download: {drucksache_nummer}",
                                    flush=True,
                                )
                            else:
                                logger.info(
                                    f"⏭️ Skipping PDF download for existing document: {drucksache_nummer}"
                                )
                                print(
                                    f"⏭️ Skipping PDF download for existing document: {drucksache_nummer}",
                                    flush=True,
                                )
                                stats["drucksachen_skipped"] += 1

                    except Exception as e:
                        logger.error(f"Error mapping drucksache {doc.get('id')}: {e}")
                        stats["errors"].append(str(e))

                # Upsert drucksache entities
                await tracer.markdown(
                    f"Upserting {len(drucksache_entities)} drucksachen to Neo4j...\n"
                )
                drucksache_results = upsert_manager.upsert_entities_batch(
                    entity_type="Drucksache", entities=drucksache_entities, batch_size=batch_size
                )
                stats["drucksachen_created"] += drucksache_results["successful"]
                stats["total_processed"] += len(drucksache_entities)

                await tracer.markdown(
                    f"Upserted {drucksache_results['successful']} drucksachen to Neo4j\n"
                )

                # Register with Graphiti if enabled
                if (
                    enable_graphiti_registration
                    and graphiti_registrar
                    and drucksache_results["successful"] > 0
                ):
                    await tracer.markdown("\nRegistering with Graphiti...\n")

                    registered = 0
                    failed = 0

                    for entity in drucksache_entities:
                        try:
                            # Extract Drucksache identifiers
                            drucksache_id = entity.get("drucksache_id")
                            drucksache_nummer = entity.get("drucksache_nummer")

                            if not drucksache_id or not drucksache_nummer:
                                logger.warning(
                                    f"Skipping Graphiti registration for entity missing keys: {entity}"
                                )
                                failed += 1
                                continue

                            # Generate entity name for embedding
                            drucksache_name = drucksache_nummer
                            if entity.get("titel"):
                                drucksache_name = f"{drucksache_nummer}: {entity['titel']}"

                            # Register with Graphiti
                            result_graphiti = await graphiti_registrar.register_drucksache(
                                drucksache_id=drucksache_id,
                                drucksache_name=drucksache_name,
                                additional_properties=None,
                            )

                            if result_graphiti.get("success"):
                                registered += 1
                            else:
                                failed += 1
                                logger.warning(
                                    f"Failed to register Drucksache {drucksache_nummer}: "
                                    f"{result_graphiti.get('reason')}"
                                )

                        except Exception as e:
                            failed += 1
                            logger.error(
                                f"Error registering Drucksache with Graphiti: {e}", exc_info=True
                            )

                    stats["graphiti_registered"] += registered
                    stats["graphiti_failed"] += failed

                    await tracer.markdown(
                        f"✅ Registered {registered} drucksachen with Graphiti ({failed} failed)\n"
                    )

                # DEBUG: Log PDF download decision
                logger.info(
                    f"🔍 PDF Download Check: extract_full_text={extract_full_text}, pdf_download_tasks={len(pdf_download_tasks)}"
                )
                print(
                    f"🔍 PDF Download Check: extract_full_text={extract_full_text}, pdf_download_tasks={len(pdf_download_tasks)}",
                    flush=True,
                )

                # Download PDFs and extract text if enabled
                if extract_full_text and pdf_download_tasks:
                    logger.info(
                        f"✅ ENTERING PDF DOWNLOAD SECTION: {len(pdf_download_tasks)} PDFs to download"
                    )
                    print(
                        f"✅ ENTERING PDF DOWNLOAD SECTION: {len(pdf_download_tasks)} PDFs to download",
                        flush=True,
                    )
                    await tracer.markdown(
                        f"\nDownloading {len(pdf_download_tasks)} PDFs with {max_concurrent_downloads} concurrent downloads...\n"
                    )

                    logger.info(f"🔄 Starting download loop for {len(pdf_download_tasks)} tasks")
                    print(
                        f"🔄 Starting download loop for {len(pdf_download_tasks)} tasks", flush=True
                    )

                    for idx, task in enumerate(pdf_download_tasks, 1):
                        logger.info(
                            f"📥 Download {idx}/{len(pdf_download_tasks)}: {task['nummer']}"
                        )
                        print(
                            f"📥 Download {idx}/{len(pdf_download_tasks)}: {task['nummer']}",
                            flush=True,
                        )

                        # Download PDF
                        try:
                            success = await download_pdf(
                                session=pdf_session,
                                url=task["url"],
                                save_path=task["path"],
                                semaphore=semaphore,
                            )
                            logger.info(f"Download result for {task['nummer']}: {success}")
                            print(f"Download result for {task['nummer']}: {success}", flush=True)
                        except Exception as e:
                            logger.error(f"❌ Exception downloading {task['nummer']}: {e}")
                            print(f"❌ Exception downloading {task['nummer']}: {e}", flush=True)
                            success = False

                        if success:
                            stats["pdfs_downloaded"] += 1
                            await tracer.markdown(f"Downloaded: {task['nummer']}\n")

                            # Extract text
                            pages = await extract_pdf_text(task["path"])

                            if pages:
                                # Create page nodes with embeddings
                                pages_created = await create_page_nodes(
                                    driver=driver,
                                    database=neo4j_database,
                                    drucksache_nummer=task["nummer"],
                                    pages=pages,
                                    wahlperiode=task["wahlperiode"],
                                )

                                stats["pages_created"] += pages_created

                                if pages_created > 0:
                                    await tracer.markdown(
                                        f"Created {pages_created} page nodes with embeddings: {task['nummer']}\n"
                                    )

                # Create relationships
                if create_relationships:
                    await tracer.markdown("\nCreating relationships...\n")
                    rel_count = await create_drucksache_relationships(
                        driver,
                        neo4j_database,
                        [d["drucksache_nummer"] for d in drucksache_entities],
                    )
                    stats["relationships_created"] += rel_count
                    await tracer.markdown(f"Created {rel_count} relationships\n")

                await tracer.markdown(
                    f"\nBatch complete: {drucksache_results['successful']} drucksachen processed\n\n"
                )

                # Check if we've reached max (if set)
                if max_drucksachen is not None and wp_count >= max_drucksachen:
                    await tracer.markdown(f"Reached max limit of {max_drucksachen} for WP {wp}\n\n")
                    break

                # Move to next page
                cursor = next_cursor
                if not cursor:
                    break

                # Small delay between batches
                await asyncio.sleep(0.5)

    except Exception as e:
        # Log error and continue to report generation
        error_msg = f"Critical error during processing: {str(e)}"
        stats["errors"].append(error_msg)
        await tracer.markdown(f"\n\n❌ **Error:** {error_msg}\n\n")
        import traceback

        await tracer.markdown(f"```\n{traceback.format_exc()}\n```\n")

    finally:
        driver.close()
        await api_client.close()
        if pdf_session:
            await pdf_session.close()

    # Calculate execution time
    execution_time = (datetime.now() - start_time).total_seconds()

    # Generate final report
    report = f"""# Bundestag Drucksache Ingestion Complete

## Summary
- **Total Fetched**: {stats['total_fetched']} drucksachen
- **Total Processed**: {stats['total_processed']} drucksachen
- **Drucksachen Created**: {stats['drucksachen_created']}
- **Drucksachen Skipped** (already exist): {stats['drucksachen_skipped']}
- **PDFs Downloaded**: {stats['pdfs_downloaded']}
- **Page Nodes Created**: {stats['pages_created']}
- **Relationships Created**: {stats['relationships_created']}"""

    if enable_graphiti_registration:
        report += f"\n- **Graphiti Registered**: {stats['graphiti_registered']} ({stats['graphiti_failed']} failed)"

    report += f"\n- **Execution Time**: {execution_time:.1f} seconds\n"

    report += f"""
## Configuration
- **Wahlperioden**: {', '.join(wahlperioden)}
- **Dokumentart**: {dokumentart}
- **Batch Size**: {batch_size}
- **Max Drucksachen**: {'All (no limit)' if max_drucksachen is None else max_drucksachen}
- **Extract Full Text**: {'Yes' if extract_full_text else 'No'}
- **Max Concurrent Downloads**: {max_concurrent_downloads}
- **Create Relationships**: {'Yes' if create_relationships else 'No'}
"""

    if start_date or end_date:
        report += "\n### Date Filters\n"
        if start_date:
            report += f"- **Start Date**: {start_date}\n"
        if end_date:
            report += f"- **End Date**: {end_date}\n"

    if extract_full_text:
        report += "\n### Storage\n"
        report += f"- **PDF Storage**: {DRUCKSACHE_STORAGE_PATH / 'wp*' / 'pdfs'}\n"
        report += f"- **Markdown Storage**: {DRUCKSACHE_STORAGE_PATH / 'wp*' / '*.md'}\n"

    report += f"\n## Errors\n{len(stats['errors'])} errors occurred during processing.\n"

    if stats["errors"]:
        report += "\n### Error Details\n"
        for error in stats["errors"][:10]:  # Show first 10 errors
            report += f"- {error}\n"

    logger.info(f"=== PROCESSOR COMPLETE === Returning report ({len(report)} chars)")
    print(f"=== PROCESSOR COMPLETE === Returning report ({len(report)} chars)", flush=True)
    return core.response.Markdown(report)
