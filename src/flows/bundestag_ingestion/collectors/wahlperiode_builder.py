"""
Builder for Wahlperiode entities - German Bundestag electoral periods.

This builder creates Wahlperiode entities from static data rather than API calls.
Wahlperioden are known historical and current legislative terms of the Bundestag.
"""

from typing import Any, Optional

import structlog

logger = structlog.get_logger()


# Static data for all Wahlperioden from 1949 to present
WAHLPERIODEN = {
    1: {
        "von": "1949-09-07",
        "bis": "1953-10-06",
        "bundeskanzler": "Konrad Adenauer",
        "koalition": "CDU/CSU, FDP, DP",
        "sitze_gesamt": 410,
        "wahltag": "1949-08-14",
        "besonderheiten": "First Bundestag of the Federal Republic of Germany",
    },
    2: {
        "von": "1953-10-06",
        "bis": "1957-10-15",
        "bundeskanzler": "Konrad Adenauer",
        "koalition": "CDU/CSU, FDP, DP, BHE",
        "sitze_gesamt": 509,
        "wahltag": "1953-09-06",
        "besonderheiten": None,
    },
    3: {
        "von": "1957-10-15",
        "bis": "1961-10-17",
        "bundeskanzler": "Konrad Adenauer",
        "koalition": "CDU/CSU, DP",
        "sitze_gesamt": 519,
        "wahltag": "1957-09-15",
        "besonderheiten": "CDU/CSU absolute majority",
    },
    4: {
        "von": "1961-10-17",
        "bis": "1965-10-19",
        "bundeskanzler": "Konrad Adenauer",
        "koalition": "CDU/CSU, FDP",
        "sitze_gesamt": 521,
        "wahltag": "1961-09-17",
        "besonderheiten": None,
    },
    5: {
        "von": "1965-10-19",
        "bis": "1969-10-20",
        "bundeskanzler": "Ludwig Erhard / Kurt Georg Kiesinger",
        "koalition": "CDU/CSU, SPD (Grand Coalition from 1966)",
        "sitze_gesamt": 518,
        "wahltag": "1965-09-19",
        "besonderheiten": "First Grand Coalition",
    },
    6: {
        "von": "1969-10-20",
        "bis": "1972-12-13",
        "bundeskanzler": "Willy Brandt",
        "koalition": "SPD, FDP",
        "sitze_gesamt": 518,
        "wahltag": "1969-09-28",
        "besonderheiten": "First SPD-led government, Ostpolitik",
    },
    7: {
        "von": "1972-12-13",
        "bis": "1976-12-14",
        "bundeskanzler": "Willy Brandt / Helmut Schmidt",
        "koalition": "SPD, FDP",
        "sitze_gesamt": 518,
        "wahltag": "1972-11-19",
        "besonderheiten": None,
    },
    8: {
        "von": "1976-12-14",
        "bis": "1980-11-04",
        "bundeskanzler": "Helmut Schmidt",
        "koalition": "SPD, FDP",
        "sitze_gesamt": 518,
        "wahltag": "1976-10-03",
        "besonderheiten": None,
    },
    9: {
        "von": "1980-11-04",
        "bis": "1983-03-29",
        "bundeskanzler": "Helmut Schmidt / Helmut Kohl",
        "koalition": "SPD, FDP (until 1982), then CDU/CSU, FDP",
        "sitze_gesamt": 519,
        "wahltag": "1980-10-05",
        "besonderheiten": "Constructive vote of no confidence in 1982",
    },
    10: {
        "von": "1983-03-29",
        "bis": "1987-02-18",
        "bundeskanzler": "Helmut Kohl",
        "koalition": "CDU/CSU, FDP",
        "sitze_gesamt": 520,
        "wahltag": "1983-03-06",
        "besonderheiten": "Die Grünen enter Bundestag",
    },
    11: {
        "von": "1987-02-18",
        "bis": "1990-12-20",
        "bundeskanzler": "Helmut Kohl",
        "koalition": "CDU/CSU, FDP",
        "sitze_gesamt": 519,
        "wahltag": "1987-01-25",
        "besonderheiten": None,
    },
    12: {
        "von": "1990-12-20",
        "bis": "1994-11-10",
        "bundeskanzler": "Helmut Kohl",
        "koalition": "CDU/CSU, FDP",
        "sitze_gesamt": 662,
        "wahltag": "1990-12-02",
        "besonderheiten": "First all-German Bundestag after reunification",
    },
    13: {
        "von": "1994-11-10",
        "bis": "1998-10-26",
        "bundeskanzler": "Helmut Kohl",
        "koalition": "CDU/CSU, FDP",
        "sitze_gesamt": 672,
        "wahltag": "1994-10-16",
        "besonderheiten": None,
    },
    14: {
        "von": "1998-10-26",
        "bis": "2002-10-17",
        "bundeskanzler": "Gerhard Schröder",
        "koalition": "SPD, GRÜNE",
        "sitze_gesamt": 669,
        "wahltag": "1998-09-27",
        "besonderheiten": "First Red-Green coalition",
    },
    15: {
        "von": "2002-10-17",
        "bis": "2005-10-18",
        "bundeskanzler": "Gerhard Schröder",
        "koalition": "SPD, GRÜNE",
        "sitze_gesamt": 603,
        "wahltag": "2002-09-22",
        "besonderheiten": None,
    },
    16: {
        "von": "2005-10-18",
        "bis": "2009-10-27",
        "bundeskanzler": "Angela Merkel",
        "koalition": "CDU/CSU, SPD",
        "sitze_gesamt": 614,
        "wahltag": "2005-09-18",
        "besonderheiten": "Second Grand Coalition, first female Chancellor",
    },
    17: {
        "von": "2009-10-27",
        "bis": "2013-10-22",
        "bundeskanzler": "Angela Merkel",
        "koalition": "CDU/CSU, FDP",
        "sitze_gesamt": 622,
        "wahltag": "2009-09-27",
        "besonderheiten": None,
    },
    18: {
        "von": "2013-10-22",
        "bis": "2017-10-24",
        "bundeskanzler": "Angela Merkel",
        "koalition": "CDU/CSU, SPD",
        "sitze_gesamt": 631,
        "wahltag": "2013-09-22",
        "besonderheiten": "Third Grand Coalition",
    },
    19: {
        "von": "2017-10-24",
        "bis": "2021-10-26",
        "bundeskanzler": "Angela Merkel",
        "koalition": "CDU/CSU, SPD",
        "sitze_gesamt": 709,
        "wahltag": "2017-09-24",
        "besonderheiten": "AfD enters Bundestag as largest opposition party",
    },
    20: {
        "von": "2021-10-26",
        "bis": None,  # Current ongoing Wahlperiode
        "bundeskanzler": "Olaf Scholz",
        "koalition": "SPD, GRÜNE, FDP",
        "sitze_gesamt": 736,
        "wahltag": "2021-09-26",
        "besonderheiten": "Traffic light coalition (Ampelkoalition), largest Bundestag in history",
    },
}


