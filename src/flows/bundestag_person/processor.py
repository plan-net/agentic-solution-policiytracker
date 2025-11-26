"""
Processor entrypoint for Bundestag Person ingestion.

Creates BundestagPersonFlow instance and executes the collection pipeline.
"""

import json
from typing import Any

from kodosumi import core


async def process_bundestag_persons(inputs: dict[str, Any], tracer) -> core.response.Markdown:
    """
    Process Bundestag persons collection.

    Args:
        inputs: Dictionary with job configuration
        tracer: Kodosumi tracer for progress updates

    Returns:
        Markdown report of execution
    """
    from src.flows.bundestag_common.base_flow import BaseBundestagFlow
    from src.flows.bundestag_common.field_extractors import (
        extract_fraktion,
        extract_wahlperioden,
        safe_date,
        safe_list,
        safe_str,
    )

    # Create flow instance
    class BundestagPersonFlow(BaseBundestagFlow):
        @property
        def endpoint(self) -> str:
            return "person"

        @property
        def entity_type(self) -> str:
            return "BundestagPerson"

        @property
        def entity_id_field(self) -> str:
            return "person_id"

        def get_entity_name(self, entity: dict[str, Any]) -> str:
            """Extract person name for Graphiti registration."""
            return entity.get("person_name", "Unknown Person")

        def map_api_to_entity(self, api_data: dict[str, Any]) -> dict[str, Any]:
            """Map Person API data to BundestagPerson entity."""
            person_id = safe_str(api_data.get("id"))
            if not person_id:
                raise ValueError("Person API data missing required 'id' field")

            # Build full name (from components only, not using titel field which has duplicates)
            vorname = safe_str(api_data.get("vorname", ""))
            nachname = safe_str(api_data.get("nachname", ""))
            namenszusatz = safe_str(api_data.get("namenszusatz", ""))

            # person_name from name components only
            full_name_parts = [vorname, namenszusatz, nachname]
            person_name = " ".join(p for p in full_name_parts if p).strip()

            # titel is stored separately (full formatted title from API)
            titel = safe_str(api_data.get("titel", ""))

            entity = {
                "person_id": person_id,
                "person_name": person_name,
                # Basic info
                "vorname": vorname,
                "nachname": nachname,
                "namenszusatz": namenszusatz,
                "titel": titel,
                "adelstitel": safe_str(api_data.get("adelstitel", "")),
                "anrede": safe_str(api_data.get("anrede", "")),
                "akademischer_titel": safe_str(api_data.get("akad_titel", "")),
                # Demographics
                "geburtsdatum": safe_date(api_data.get("geburtsdatum")),
                "geburtsort": safe_str(api_data.get("geburtsort", "")),
                "geburtsland": safe_str(api_data.get("geburtsland", "")),
                "geschlecht": safe_str(api_data.get("geschlecht", "")),
                "familienstand": safe_str(api_data.get("familienstand", "")),
                "religion": safe_str(api_data.get("religion", "")),
                "beruf": safe_str(api_data.get("beruf", "")),
                # Dates
                "sterbedatum": safe_date(api_data.get("sterbedatum")),
                "mdb_since": safe_date(api_data.get("mdb_seit")),
                # Political affiliation
                "current_fraktion": extract_fraktion(api_data),
                "wahlperioden": extract_wahlperioden(api_data),
                # Contact
                "homepage": safe_str(api_data.get("homepage", "")),
                # Historical data
                "historie_von": safe_date(api_data.get("historie_von")),
                "historie_bis": safe_date(api_data.get("historie_bis")),
                # API metadata fields (always available)
                "funktion": safe_list(api_data.get("funktion", [])),  # ["MdB"]
                "typ": safe_str(api_data.get("typ", "")),  # "Person"
                "datum": safe_date(api_data.get("datum")),  # Current snapshot date
                "basisdatum": safe_date(api_data.get("basisdatum")),  # Base/start date
                "ressort": safe_list(api_data.get("ressort", [])),  # Ministry assignments
                "person_roles_history": json.dumps(
                    api_data.get("person_roles", [])
                ),  # Complete role history as JSON string
                # Metadata
                "aktualisiert": safe_date(api_data.get("aktualisiert")),
            }

            return entity

    # Get OpenAI API key for Graphiti registration
    openai_api_key = inputs.get("openai_api_key")
    if not openai_api_key:
        import os
        openai_api_key = os.getenv("OPENAI_API_KEY")

    # Initialize flow with Graphiti registration enabled
    flow = BundestagPersonFlow(
        api_key=inputs["api_key"],
        api_url=inputs["api_url"],
        neo4j_uri=inputs["neo4j_uri"],
        neo4j_username=inputs["neo4j_username"],
        neo4j_password=inputs["neo4j_password"],
        neo4j_database=inputs["neo4j_database"],
        enable_graphiti_registration=True if openai_api_key else False,
        openai_api_key=openai_api_key,
    )

    try:
        # Execute flow pipeline
        result = await flow.process(inputs, tracer)
        return result

    finally:
        # Cleanup
        flow.cleanup()
