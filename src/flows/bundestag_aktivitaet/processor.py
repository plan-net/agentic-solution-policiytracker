"""
Processor entrypoint for Bundestag Aktivitaet ingestion.

Creates BundestagAktivitaetFlow instance and executes the collection pipeline.
"""

import json
from datetime import datetime
from typing import Any

import structlog
from kodosumi import core

logger = structlog.get_logger()


async def process_bundestag_aktivitaeten(inputs: dict[str, Any], tracer) -> core.response.Markdown:
    """
    Process Bundestag aktivitaeten collection.

    Args:
        inputs: Dictionary with job configuration
        tracer: Kodosumi tracer for progress updates

    Returns:
        Markdown report of execution
    """
    from src.flows.bundestag_common.base_flow import BaseBundestagFlow
    from src.flows.bundestag_common.field_extractors import (
        safe_date,
        safe_int,
        safe_str,
    )

    # Create flow instance
    class BundestagAktivitaetFlow(BaseBundestagFlow):
        @property
        def endpoint(self) -> str:
            return "aktivitaet"

        @property
        def entity_type(self) -> str:
            return "Aktivitaet"

        @property
        def entity_id_field(self) -> str:
            return "aktivitaet_id"

        def get_entity_name(self, entity: dict[str, Any]) -> str:
            """Extract aktivitaet name for Graphiti registration."""
            titel = entity.get("titel", "")
            aktivitaetsart = entity.get("aktivitaetsart", "")
            if titel:
                return titel
            return f"{aktivitaetsart} {entity.get('aktivitaet_id', 'Unknown')}"

        async def process(self, inputs: dict[str, Any], tracer) -> core.response.Markdown:
            """
            Override process to add relationship creation after entity upsert.
            """
            import time

            start_time = time.time()

            await tracer.markdown(f"# {inputs.get('job_name', 'Bundestag Aktivitaet Ingestion')}\n")
            await tracer.markdown(f"**Endpoint:** {self.endpoint}\n")
            await tracer.markdown(f"**Entity Type:** {self.entity_type}\n")
            await tracer.markdown(
                f"**Start Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            # Stage 1: Fetch data from API
            await tracer.markdown("## Stage 1: Fetching Data from API\n")
            filters = {}
            wahlperiode = inputs.get("wahlperiode")
            if wahlperiode and wahlperiode != "all":
                filters["f.wahlperiode"] = wahlperiode
            aktivitaetsart = inputs.get("aktivitaetsart")
            if aktivitaetsart and aktivitaetsart != "Alle":
                filters["f.aktivitaetsart"] = aktivitaetsart
            start_date = inputs.get("start_date")
            if start_date:
                filters["f.datum_von"] = start_date
            end_date = inputs.get("end_date")
            if end_date:
                filters["f.datum_bis"] = end_date

            max_items = inputs.get("max_items", 100)

            items = await self.fetch_data(filters, max_items, tracer)
            await tracer.markdown(f"✅ Fetched **{len(items)}** items from API\n\n")

            # Stage 2: Map to entities
            await tracer.markdown("## Stage 2: Mapping to Entities\n")
            entities = await self.map_to_entities(items, tracer)
            await tracer.markdown(f"✅ Mapped **{len(entities)}** entities\n\n")

            # Stage 3: Upsert to Neo4j
            await tracer.markdown("## Stage 3: Upserting to Neo4j\n")
            upsert_results = await self.upsert_entities(entities, tracer)
            await tracer.markdown(
                f"✅ Upserted **{upsert_results['successful']}** entities ({upsert_results['failed']} failed)\n\n"
            )

            # Stage 4: Create Relationships (NEW!)
            await tracer.markdown("## Stage 4: Creating Relationships\n")
            relationship_stats = await self.create_relationships(
                entities, tracer, create_relationships_flag=inputs.get("create_relationships", True)
            )

            # Generate report
            duration = time.time() - start_time
            await tracer.markdown(f"**Duration:** {duration:.1f} seconds\n")
            await tracer.markdown(
                f"**End Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            report = self.generate_report_with_relationships(
                items_fetched=len(items),
                entities_created=len(entities),
                upsert_results=upsert_results,
                relationship_stats=relationship_stats,
                duration=duration,
                inputs=inputs,
            )

            return core.response.Markdown(report)

        def generate_report_with_relationships(
            self,
            items_fetched: int,
            entities_created: int,
            upsert_results: dict[str, int],
            relationship_stats: dict[str, int],
            duration: float,
            inputs: dict[str, Any],
        ) -> str:
            """Generate execution summary report with relationship stats."""
            return f"""# {inputs.get('job_name', 'Bundestag Aktivitaet Ingestion')} - Report

## Summary

**Endpoint:** {self.endpoint}
**Entity Type:** {self.entity_type}
**Execution Time:** {duration:.1f} seconds

## Results

| Stage | Count |
|-------|-------|
| Items Fetched from API | {items_fetched} |
| Entities Mapped | {entities_created} |
| Successfully Upserted | {upsert_results['successful']} |
| Failed | {upsert_results['failed']} |

## Relationships Created

| Relationship Type | Count |
|-------------------|-------|
| PERFORMED_BY (Person) | {relationship_stats['performed_by']} |
| RELATED_TO_VORGANG (Procedure) | {relationship_stats['related_to_vorgang']} |
| REFERENCES_DOCUMENT (Drucksache) | {relationship_stats['references_document']} |
| IN_WAHLPERIODE (Electoral Period) | {relationship_stats['in_wahlperiode']} |
| **Total Relationships** | **{relationship_stats['total']}** |

## Neo4j Statistics

**Total {self.entity_type} in database:** {self.upsert_manager.get_entity_count(self.entity_type)}

## Parameters

- **Wahlperiode:** {inputs.get('wahlperiode', 'all')}
- **Aktivitaetsart:** {inputs.get('aktivitaetsart', 'Alle')}
- **Max Items:** {inputs.get('max_items', 'unlimited')}
- **Create Relationships:** {inputs.get('create_relationships', True)}
- **Date Range:** {inputs.get('start_date', 'none')} to {inputs.get('end_date', 'none')}

---

✅ Data ingestion complete!

Access your data at: http://localhost:7474
"""

        def map_api_to_entity(self, api_data: dict[str, Any]) -> dict[str, Any]:
            """Map Aktivitaet API data to Aktivitaet entity."""
            aktivitaet_id = safe_str(api_data.get("id"))
            if not aktivitaet_id:
                raise ValueError("Aktivitaet API data missing required 'id' field")

            # Extract fundstelle (source document reference)
            fundstelle = api_data.get("fundstelle", {})
            fundstelle_urheber = (
                fundstelle.get("urheber", []) if isinstance(fundstelle, dict) else []
            )

            entity = {
                "aktivitaet_id": aktivitaet_id,
                # Core fields
                "aktivitaetsart": safe_str(api_data.get("aktivitaetsart", "")),
                "typ": safe_str(api_data.get("typ", "Aktivität")),
                "person_id": safe_str(api_data.get("person_id", "")),
                "wahlperiode": safe_int(api_data.get("wahlperiode")),
                "datum": safe_date(api_data.get("datum")),
                "titel": safe_str(api_data.get("titel", "")),
                "dokumentart": safe_str(api_data.get("dokumentart", "")),
                "vorgangsbezug_anzahl": safe_int(api_data.get("vorgangsbezug_anzahl")),
                "aktualisiert": safe_date(api_data.get("aktualisiert")),
                # Fundstelle fields (flattened)
                "fundstelle_id": safe_str(fundstelle.get("id", ""))
                if isinstance(fundstelle, dict)
                else "",
                "fundstelle_dokumentnummer": safe_str(fundstelle.get("dokumentnummer", ""))
                if isinstance(fundstelle, dict)
                else "",
                "fundstelle_datum": safe_date(fundstelle.get("datum"))
                if isinstance(fundstelle, dict)
                else None,
                "fundstelle_verteildatum": safe_date(fundstelle.get("verteildatum"))
                if isinstance(fundstelle, dict)
                else None,
                "fundstelle_pdf_url": safe_str(fundstelle.get("pdf_url", ""))
                if isinstance(fundstelle, dict)
                else "",
                "fundstelle_dokumentart": safe_str(fundstelle.get("dokumentart", ""))
                if isinstance(fundstelle, dict)
                else "",
                "fundstelle_drucksachetyp": safe_str(fundstelle.get("drucksachetyp", ""))
                if isinstance(fundstelle, dict)
                else "",
                "fundstelle_herausgeber": safe_str(fundstelle.get("herausgeber", ""))
                if isinstance(fundstelle, dict)
                else "",
                "fundstelle_urheber": json.dumps(fundstelle_urheber)
                if fundstelle_urheber
                else "[]",
                # Store vorgangsbezug as JSON for reference
                "vorgangsbezug_json": json.dumps(api_data.get("vorgangsbezug", [])),
            }

            return entity

        async def create_relationships(
            self, entities: list[dict[str, Any]], tracer, create_relationships_flag: bool = True
        ) -> dict[str, int]:
            """
            Create relationships between Aktivitaet and related entities.

            Args:
                entities: List of Aktivitaet entities
                tracer: Kodosumi tracer for progress updates
                create_relationships_flag: Whether to create relationships

            Returns:
                Dict with relationship creation counts
            """
            if not create_relationships_flag:
                logger.info("Skipping relationship creation (disabled)")
                return {
                    "total": 0,
                    "performed_by": 0,
                    "related_to_vorgang": 0,
                    "references_document": 0,
                    "in_wahlperiode": 0,
                }

            await tracer.markdown("\n### Creating Relationships\n")

            stats = {
                "total": 0,
                "performed_by": 0,
                "related_to_vorgang": 0,
                "references_document": 0,
                "in_wahlperiode": 0,
            }

            with self.neo4j_driver.session(database=self.neo4j_database) as session:
                for entity in entities:
                    aktivitaet_id = entity["aktivitaet_id"]

                    try:
                        # 1. PERFORMED_BY relationship to BundestagPerson
                        person_id = entity.get("person_id", "")
                        if person_id:
                            result = session.run(
                                """
                                MATCH (a:Aktivitaet {aktivitaet_id: $aktivitaet_id})
                                MATCH (p:BundestagPerson {person_id: $person_id})
                                MERGE (a)-[:PERFORMED_BY]->(p)
                                RETURN count(*) as created
                            """,
                                aktivitaet_id=aktivitaet_id,
                                person_id=person_id,
                            )

                            record = result.single()
                            if record and record["created"] > 0:
                                stats["performed_by"] += 1
                                stats["total"] += 1

                        # 2. RELATED_TO_VORGANG relationships
                        vorgangsbezug_json = entity.get("vorgangsbezug_json", "[]")
                        try:
                            vorgangsbezug = json.loads(vorgangsbezug_json)
                            for vb in vorgangsbezug:
                                vorgang_id = vb.get("id", "")
                                vorgangsposition = vb.get("vorgangsposition", "")

                                if vorgang_id:
                                    result = session.run(
                                        """
                                        MATCH (a:Aktivitaet {aktivitaet_id: $aktivitaet_id})
                                        MATCH (v:Vorgang {vorgang_id: $vorgang_id})
                                        MERGE (a)-[r:RELATED_TO_VORGANG]->(v)
                                        SET r.vorgangsposition = $vorgangsposition
                                        RETURN count(*) as created
                                    """,
                                        aktivitaet_id=aktivitaet_id,
                                        vorgang_id=vorgang_id,
                                        vorgangsposition=vorgangsposition,
                                    )

                                    record = result.single()
                                    if record and record["created"] > 0:
                                        stats["related_to_vorgang"] += 1
                                        stats["total"] += 1
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse vorgangsbezug_json for {aktivitaet_id}"
                            )

                        # 3. REFERENCES_DOCUMENT relationship to Drucksache
                        dokumentnummer = entity.get("fundstelle_dokumentnummer", "")
                        if dokumentnummer:
                            result = session.run(
                                """
                                MATCH (a:Aktivitaet {aktivitaet_id: $aktivitaet_id})
                                MATCH (d:Drucksache {drucksache_nummer: $dokumentnummer})
                                MERGE (a)-[:REFERENCES_DOCUMENT]->(d)
                                RETURN count(*) as created
                            """,
                                aktivitaet_id=aktivitaet_id,
                                dokumentnummer=dokumentnummer,
                            )

                            record = result.single()
                            if record and record["created"] > 0:
                                stats["references_document"] += 1
                                stats["total"] += 1

                        # 4. IN_WAHLPERIODE relationship
                        wahlperiode = entity.get("wahlperiode")
                        if wahlperiode:
                            result = session.run(
                                """
                                MATCH (a:Aktivitaet {aktivitaet_id: $aktivitaet_id})
                                MERGE (w:Wahlperiode {wahlperiode_nummer: $wahlperiode})
                                MERGE (a)-[:IN_WAHLPERIODE]->(w)
                                RETURN count(*) as created
                            """,
                                aktivitaet_id=aktivitaet_id,
                                wahlperiode=wahlperiode,
                            )

                            record = result.single()
                            if record and record["created"] > 0:
                                stats["in_wahlperiode"] += 1
                                stats["total"] += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to create relationships for aktivitaet {aktivitaet_id}: {e}"
                        )

            await tracer.markdown(
                f"""
- **PERFORMED_BY** (Person): {stats['performed_by']}
- **RELATED_TO_VORGANG** (Procedure): {stats['related_to_vorgang']}
- **REFERENCES_DOCUMENT** (Drucksache): {stats['references_document']}
- **IN_WAHLPERIODE** (Electoral Period): {stats['in_wahlperiode']}
- **Total Relationships**: {stats['total']}
"""
            )

            return stats

    # Get OpenAI API key for Graphiti registration
    openai_api_key = inputs.get("openai_api_key")
    if not openai_api_key:
        import os
        openai_api_key = os.getenv("OPENAI_API_KEY")

    # Initialize flow with Graphiti registration enabled
    flow = BundestagAktivitaetFlow(
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