class WahlperiodeBuilder:
    """
    Builder for creating Wahlperiode entities from static data.

    Wahlperioden are German Bundestag electoral periods. Unlike other entities,
    they don't come from the API but are defined as static historical data.
    """

    def __init__(self):
        """Initialize the Wahlperiode builder."""
        logger.info("Initialized WahlperiodeBuilder", total_periods=len(WAHLPERIODEN))

    async def build_wahlperiode_entities(self, entity_builder: Any) -> dict[str, Any]:
        """
        Build Wahlperiode entities for all known electoral periods.

        Args:
            entity_builder: Entity builder instance with create_wahlperiode_entity method

        Returns:
            Statistics dictionary with:
            - entities_created: Number of Wahlperiode entities created
            - periods_processed: List of period numbers processed
            - current_period: Current ongoing Wahlperiode number
            - historical_periods: Count of historical periods
        """
        logger.info("Starting Wahlperiode entity creation")

        entities_created = 0
        periods_processed = []
        current_period = None

        for wahlperiode_nummer, data in WAHLPERIODEN.items():
            try:
                # Create entity using the entity builder
                entity = await entity_builder.create_wahlperiode_entity(
                    wahlperiode_nummer=wahlperiode_nummer, **data
                )

                entities_created += 1
                periods_processed.append(wahlperiode_nummer)

                # Track current period (the one without end date)
                if data["bis"] is None:
                    current_period = wahlperiode_nummer

                logger.debug(
                    "Created Wahlperiode entity",
                    wahlperiode=wahlperiode_nummer,
                    von=data["von"],
                    bis=data["bis"],
                    bundeskanzler=data["bundeskanzler"],
                )

            except Exception as e:
                logger.error(
                    "Failed to create Wahlperiode entity",
                    wahlperiode=wahlperiode_nummer,
                    error=str(e),
                )
                continue

        historical_periods = len([p for p in WAHLPERIODEN.values() if p["bis"] is not None])

        stats = {
            "entities_created": entities_created,
            "periods_processed": periods_processed,
            "total_periods": len(WAHLPERIODEN),
            "current_period": current_period,
            "historical_periods": historical_periods,
            "builder_type": "WahlperiodeBuilder",
        }

        logger.info("Completed Wahlperiode entity creation", **stats)

        return stats

    def get_wahlperiode_data(self, wahlperiode_nummer: int) -> Optional[dict[str, Any]]:
        """
        Get data for a specific Wahlperiode.

        Args:
            wahlperiode_nummer: Electoral period number

        Returns:
            Dictionary with Wahlperiode data or None if not found
        """
        return WAHLPERIODEN.get(wahlperiode_nummer)

    def get_all_wahlperioden(self) -> dict[int, dict[str, Any]]:
        """
        Get all Wahlperiode data.

        Returns:
            Dictionary mapping period numbers to their data
        """
        return WAHLPERIODEN.copy()

    def get_current_wahlperiode(self) -> Optional[int]:
        """
        Get the current (ongoing) Wahlperiode number.

        Returns:
            Current Wahlperiode number or None if not found
        """
        for nummer, data in WAHLPERIODEN.items():
            if data["bis"] is None:
                return nummer
        return None

    def get_wahlperioden_by_chancellor(self, bundeskanzler: str) -> list[int]:
        """
        Get all Wahlperioden for a specific Chancellor.

        Args:
            bundeskanzler: Name of the Chancellor (case-sensitive)

        Returns:
            List of Wahlperiode numbers
        """
        matching_periods = []
        for nummer, data in WAHLPERIODEN.items():
            if bundeskanzler in data.get("bundeskanzler", ""):
                matching_periods.append(nummer)
        return matching_periods
