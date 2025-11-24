"""
Edge builder for German Bundestag relationships using political schema v4.

This module provides the BundestagEdgeBuilder class for creating edge/relationship
objects between Bundestag entities according to the political_schema_v4 definitions.
"""

from typing import Any, Optional

import structlog

from src.graphrag.political_schema_v4 import (
    AuthorsDrucksache,
    DebatedInPlenum,
    InitiatesVorgang,
    InWahlperiode,
    LeadsFraktion,
    MemberOfFraktion,
    RelatesToDrucksache,
    RepresentsWahlkreis,
    SpeaksInPlenum,
)

logger = structlog.get_logger()


class BundestagEdgeBuilder:
    """
    Builder for creating Bundestag edge/relationship objects.

    Transforms relationship data into Pydantic edge objects according
    to political_schema_v4 relationship definitions.
    """

    def __init__(self):
        """Initialize the edge builder."""
        logger.info("Initialized BundestagEdgeBuilder")

    async def create_member_of_fraktion_edge(
        self,
        person_id: str,
        fraktion_name: str,
        wahlperiode: int,
        joined_date: Optional[str] = None,
        left_date: Optional[str] = None,
        role: Optional[str] = "Mitglied",
        **kwargs,
    ) -> MemberOfFraktion:
        """
        Create a MEMBER_OF_FRAKTION edge linking Person to BundestagFraktion.

        Args:
            person_id: Person ID
            fraktion_name: Fraktion name
            wahlperiode: Electoral period
            joined_date: When person joined faction
            left_date: When person left faction (None if current)
            role: Role in faction (Mitglied, Vorsitzende, etc.)
            **kwargs: Additional fields

        Returns:
            MemberOfFraktion edge object
        """
        try:
            edge = MemberOfFraktion(joined_date=joined_date, left_date=left_date, role=role)

            logger.debug(
                "Created MEMBER_OF_FRAKTION edge",
                person_id=person_id,
                fraktion=fraktion_name,
                wahlperiode=wahlperiode,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create MEMBER_OF_FRAKTION edge",
                person_id=person_id,
                fraktion=fraktion_name,
                error=str(e),
            )
            raise

    async def create_in_wahlperiode_edge(
        self,
        entity_id: str,
        entity_type: str,
        wahlperiode_nummer: int,
        active_from: Optional[str] = None,
        active_until: Optional[str] = None,
        **kwargs,
    ) -> InWahlperiode:
        """
        Create an IN_WAHLPERIODE edge linking entity to Wahlperiode.

        Args:
            entity_id: Entity ID (Person, Fraktion, Vorgang, etc.)
            entity_type: Type of entity
            wahlperiode_nummer: Electoral period number
            active_from: Start of activity in period
            active_until: End of activity (None if ongoing)
            **kwargs: Additional fields

        Returns:
            InWahlperiode edge object
        """
        try:
            edge = InWahlperiode(
                entity_type=entity_type, active_from=active_from, active_until=active_until
            )

            logger.debug(
                "Created IN_WAHLPERIODE edge",
                entity_id=entity_id,
                entity_type=entity_type,
                wahlperiode=wahlperiode_nummer,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create IN_WAHLPERIODE edge",
                entity_id=entity_id,
                entity_type=entity_type,
                error=str(e),
            )
            raise

    async def create_leads_fraktion_edge(
        self,
        person_id: str,
        fraktion_name: str,
        leadership_role: str,
        from_date: str,
        to_date: Optional[str] = None,
        **kwargs,
    ) -> LeadsFraktion:
        """
        Create a LEADS_FRAKTION edge for faction leadership.

        Args:
            person_id: Person ID
            fraktion_name: Fraktion name
            leadership_role: Role (Vorsitzende, Stellvertretende Vorsitzende, etc.)
            from_date: Start of leadership
            to_date: End of leadership (None if current)
            **kwargs: Additional fields

        Returns:
            LeadsFraktion edge object
        """
        try:
            edge = LeadsFraktion(
                leadership_role=leadership_role, from_date=from_date, to_date=to_date
            )

            logger.debug(
                "Created LEADS_FRAKTION edge",
                person_id=person_id,
                fraktion=fraktion_name,
                role=leadership_role,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create LEADS_FRAKTION edge",
                person_id=person_id,
                fraktion=fraktion_name,
                error=str(e),
            )
            raise

    async def create_represents_wahlkreis_edge(
        self,
        person_id: str,
        wahlkreis_nummer: str,
        wahlkreis_name: str,
        wahlperiode: int,
        elected_directly: bool,
        vote_percentage: Optional[float] = None,
        **kwargs,
    ) -> RepresentsWahlkreis:
        """
        Create a REPRESENTS_WAHLKREIS edge for constituency representation.

        Args:
            person_id: Person ID
            wahlkreis_nummer: Constituency number
            wahlkreis_name: Constituency name
            wahlperiode: Electoral period
            elected_directly: True if directly elected, False if via Landesliste
            vote_percentage: Percentage of votes received
            **kwargs: Additional fields

        Returns:
            RepresentsWahlkreis edge object
        """
        try:
            edge = RepresentsWahlkreis(
                wahlkreis_nummer=wahlkreis_nummer,
                wahlkreis_name=wahlkreis_name,
                wahlperiode=wahlperiode,
                elected_directly=elected_directly,
                vote_percentage=vote_percentage,
            )

            logger.debug(
                "Created REPRESENTS_WAHLKREIS edge",
                person_id=person_id,
                wahlkreis=wahlkreis_name,
                wahlperiode=wahlperiode,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create REPRESENTS_WAHLKREIS edge",
                person_id=person_id,
                wahlkreis=wahlkreis_name,
                error=str(e),
            )
            raise

    async def create_initiates_vorgang_edge(
        self,
        initiator_id: str,
        vorgang_name: str,
        date_initiated: Optional[str] = None,
        role: str = "Antragsteller",
        co_initiators: Optional[str] = None,
        **kwargs,
    ) -> InitiatesVorgang:
        """
        Create an INITIATES_VORGANG edge for procedure initiation.

        Args:
            initiator_id: Person or Fraktion ID
            vorgang_name: Vorgang name
            date_initiated: When procedure was initiated
            role: Initiator role (Antragsteller, Einbringer, Urheber)
            co_initiators: JSON array of additional initiators
            **kwargs: Additional fields

        Returns:
            InitiatesVorgang edge object
        """
        try:
            edge = InitiatesVorgang(
                date_initiated=date_initiated, role=role, co_initiators=co_initiators
            )

            logger.debug(
                "Created INITIATES_VORGANG edge",
                initiator_id=initiator_id,
                vorgang=vorgang_name,
                role=role,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create INITIATES_VORGANG edge",
                initiator_id=initiator_id,
                vorgang=vorgang_name,
                error=str(e),
            )
            raise

    async def create_relates_to_drucksache_edge(
        self,
        vorgang_id: str,
        drucksache_nummer: str,
        relationship_type: str,
        relevance: Optional[str] = None,
        **kwargs,
    ) -> RelatesToDrucksache:
        """
        Create a RELATES_TO_DRUCKSACHE edge linking Vorgang to Drucksache.

        Args:
            vorgang_id: Vorgang ID
            drucksache_nummer: Drucksache number
            relationship_type: Type (hauptdrucksache, beratungsgrundlage, beschlussempfehlung)
            relevance: Importance (primary, supporting, reference)
            **kwargs: Additional fields

        Returns:
            RelatesToDrucksache edge object
        """
        try:
            edge = RelatesToDrucksache(relationship_type=relationship_type, relevance=relevance)

            logger.debug(
                "Created RELATES_TO_DRUCKSACHE edge",
                vorgang_id=vorgang_id,
                drucksache=drucksache_nummer,
                type=relationship_type,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create RELATES_TO_DRUCKSACHE edge",
                vorgang_id=vorgang_id,
                drucksache=drucksache_nummer,
                error=str(e),
            )
            raise

    async def create_debated_in_plenum_edge(
        self,
        vorgang_id: str,
        plenarprotokoll_id: str,
        debate_date: str,
        reading: Optional[str] = None,
        tagesordnungspunkt: Optional[str] = None,
        outcome: Optional[str] = None,
        **kwargs,
    ) -> DebatedInPlenum:
        """
        Create a DEBATED_IN_PLENUM edge linking Vorgang to Plenarprotokoll.

        Args:
            vorgang_id: Vorgang ID
            plenarprotokoll_id: Plenarprotokoll ID
            debate_date: Date of debate
            reading: Which reading (Erste Beratung, Zweite Beratung, Dritte Beratung)
            tagesordnungspunkt: Agenda item number
            outcome: Result (angenommen, abgelehnt, überwiesen, vertagt)
            **kwargs: Additional fields

        Returns:
            DebatedInPlenum edge object
        """
        try:
            edge = DebatedInPlenum(
                debate_date=debate_date,
                reading=reading,
                tagesordnungspunkt=tagesordnungspunkt,
                outcome=outcome,
            )

            logger.debug(
                "Created DEBATED_IN_PLENUM edge",
                vorgang_id=vorgang_id,
                plenarprotokoll_id=plenarprotokoll_id,
                debate_date=debate_date,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create DEBATED_IN_PLENUM edge",
                vorgang_id=vorgang_id,
                plenarprotokoll_id=plenarprotokoll_id,
                error=str(e),
            )
            raise

    async def create_speaks_in_plenum_edge(
        self,
        person_id: str,
        plenarprotokoll_id: str,
        speech_date: str,
        rede_nummer: Optional[str] = None,
        tagesordnungspunkt: Optional[str] = None,
        rede_art: Optional[str] = None,
        dauer_minuten: Optional[int] = None,
        **kwargs,
    ) -> SpeaksInPlenum:
        """
        Create a SPEAKS_IN_PLENUM edge for plenary speeches.

        Args:
            person_id: Person ID
            plenarprotokoll_id: Plenarprotokoll ID
            speech_date: Date of speech
            rede_nummer: Speech number in protocol
            tagesordnungspunkt: Agenda item
            rede_art: Speech type (Hauptrede, Zwischenruf, etc.)
            dauer_minuten: Speech duration in minutes
            **kwargs: Additional fields

        Returns:
            SpeaksInPlenum edge object
        """
        try:
            edge = SpeaksInPlenum(
                speech_date=speech_date,
                rede_nummer=rede_nummer,
                tagesordnungspunkt=tagesordnungspunkt,
                rede_art=rede_art,
                dauer_minuten=dauer_minuten,
            )

            logger.debug(
                "Created SPEAKS_IN_PLENUM edge",
                person_id=person_id,
                plenarprotokoll_id=plenarprotokoll_id,
                speech_date=speech_date,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create SPEAKS_IN_PLENUM edge",
                person_id=person_id,
                plenarprotokoll_id=plenarprotokoll_id,
                error=str(e),
            )
            raise

    async def create_authors_drucksache_edge(
        self,
        person_id: str,
        drucksache_nummer: str,
        author_role: str = "Mitautor",
        author_position: Optional[int] = None,
        **kwargs,
    ) -> AuthorsDrucksache:
        """
        Create an AUTHORS_DRUCKSACHE edge for document authorship.

        Args:
            person_id: Person ID
            drucksache_nummer: Drucksache number
            author_role: Role (Hauptautor, Mitautor, Berichterstatter)
            author_position: Position in author list (1 = first author)
            **kwargs: Additional fields

        Returns:
            AuthorsDrucksache edge object
        """
        try:
            edge = AuthorsDrucksache(author_role=author_role, author_position=author_position)

            logger.debug(
                "Created AUTHORS_DRUCKSACHE edge",
                person_id=person_id,
                drucksache=drucksache_nummer,
                role=author_role,
            )

            return edge

        except Exception as e:
            logger.error(
                "Failed to create AUTHORS_DRUCKSACHE edge",
                person_id=person_id,
                drucksache=drucksache_nummer,
                error=str(e),
            )
            raise

    async def build(self, raw_data: dict[str, Any], entity: Any) -> list[Any]:
        """
        Generic build method for creating edges from raw data.

        This method can extract multiple edges from a single entity's raw data.
        For example, a Person entity might generate:
        - MEMBER_OF_FRAKTION edge
        - IN_WAHLPERIODE edge(s)
        - REPRESENTS_WAHLKREIS edge

        Args:
            raw_data: Raw dictionary from API
            entity: The entity object that was created from this data

        Returns:
            List of edge objects
        """
        edges = []

        # Extract edges based on entity type and available data
        # This is a simplified example - actual implementation would be more complex

        # Example: If entity has fraktion, create MEMBER_OF_FRAKTION edge
        if hasattr(entity, "fraktion") and entity.fraktion:
            try:
                edge = await self.create_member_of_fraktion_edge(
                    person_id=getattr(entity, "person_id", ""),
                    fraktion_name=entity.fraktion,
                    wahlperiode=raw_data.get("wahlperiode", 0),
                )
                edges.append(edge)
            except Exception as e:
                logger.warning("Could not create MEMBER_OF_FRAKTION edge", error=str(e))

        return edges
