"""
Sample Bundestag API response data for testing.

Contains realistic API responses for all 8 Bundestag data endpoints to be used
in unit and integration tests. Based on actual Bundestag DIP API structure.
"""

from typing import Any

# ===================================================================
# VORGANG (Legislative Procedure) Sample Data
# ===================================================================

SAMPLE_VORGANG_RESPONSE: dict[str, Any] = {
    "documents": [
        {
            "id": "287654",
            "titel": "Gesetz zur Stärkung des Wettbewerbs in der Gesetzlichen Krankenversicherung",
            "vorgangstyp": "Gesetzgebung",
            "wahlperiode": 20,
            "beratungsstand": "Verkündet - Gesetz/Verordnung erlassen",
            "initiative": "Bundesregierung",
            "sachgebiet": "Gesundheit",
            "datum": "2024-03-15T00:00:00Z",
            "abgeschlossen": "2024-06-20T00:00:00Z",
            "abstract": "Ziel des Gesetzes ist die Stärkung des Wettbewerbs zwischen den Krankenkassen.",
            "ziel": "Verbesserung der Versorgungsqualität durch verstärkten Wettbewerb",
            "wichtige_drucksachen": ["20/1234", "20/1567"],
            "plenum": ["Erste Beratung", "Zweite Beratung", "Dritte Beratung"],
            "aktualisiert": "2024-06-21T10:30:00Z",
            "fundstelle": {"url": "https://dip.bundestag.de/vorgang/287654"},
        }
    ],
    "numFound": 1,
    "cursor": "AoE/3456789abcdef",
}


# ===================================================================
# DRUCKSACHE (Parliamentary Document) Sample Data
# ===================================================================

SAMPLE_DRUCKSACHE_RESPONSE: dict[str, Any] = {
    "documents": [
        {
            "id": "320145",
            "titel": "Entwurf eines Gesetzes zur Digitalisierung der Energiewende",
            "drucksachetyp": "Gesetzentwurf",
            "wahlperiode": 20,
            "herausgeber": "BT",
            "dokumentnummer": "20/5678",
            "datum": "2024-04-10T00:00:00Z",
            "dokumentart": "Gesetzentwurf",
            "autoren": ["Bundesregierung"],
            "fundstelle": {
                "pdf_url": "https://dserver.bundestag.de/btd/20/056/2005678.pdf",
                "dokumentart": "Drucksache",
            },
            "aktualisiert": "2024-04-11T08:15:00Z",
        }
    ],
    "numFound": 1,
    "cursor": "AoE/xyz123456",
}


# ===================================================================
# PERSON (Member of Parliament) Sample Data
# ===================================================================

SAMPLE_PERSON_RESPONSE: dict[str, Any] = {
    "documents": [
        {
            "id": "11004809",
            "nachname": "Müller",
            "vorname": "Anna",
            "akadTitel": "Dr.",
            "fraktion": "SPD",
            "partei": "SPD",
            "wahlperioden": [19, 20],
            "mdbId": "11004809",
            "geburtsdatum": "1975-06-15",
            "geburtsort": "Hamburg",
            "beruf": "Rechtsanwältin",
            "wahlkreis": "Hamburg-Mitte",
            "landesliste": "Hamburg",
            "aktualisiert": "2024-05-01T00:00:00Z",
        }
    ],
    "numFound": 1,
    "cursor": "AoE/person123",
}


# ===================================================================
# PLENARPROTOKOLL (Plenary Protocol) Sample Data
# ===================================================================

SAMPLE_PLENARPROTOKOLL_RESPONSE: dict[str, Any] = {
    "documents": [
        {
            "id": "258741",
            "titel": "Plenarprotokoll 20/125",
            "wahlperiode": 20,
            "sitzungsnummer": 125,
            "datum": "2024-05-15T09:00:00Z",
            "dokumentart": "Plenarprotokoll",
            "pdf_url": "https://dserver.bundestag.de/btp/20/20125.pdf",
            "herausgeber": "BT",
            "tagesordnungspunkte": [
                {
                    "top_nummer": 1,
                    "titel": "Gesetz zur Digitalisierung der Energiewende",
                    "beratungsgang": "Zweite Beratung",
                },
                {
                    "top_nummer": 2,
                    "titel": "Antrag zur Förderung erneuerbarer Energien",
                    "beratungsgang": "Erste Beratung",
                },
            ],
            "aktualisiert": "2024-05-16T00:00:00Z",
        }
    ],
    "numFound": 1,
    "cursor": "AoE/protokoll456",
}


# ===================================================================
# VORGANGSPOSITION (Procedure Position/Step) Sample Data
# ===================================================================

SAMPLE_VORGANGSPOSITION_RESPONSE: dict[str, Any] = {
    "documents": [
        {
            "id": "VP-456789",
            "vorgangsposition_name": "Erste Beratung",
            "vorgangstyp": "Gesetzgebung",
            "sequenz": 1,
            "datum": "2024-04-20T00:00:00Z",
            "zuordnung": "BT",
            "urheber": "Bundesregierung",
            "fundstelle": "Plenarprotokoll 20/120",
            "vorgang_id": "287654",
            "aktualisiert": "2024-04-21T00:00:00Z",
        }
    ],
    "numFound": 1,
    "cursor": "AoE/vpos123",
}


# ===================================================================
# AKTIVITAET (Activity) Sample Data
# ===================================================================

