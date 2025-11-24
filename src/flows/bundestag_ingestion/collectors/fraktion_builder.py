"""
Builder for BundestagFraktion entities derived from Person data.

This builder creates BundestagFraktion entities by analyzing Person data rather
than direct API calls. Fraktionen are derived from the fraktion field in Person
objects, and seat counts are calculated from member counts.
"""

from collections import Counter
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


# Known faction colors for visualization
FRAKTION_COLORS = {
    "CDU/CSU": "#000000",  # Black
    "SPD": "#E3000F",  # Red
    "GRÜNE": "#46962B",  # Green
    "BÜNDNIS 90/DIE GRÜNEN": "#46962B",
    "FDP": "#FFED00",  # Yellow
    "AfD": "#009EE0",  # Light blue
    "DIE LINKE": "#BE3075",  # Magenta/Purple
    "LINKE": "#BE3075",
    "PDS": "#BE3075",  # Historical Left party
}

# Common faction abbreviations
FRAKTION_ABBREVIATIONS = {
    "CDU/CSU": "CDU/CSU",
    "SPD": "SPD",
    "BÜNDNIS 90/DIE GRÜNEN": "GRÜNE",
    "GRÜNE": "GRÜNE",
    "FDP": "FDP",
    "AfD": "AfD",
    "DIE LINKE": "LINKE",
    "LINKE": "LINKE",
    "PDS": "PDS",
}


