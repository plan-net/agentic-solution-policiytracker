"""
Static reference data for German Bundestag Fraktionen (Parliamentary Groups).

Since the Bundestag API does not provide a dedicated fraktion endpoint,
this module contains complete reference data for all major Fraktionen from 1949 to present.

Data sourced from:
- Bundestag person API data
- https://www.bundestag.de/parlament/fraktionen
- https://kgparl.de/en/research/parliamentary-groups-in-the-german-bundestag/
- Historical parliamentary records
"""

from typing import List, Dict, Any


FRAKTION_REFERENCE_DATA: List[Dict[str, Any]] = [
    # Major continuous parties (1949-present)
    {
        "fraktion_id": "cdu_csu",
        "fraktion_name": "CDU/CSU",
        "full_name": "Christlich Demokratische Union/Christlich-Soziale Union",
        "abbreviation": "CDU/CSU",
        "founding_date": "1949-09-07",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "fraktion",
        "party_family": "conservative",
        "active_wahlperioden": list(range(1, 22)),  # WP 1-21
        "description": "Christian democratic and conservative parliamentary group",
    },
    {
        "fraktion_id": "spd",
        "fraktion_name": "SPD",
        "full_name": "Sozialdemokratische Partei Deutschlands",
        "abbreviation": "SPD",
        "founding_date": "1949-09-07",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "fraktion",
        "party_family": "social_democratic",
        "active_wahlperioden": list(range(1, 22)),  # WP 1-21
        "description": "Social democratic parliamentary group",
    },
    {
        "fraktion_id": "fdp",
        "fraktion_name": "FDP",
        "full_name": "Freie Demokratische Partei",
        "abbreviation": "FDP",
        "founding_date": "1949-09-07",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "fraktion",
        "party_family": "liberal",
        "active_wahlperioden": list(range(1, 22)),  # WP 1-21 (with gaps in 14, 19, 20)
        "description": "Liberal parliamentary group",
    },

    # Green Party (1983-present)
    {
        "fraktion_id": "gruene",
        "fraktion_name": "BÜNDNIS 90/DIE GRÜNEN",
        "full_name": "Bündnis 90/Die Grünen",
        "abbreviation": "GRÜNE",
        "founding_date": "1983-03-29",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "fraktion",
        "party_family": "green",
        "active_wahlperioden": list(range(10, 22)),  # WP 10-21 (with gap in 11)
        "description": "Green and ecological parliamentary group",
    },

    # Left Party Evolution
    {
        "fraktion_id": "pds",
        "fraktion_name": "PDS",
        "full_name": "Partei des Demokratischen Sozialismus",
        "abbreviation": "PDS",
        "founding_date": "1990-12-20",
        "dissolution_date": "2005-10-18",
        "status": "dissolved",
        "fraktion_type": "fraktion",
        "party_family": "left",
        "active_wahlperioden": [12, 13],  # WP 12-13 (as fraktion)
        "description": "Party of Democratic Socialism, successor to SED in East Germany",
    },
    {
        "fraktion_id": "pds_gruppe",
        "fraktion_name": "PDS (Gruppe)",
        "full_name": "PDS Gruppe",
        "abbreviation": "PDS (Gruppe)",
        "founding_date": "1994-11-10",
        "dissolution_date": "2005-10-18",
        "status": "dissolved",
        "fraktion_type": "gruppe",
        "party_family": "left",
        "active_wahlperioden": [14, 15, 16],  # WP 14-16 (as gruppe due to < 5% threshold)
        "description": "PDS parliamentary group (below fraktion threshold)",
    },
    {
        "fraktion_id": "pds_ll_gruppe",
        "fraktion_name": "PDS/LL (Gruppe)",
        "full_name": "PDS/Linke Liste Gruppe",
        "abbreviation": "PDS/LL",
        "founding_date": "1994-11-10",
        "dissolution_date": "1998-10-26",
        "status": "dissolved",
        "fraktion_type": "gruppe",
        "party_family": "left",
        "active_wahlperioden": [13],  # WP 13
        "description": "PDS/Left List parliamentary group",
    },
    {
        "fraktion_id": "die_linke",
        "fraktion_name": "DIE LINKE",
        "full_name": "Die Linke",
        "abbreviation": "DIE LINKE",
        "founding_date": "2005-10-18",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "fraktion",
        "party_family": "left",
        "active_wahlperioden": [17, 18, 19, 20, 21],  # WP 17-21
        "description": "The Left party, successor to PDS",
    },
    {
        "fraktion_id": "die_linke_gruppe",
        "fraktion_name": "Die Linke (Gruppe)",
        "full_name": "Die Linke Gruppe",
        "abbreviation": "Die Linke (Gruppe)",
        "founding_date": "2024-01-01",  # Approximate - after coalition split
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "gruppe",
        "party_family": "left",
        "active_wahlperioden": [20, 21],  # WP 20-21 (fell below threshold)
        "description": "The Left parliamentary group (below fraktion threshold)",
    },

    # Alternative for Germany (2017-present)
    {
        "fraktion_id": "afd",
        "fraktion_name": "AfD",
        "full_name": "Alternative für Deutschland",
        "abbreviation": "AfD",
        "founding_date": "2017-10-24",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "fraktion",
        "party_family": "right_populist",
        "active_wahlperioden": [19, 20, 21],  # WP 19-21
        "description": "Alternative for Germany, right-populist parliamentary group",
    },

    # Historical parties (early Wahlperioden 1-5)
    {
        "fraktion_id": "kpd",
        "fraktion_name": "KPD",
        "full_name": "Kommunistische Partei Deutschlands",
        "abbreviation": "KPD",
        "founding_date": "1949-09-07",
        "dissolution_date": "1953-10-06",
        "status": "dissolved",
        "fraktion_type": "fraktion",
        "party_family": "communist",
        "active_wahlperioden": [1, 2],  # WP 1-2 (banned in 1956)
        "description": "Communist Party of Germany",
    },
    {
        "fraktion_id": "dp",
        "fraktion_name": "DP",
        "full_name": "Deutsche Partei",
        "abbreviation": "DP",
        "founding_date": "1949-09-07",
        "dissolution_date": "1961-10-17",
        "status": "dissolved",
        "fraktion_type": "fraktion",
        "party_family": "conservative",
        "active_wahlperioden": [1, 2, 3],  # WP 1-3
        "description": "German Party, conservative regional party",
    },
    {
        "fraktion_id": "bp",
        "fraktion_name": "BP",
        "full_name": "Bayernpartei",
        "abbreviation": "BP",
        "founding_date": "1949-09-07",
        "dissolution_date": "1953-10-06",
        "status": "dissolved",
        "fraktion_type": "fraktion",
        "party_family": "regional",
        "active_wahlperioden": [1, 2],  # WP 1-2
        "description": "Bavaria Party, Bavarian regionalist party",
    },
    {
        "fraktion_id": "wav",
        "fraktion_name": "WAV",
        "full_name": "Wirtschaftliche Aufbau-Vereinigung",
        "abbreviation": "WAV",
        "founding_date": "1949-09-07",
        "dissolution_date": "1953-10-06",
        "status": "dissolved",
        "fraktion_type": "fraktion",
        "party_family": "economic",
        "active_wahlperioden": [1, 2],  # WP 1-2
        "description": "Economic Reconstruction Union",
    },
    {
        "fraktion_id": "zentrum",
        "fraktion_name": "Zentrum",
        "full_name": "Deutsche Zentrumspartei",
        "abbreviation": "Zentrum",
        "founding_date": "1949-09-07",
        "dissolution_date": "1957-10-15",
        "status": "dissolved",
        "fraktion_type": "fraktion",
        "party_family": "christian_democratic",
        "active_wahlperioden": [1, 2, 3],  # WP 1-3
        "description": "German Centre Party",
    },

    # Special status
    {
        "fraktion_id": "fraktionslos",
        "fraktion_name": "fraktionslos",
        "full_name": "Fraktionslose Abgeordnete",
        "abbreviation": "fraktionslos",
        "founding_date": "1949-09-07",
        "dissolution_date": None,
        "status": "active",
        "fraktion_type": "independent",
        "party_family": "independent",
        "active_wahlperioden": list(range(1, 22)),  # WP 1-21 (always present)
        "description": "Independent members without parliamentary group affiliation",
    },
]
