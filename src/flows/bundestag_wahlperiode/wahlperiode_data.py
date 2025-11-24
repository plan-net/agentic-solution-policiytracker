"""
Static reference data for German Bundestag Wahlperioden (Electoral Periods).

Since the Bundestag API does not provide a dedicated wahlperiode endpoint,
this module contains complete reference data for all Wahlperioden from 1949 to present.

Data sourced from:
- https://www.bundestag.de/parlament/geschichte/75jahre/wahlperioden
- https://www.bundeswahlleiterin.de/
- Official Bundestag historical records
"""

from typing import Any

WAHLPERIODE_REFERENCE_DATA: list[dict[str, Any]] = [
    # First 10 Wahlperioden (1949-1987)
    {
        "wahlperiode_nummer": 1,
        "election_date": "1949-08-14",
        "start_date": "1949-09-07",
        "end_date": "1953-09-06",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 2,
        "election_date": "1953-09-06",
        "start_date": "1953-10-06",
        "end_date": "1957-10-15",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 3,
        "election_date": "1957-09-15",
        "start_date": "1957-10-15",
        "end_date": "1961-10-17",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 4,
        "election_date": "1961-09-17",
        "start_date": "1961-10-17",
        "end_date": "1965-10-19",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 5,
        "election_date": "1965-09-19",
        "start_date": "1965-10-19",
        "end_date": "1969-10-20",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 6,
        "election_date": "1969-09-28",
        "start_date": "1969-10-20",
        "end_date": "1972-12-13",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 7,
        "election_date": "1972-11-19",
        "start_date": "1972-12-13",
        "end_date": "1976-12-14",
        "is_snap_election": True,  # First snap election
    },
    {
        "wahlperiode_nummer": 8,
        "election_date": "1976-10-03",
        "start_date": "1976-12-14",
        "end_date": "1980-11-04",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 9,
        "election_date": "1980-10-05",
        "start_date": "1980-11-04",
        "end_date": "1983-03-29",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 10,
        "election_date": "1983-03-06",
        "start_date": "1983-03-29",
        "end_date": "1987-02-18",
        "is_snap_election": True,  # Second snap election
    },
    # Wahlperioden 11-21 (1987-2029)
    {
        "wahlperiode_nummer": 11,
        "election_date": "1987-01-25",
        "start_date": "1987-02-18",
        "end_date": "1990-12-20",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 12,
        "election_date": "1990-12-02",
        "start_date": "1990-12-20",
        "end_date": "1994-11-10",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 13,
        "election_date": "1994-10-16",
        "start_date": "1994-11-10",
        "end_date": "1998-10-26",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 14,
        "election_date": "1998-09-27",
        "start_date": "1998-10-26",
        "end_date": "2002-10-17",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 15,
        "election_date": "2002-09-22",
        "start_date": "2002-10-17",
        "end_date": "2005-10-18",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 16,
        "election_date": "2005-09-18",
        "start_date": "2005-10-18",
        "end_date": "2009-10-27",
        "is_snap_election": True,  # Third snap election
    },
    {
        "wahlperiode_nummer": 17,
        "election_date": "2009-09-27",
        "start_date": "2009-10-27",
        "end_date": "2013-10-22",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 18,
        "election_date": "2013-09-22",
        "start_date": "2013-10-22",
        "end_date": "2017-10-24",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 19,
        "election_date": "2017-09-24",
        "start_date": "2017-10-24",
        "end_date": "2021-10-26",
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 20,
        "election_date": "2021-09-26",
        "start_date": "2021-10-26",
        "end_date": "2025-03-25",  # Shortened due to snap election
        "is_snap_election": False,
    },
    {
        "wahlperiode_nummer": 21,
        "election_date": "2025-02-23",
        "start_date": "2025-03-25",
        "end_date": "2029-10-30",  # Projected
        "is_snap_election": True,  # Fourth snap election
    },
]