class FraktionBuilder:
    """
    Builder for creating BundestagFraktion entities from Person data.

    Unlike API collectors, this builder analyzes Person entities to derive
    Fraktion information including membership counts and seat allocations.
    """

    def __init__(self):
        """Initialize the Fraktion builder."""
        logger.info("Initialized FraktionBuilder")

    async def build_from_person_data(
        self,
        persons: list[dict[str, Any]],
        wahlperiode: int,
        entity_builder: Any,
        edge_builder: Any,
    ) -> dict[str, Any]:
        """
        Build BundestagFraktion entities from Person data.

        This method:
        1. Extracts unique fraktionen from persons list
        2. Counts members (sitze) per fraktion
        3. Creates BundestagFraktion entities
        4. Links persons to fraktionen using MEMBER_OF_FRAKTION edges

        Args:
            persons: List of Person entity dictionaries with fraktion field
            wahlperiode: Electoral period number
            entity_builder: Entity builder with create_fraktion_entity method
            edge_builder: Edge builder with create_member_of_fraktion_edge method

        Returns:
            Statistics dictionary with:
            - entities_created: Number of BundestagFraktion entities created
            - edges_created: Number of MEMBER_OF_FRAKTION edges created
            - fraktionen_found: List of fraktion names
            - total_members: Total number of MdB members across all fraktionen
            - wahlperiode: Electoral period processed
        """
        logger.info(
            "Starting Fraktion entity creation from Person data",
            wahlperiode=wahlperiode,
            total_persons=len(persons),
        )

        # Extract fraktionen from persons
        fraktion_data = self._extract_fraktion_data(persons, wahlperiode)

        if not fraktion_data:
            logger.warning("No fraktionen found in Person data", wahlperiode=wahlperiode)
            return {
                "entities_created": 0,
                "edges_created": 0,
                "fraktionen_found": [],
                "total_members": 0,
                "wahlperiode": wahlperiode,
                "builder_type": "FraktionBuilder",
            }

        # Create fraktion entities
        entities_created = 0
        edges_created = 0
        fraktionen_found = []

        for fraktion_name, data in fraktion_data.items():
            try:
                # Create fraktion entity
                fraktion_entity = await entity_builder.create_fraktion_entity(
                    fraktion_name=fraktion_name,
                    kurz=self._get_abbreviation(fraktion_name),
                    wahlperiode=wahlperiode,
                    sitze=data["member_count"],
                    prozent=data["percentage"],
                    koalition_opposition=data.get("koalition_opposition", "Unknown"),
                    mitglieder_anzahl=data["member_count"],
                    farbe=self._get_color(fraktion_name),
                    member_ids=data["member_ids"],
                )

                entities_created += 1
                fraktionen_found.append(fraktion_name)

                logger.debug(
                    "Created Fraktion entity",
                    fraktion=fraktion_name,
                    sitze=data["member_count"],
                    wahlperiode=wahlperiode,
                )

                # Create MEMBER_OF_FRAKTION edges for all members
                for person_id in data["member_ids"]:
                    try:
                        edge = await edge_builder.create_member_of_fraktion_edge(
                            person_id=person_id,
                            fraktion_name=fraktion_name,
                            wahlperiode=wahlperiode,
                        )
                        edges_created += 1

                    except Exception as e:
                        logger.error(
                            "Failed to create MEMBER_OF_FRAKTION edge",
                            person_id=person_id,
                            fraktion=fraktion_name,
                            error=str(e),
                        )
                        continue

            except Exception as e:
                logger.error(
                    "Failed to create Fraktion entity",
                    fraktion=fraktion_name,
                    wahlperiode=wahlperiode,
                    error=str(e),
                )
                continue

        total_members = sum(data["member_count"] for data in fraktion_data.values())

        stats = {
            "entities_created": entities_created,
            "edges_created": edges_created,
            "fraktionen_found": fraktionen_found,
            "total_members": total_members,
            "wahlperiode": wahlperiode,
            "fraktion_details": {
                name: {"sitze": data["member_count"], "prozent": data["percentage"]}
                for name, data in fraktion_data.items()
            },
            "builder_type": "FraktionBuilder",
        }

        logger.info("Completed Fraktion entity creation", **stats)

        return stats

    def _extract_fraktion_data(
        self, persons: list[dict[str, Any]], wahlperiode: int
    ) -> dict[str, dict[str, Any]]:
        """
        Extract fraktion data from Person entities.

        Args:
            persons: List of Person entity dictionaries
            wahlperiode: Electoral period to filter by

        Returns:
            Dictionary mapping fraktion names to their data:
            {
                "CDU/CSU": {
                    "member_count": 197,
                    "percentage": 26.8,
                    "member_ids": ["id1", "id2", ...],
                    "koalition_opposition": "Opposition"
                }
            }
        """
        # Count fraktion memberships
        fraktion_counter = Counter()
        fraktion_members = {}

        for person in persons:
            # Skip if person doesn't have fraktion or is not in the wahlperiode
            fraktion = person.get("fraktion")
            person_wahlperioden = person.get("wahlperioden", [])

            if not fraktion or fraktion == "fraktionslos":
                continue

            # Check if person was in this wahlperiode
            if wahlperiode not in person_wahlperioden:
                continue

            # Count and track members
            fraktion_counter[fraktion] += 1

            if fraktion not in fraktion_members:
                fraktion_members[fraktion] = []

            fraktion_members[fraktion].append(person.get("person_id"))

        if not fraktion_counter:
            return {}

        # Calculate total seats
        total_seats = sum(fraktion_counter.values())

        # Build fraktion data with percentages
        fraktion_data = {}

        for fraktion_name, count in fraktion_counter.items():
            percentage = round((count / total_seats) * 100, 1) if total_seats > 0 else 0.0

            fraktion_data[fraktion_name] = {
                "member_count": count,
                "percentage": percentage,
                "member_ids": fraktion_members[fraktion_name],
                "koalition_opposition": self._determine_koalition_status(
                    fraktion_name, wahlperiode
                ),
            }

        return fraktion_data

    def _get_abbreviation(self, fraktion_name: str) -> str:
        """
        Get standard abbreviation for a fraktion.

        Args:
            fraktion_name: Full fraktion name

        Returns:
            Standard abbreviation or original name if not found
        """
        return FRAKTION_ABBREVIATIONS.get(fraktion_name, fraktion_name)

    def _get_color(self, fraktion_name: str) -> Optional[str]:
        """
        Get visualization color for a fraktion.

        Args:
            fraktion_name: Fraktion name

        Returns:
            Hex color code or None if not found
        """
        return FRAKTION_COLORS.get(fraktion_name)

    def _determine_koalition_status(self, fraktion_name: str, wahlperiode: int) -> str:
        """
        Determine if a fraktion is in Koalition or Opposition.

        This is a heuristic based on known historical coalitions.
        For more accuracy, this could query the Wahlperiode entity.

        Args:
            fraktion_name: Fraktion name
            wahlperiode: Electoral period number

        Returns:
            "Koalition" or "Opposition"
        """
        # Known coalitions by Wahlperiode
        koalition_map = {
            19: ["CDU/CSU", "SPD"],  # 2017-2021 Grand Coalition
            20: ["SPD", "GRÜNE", "BÜNDNIS 90/DIE GRÜNEN", "FDP"],  # 2021- Traffic Light
        }

        koalition_parties = koalition_map.get(wahlperiode, [])

        # Check if fraktion is in coalition
        if fraktion_name in koalition_parties:
            return "Koalition"
        else:
            return "Opposition"

    async def get_fraktion_statistics(
        self, persons: list[dict[str, Any]], wahlperiode: int
    ) -> dict[str, Any]:
        """
        Get statistics about fraktionen without creating entities.

        Useful for analysis before entity creation.

        Args:
            persons: List of Person entity dictionaries
            wahlperiode: Electoral period number

        Returns:
            Statistics dictionary with fraktion breakdown
        """
        fraktion_data = self._extract_fraktion_data(persons, wahlperiode)

        total_members = sum(data["member_count"] for data in fraktion_data.values())

        return {
            "wahlperiode": wahlperiode,
            "total_fraktionen": len(fraktion_data),
            "total_members": total_members,
            "fraktionen": {
                name: {
                    "sitze": data["member_count"],
                    "prozent": data["percentage"],
                    "koalition_opposition": data["koalition_opposition"],
                }
                for name, data in fraktion_data.items()
            },
        }