SAMPLE_AKTIVITAET_RESPONSE: dict[str, Any] = {
    "documents": [
        {
            "id": "AKT-789456",
            "aktivitaet_name": "Abstimmung über Gesetzentwurf",
            "typ": "Abstimmung",
            "datum": "2024-05-15T15:30:00Z",
            "sitzung": "Plenarsitzung 20/125",
            "ergebnis": "Angenommen",
            "ja_stimmen": 398,
            "nein_stimmen": 256,
            "enthaltungen": 15,
            "nicht_abgestimmt": 42,
            "vorgang_id": "287654",
            "drucksache_ids": ["20/5678"],
            "aktualisiert": "2024-05-15T18:00:00Z",
        }
    ],
    "numFound": 1,
    "cursor": "AoE/akt456",
}


# ===================================================================
# WAHLPERIODE (Electoral Period) Sample Data
# ===================================================================

SAMPLE_WAHLPERIODE_DATA: dict[str, Any] = {
    "wahlperiode_nummer": 20,
    "von": "2021-10-26",
    "bis": None,  # Current period
    "bundeskanzler": "Olaf Scholz",
    "koalition": "SPD, Bündnis 90/Die Grünen, FDP",
    "sitze_gesamt": 736,
    "wahltag": "2021-09-26",
    "besonderheiten": "Ampelkoalition",
}


# ===================================================================
# FRAKTION (Parliamentary Group) Sample Data
# ===================================================================

SAMPLE_FRAKTION_DATA: dict[str, Any] = {
    "fraktion_name": "SPD",
    "kurz": "SPD",
    "wahlperiode": 20,
    "sitze": 206,
    "prozent": 28.0,
    "vorsitzende": ["Dr. Rolf Mützenich"],
    "parlamentarische_geschaeftsfuehrer": ["Katja Mast"],
    "koalition_opposition": "Koalition",
    "koalitionspartner": "Bündnis 90/Die Grünen, FDP",
    "gruendungsdatum": "1863-05-23",
    "mitglieder_anzahl": 206,
    "farbe": "#E3000F",
    "member_ids": ["11004809", "11004810", "11004811"],  # Sample member IDs
}


# ===================================================================
# PAGINATED RESPONSE (Multi-page) Sample Data
# ===================================================================

SAMPLE_PAGINATED_RESPONSE_PAGE_1: dict[str, Any] = {
    "documents": [
        {"id": f"V{i}", "titel": f"Vorgang {i}", "vorgangstyp": "Gesetzgebung"}
        for i in range(1, 101)
    ],
    "numFound": 250,
    "cursor": "AoE/page1cursor",
}

SAMPLE_PAGINATED_RESPONSE_PAGE_2: dict[str, Any] = {
    "documents": [
        {"id": f"V{i}", "titel": f"Vorgang {i}", "vorgangstyp": "Gesetzgebung"}
        for i in range(101, 201)
    ],
    "numFound": 250,
    "cursor": "AoE/page2cursor",
}

SAMPLE_PAGINATED_RESPONSE_PAGE_3: dict[str, Any] = {
    "documents": [
        {"id": f"V{i}", "titel": f"Vorgang {i}", "vorgangstyp": "Gesetzgebung"}
        for i in range(201, 251)
    ],
    "numFound": 250,
    "cursor": None,  # Last page
}


# ===================================================================
# ERROR RESPONSES
# ===================================================================

SAMPLE_ERROR_RATE_LIMIT: dict[str, Any] = {
    "error": "Rate limit exceeded",
    "message": "Too many requests. Please try again later.",
    "retry_after": 60,
}

SAMPLE_ERROR_NOT_FOUND: dict[str, Any] = {"error": "Not found", "message": "Resource not found"}

SAMPLE_ERROR_INVALID_PARAMS: dict[str, Any] = {
    "error": "Invalid parameters",
    "message": "Invalid filter parameters provided",
}


# ===================================================================
# CONVENIENCE FUNCTIONS
# ===================================================================


def get_sample_vorgaenge(count: int = 10) -> dict[str, Any]:
    """Generate multiple sample Vorgang responses."""
    return {
        "documents": [
            {
                "id": f"V{i}",
                "titel": f"Gesetz zur Änderung {i}",
                "vorgangstyp": "Gesetzgebung",
                "wahlperiode": 20,
                "beratungsstand": "In Beratung",
                "datum": f"2024-{i:02d}-01T00:00:00Z",
            }
            for i in range(1, count + 1)
        ],
        "numFound": count,
        "cursor": None,
    }


def get_sample_drucksachen(count: int = 10) -> dict[str, Any]:
    """Generate multiple sample Drucksache responses."""
    return {
        "documents": [
            {
                "id": f"D{i}",
                "titel": f"Drucksache {i}",
                "drucksachetyp": "Gesetzentwurf",
                "wahlperiode": 20,
                "dokumentnummer": f"20/{1000+i}",
                "datum": f"2024-{i:02d}-15T00:00:00Z",
            }
            for i in range(1, count + 1)
        ],
        "numFound": count,
        "cursor": None,
    }


def get_sample_persons(count: int = 10) -> dict[str, Any]:
    """Generate multiple sample Person responses."""
    return {
        "documents": [
            {
                "id": f"110048{i:02d}",
                "nachname": f"Person{i}",
                "vorname": "Test",
                "fraktion": "SPD" if i % 2 == 0 else "CDU/CSU",
                "wahlperioden": [20],
            }
            for i in range(1, count + 1)
        ],
        "numFound": count,
        "cursor": None,
    }
