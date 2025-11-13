"""
Entity builder for German Bundestag entities using political schema v4.

This module provides the BundestagEntityBuilder class for creating entity objects
from raw Bundestag data according to the political_schema_v4 definitions.
"""

import json
import structlog
from typing import Any, Dict, List, Optional

from src.graphrag.political_schema_v4 import (
    Wahlperiode,
    BundestagFraktion,
    BundestagPerson,
    Vorgang,
    Drucksache,
    Plenarprotokoll,
    Vorgangsposition,
    Aktivitaet,
)

logger = structlog.get_logger()


class BundestagEntityBuilder:
    """
    Builder for creating Bundestag entity objects from raw API data.

    Transforms raw dictionary data from the Bundestag DIP API into
    Pydantic entity objects according to political_schema_v4.
    """

    def __init__(self):
        """Initialize the entity builder."""
        logger.info("Initialized BundestagEntityBuilder")

    async def create_wahlperiode_entity(
        self,
        wahlperiode_nummer: int,
        von: str,
        bis: Optional[str] = None,
        bundeskanzler: Optional[str] = None,
        koalition: Optional[str] = None,
        sitze_gesamt: Optional[int] = None,
        wahltag: Optional[str] = None,
        besonderheiten: Optional[str] = None,
        **kwargs,
    ) -> Wahlperiode:
        """
        Create a Wahlperiode entity.

        Args:
            wahlperiode_nummer: Period number (1-20)
            von: Start date (ISO format)
            bis: End date (ISO format, None if current)
            bundeskanzler: Chancellor name
            koalition: Coalition parties
            sitze_gesamt: Total seats in Bundestag
            wahltag: Election date
            besonderheiten: Special characteristics
            **kwargs: Additional fields

        Returns:
            Wahlperiode entity object
        """
        try:
            entity = Wahlperiode(
                wahlperiode_nummer=wahlperiode_nummer,
                von=von,
                bis=bis,
                bundeskanzler=bundeskanzler,
                koalition=koalition,
                sitze_gesamt=sitze_gesamt,
                wahltag=wahltag,
                besonderheiten=besonderheiten,
            )

            logger.debug(
                "Created Wahlperiode entity", wahlperiode=wahlperiode_nummer, von=von, bis=bis
            )

            return entity

        except Exception as e:
            logger.error(
                "Failed to create Wahlperiode entity", wahlperiode=wahlperiode_nummer, error=str(e)
            )
            raise

    async def create_fraktion_entity(
        self,
        fraktion_name: str,
        kurz: str,
        wahlperiode: int,
        sitze: int,
        koalition_opposition: str,
        prozent: Optional[float] = None,
        vorsitzende: Optional[str] = None,
        parlamentarische_geschaeftsfuehrer: Optional[str] = None,
        koalitionspartner: Optional[str] = None,
        gruendungsdatum: Optional[str] = None,
        mitglieder_anzahl: Optional[int] = None,
        farbe: Optional[str] = None,
        member_ids: Optional[List[str]] = None,
        **kwargs,
    ) -> BundestagFraktion:
        """
        Create a BundestagFraktion entity.

        Args:
            fraktion_name: Full faction name
            kurz: Short abbreviation
            wahlperiode: Electoral period
            sitze: Number of seats
            koalition_opposition: "Koalition" or "Opposition"
            prozent: Percentage of total seats
            vorsitzende: JSON array of faction leaders
            parlamentarische_geschaeftsfuehrer: JSON array of parliamentary managers
            koalitionspartner: Coalition partners if in government
            gruendungsdatum: Formation date
            mitglieder_anzahl: Total number of members
            farbe: Party color for visualization
            member_ids: List of member IDs (not stored in entity, used for edges)
            **kwargs: Additional fields

        Returns:
            BundestagFraktion entity object
        """
        try:
            entity = BundestagFraktion(
                fraktion_name=fraktion_name,
                kurz=kurz,
                wahlperiode=wahlperiode,
                sitze=sitze,
                prozent=prozent,
                vorsitzende=vorsitzende,
                parlamentarische_geschaeftsfuehrer=parlamentarische_geschaeftsfuehrer,
                koalition_opposition=koalition_opposition,
                koalitionspartner=koalitionspartner,
                gruendungsdatum=gruendungsdatum,
                mitglieder_anzahl=mitglieder_anzahl,
                farbe=farbe,
            )

            logger.debug(
                "Created BundestagFraktion entity",
                fraktion=fraktion_name,
                wahlperiode=wahlperiode,
                sitze=sitze,
            )

            return entity

        except Exception as e:
            logger.error(
                "Failed to create BundestagFraktion entity",
                fraktion=fraktion_name,
                wahlperiode=wahlperiode,
                error=str(e),
            )
            raise

    async def create_person_entity(
        self,
        person_name: str,
        person_id: str,
        fraktion: Optional[str] = None,
        partei: Optional[str] = None,
        wahlperioden: Optional[str] = None,
        ausschuss_mitgliedschaften: Optional[str] = None,
        titel: Optional[str] = None,
        beruf: Optional[str] = None,
        geburtsdatum: Optional[str] = None,
        geburtsort: Optional[str] = None,
        wahlkreis: Optional[str] = None,
        landesliste: Optional[str] = None,
        website: Optional[str] = None,
        foto_url: Optional[str] = None,
        aktualisiert: Optional[str] = None,
        **kwargs,
    ) -> BundestagPerson:
        """
        Create a BundestagPerson entity.

        Args:
            person_name: Full name
            person_id: Unique person ID
            fraktion: Current parliamentary group
            partei: Political party affiliation
            wahlperioden: JSON array of Wahlperiode numbers served
            ausschuss_mitgliedschaften: JSON array of committee memberships
            titel: Academic/professional title
            beruf: Professional occupation
            geburtsdatum: Date of birth
            geburtsort: Place of birth
            wahlkreis: Directly elected constituency
            landesliste: State list position
            website: Personal website
            foto_url: Photo URL
            aktualisiert: Last updated timestamp
            **kwargs: Additional fields

        Returns:
            BundestagPerson entity object
        """
        try:
            entity = BundestagPerson(
                person_name=person_name,
                person_id=person_id,
                fraktion=fraktion,
                partei=partei,
                wahlperioden=wahlperioden,
                ausschuss_mitgliedschaften=ausschuss_mitgliedschaften,
                titel=titel,
                beruf=beruf,
                geburtsdatum=geburtsdatum,
                geburtsort=geburtsort,
                wahlkreis=wahlkreis,
                landesliste=landesliste,
                website=website,
                foto_url=foto_url,
                aktualisiert=aktualisiert,
            )

            logger.debug(
                "Created BundestagPerson entity",
                person=person_name,
                person_id=person_id,
                fraktion=fraktion,
            )

            return entity

        except Exception as e:
            logger.error(
                "Failed to create BundestagPerson entity",
                person=person_name,
                person_id=person_id,
                error=str(e),
            )
            raise

    async def create_vorgang_entity(
        self,
        vorgang_name: str,
        vorgangstyp: str,
        wahlperiode: int,
        beratungsstand: str,
        vorgangsnummer: Optional[str] = None,
        initiative: Optional[str] = None,
        sachgebiet: Optional[str] = None,
        datum: Optional[str] = None,
        abgeschlossen_datum: Optional[str] = None,
        abstract: Optional[str] = None,
        ziel: Optional[str] = None,
        wichtige_drucksachen: Optional[str] = None,
        plenum_anzahl: Optional[int] = None,
        ausschuss_federf: Optional[str] = None,
        inkrafttreten: Optional[str] = None,
        verkuendung_bundesgesetzblatt: Optional[str] = None,
        ratifikation: Optional[str] = None,
        gesta_id: Optional[str] = None,
        aktualisiert: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs,
    ) -> Vorgang:
        """
        Create a Vorgang entity.

        Args:
            vorgang_name: Official procedure title
            vorgangstyp: Procedure type
            wahlperiode: Electoral period
            beratungsstand: Current status
            (additional parameters as per schema)

        Returns:
            Vorgang entity object
        """
        try:
            entity = Vorgang(
                vorgang_name=vorgang_name,
                vorgangstyp=vorgangstyp,
                wahlperiode=wahlperiode,
                vorgangsnummer=vorgangsnummer,
                initiative=initiative,
                beratungsstand=beratungsstand,
                sachgebiet=sachgebiet,
                datum=datum,
                abgeschlossen_datum=abgeschlossen_datum,
                abstract=abstract,
                ziel=ziel,
                wichtige_drucksachen=wichtige_drucksachen,
                plenum_anzahl=plenum_anzahl,
                ausschuss_federf=ausschuss_federf,
                inkrafttreten=inkrafttreten,
                verkuendung_bundesgesetzblatt=verkuendung_bundesgesetzblatt,
                ratifikation=ratifikation,
                gesta_id=gesta_id,
                aktualisiert=aktualisiert,
                url=url,
            )

            logger.debug(
                "Created Vorgang entity",
                vorgang=vorgang_name,
                vorgangstyp=vorgangstyp,
                wahlperiode=wahlperiode,
            )

            return entity

        except Exception as e:
            logger.error("Failed to create Vorgang entity", vorgang=vorgang_name, error=str(e))
            raise

    async def build(self, raw_data: Dict[str, Any]) -> Any:
        """
        Generic build method for creating entities from raw data.

        Determines entity type from raw data and calls appropriate creation method.

        Args:
            raw_data: Raw dictionary from API

        Returns:
            Entity object of appropriate type
        """
        # Determine entity type from data structure
        if "wahlperiode_nummer" in raw_data or "wahlperiode" in raw_data.get("id", ""):
            return await self.create_wahlperiode_entity(**raw_data)

        elif "fraktion_name" in raw_data:
            return await self.create_fraktion_entity(**raw_data)

        elif "person_id" in raw_data or "person_name" in raw_data:
            return await self.create_person_entity(**raw_data)

        elif "vorgangstyp" in raw_data:
            return await self.create_vorgang_entity(**raw_data)

        else:
            logger.warning(
                "Unable to determine entity type from raw data", raw_data_keys=list(raw_data.keys())
            )
            raise ValueError(f"Cannot determine entity type from raw data: {raw_data.keys()}")
