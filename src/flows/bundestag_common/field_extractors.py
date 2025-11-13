"""
Deterministic field extractors for Bundestag API data.

These functions handle the various data format inconsistencies in the Bundestag DIP API
responses, providing predictable, type-safe extraction of complex nested fields.
"""

import json
from typing import Any, Dict, List, Optional, Union
import structlog

logger = structlog.get_logger()


def extract_fraktion(api_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract current Fraktion (parliamentary group) from API data.

    Handles multiple formats:
    - String: "CDU/CSU"
    - List of strings: ["CDU/CSU"]
    - List of dicts: [{"fraktion": "CDU/CSU", "wahlperiode": [20]}]
    - Dict: {"fraktion": "CDU/CSU"}

    Args:
        api_data: Raw API response data

    Returns:
        Fraktion name or None if not found
    """
    fraktion_data = api_data.get("fraktion")

    if not fraktion_data:
        return None

    # String format - direct return
    if isinstance(fraktion_data, str):
        return fraktion_data

    # List format - get first item
    if isinstance(fraktion_data, list) and fraktion_data:
        first_item = fraktion_data[0]

        # List of dicts
        if isinstance(first_item, dict):
            return first_item.get("fraktion")

        # List of strings
        if isinstance(first_item, str):
            return first_item

    # Dict format
    if isinstance(fraktion_data, dict):
        return fraktion_data.get("fraktion")

    logger.warning("Unable to extract fraktion", fraktion_data_type=type(fraktion_data).__name__)
    return None


def extract_wahlperioden(api_data: Dict[str, Any]) -> List[int]:
    """
    Extract Wahlperiode numbers from API data.

    Handles multiple formats:
    - List of integers: [16, 18, 19, 20, 21]
    - List of dicts: [{"nummer": 20, "von": "..."}]
    - Single integer: 20

    Args:
        api_data: Raw API response data

    Returns:
        List of Wahlperiode numbers (sorted, deduplicated)
    """
    wahlperioden_data = api_data.get("wahlperiode", [])

    if not wahlperioden_data:
        return []

    numbers = []

    # Single integer
    if isinstance(wahlperioden_data, int):
        return [wahlperioden_data]

    # List format
    if isinstance(wahlperioden_data, list):
        for item in wahlperioden_data:
            # Integer in list
            if isinstance(item, int):
                numbers.append(item)
            # Dict with nummer field
            elif isinstance(item, dict) and "nummer" in item:
                nummer = item["nummer"]
                if isinstance(nummer, int):
                    numbers.append(nummer)

    # Remove duplicates and sort
    return sorted(list(set(numbers)))


def extract_committee_memberships(api_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract committee (Ausschuss) memberships from API data.

    Returns JSON string of committee memberships for storage in entity.

    Args:
        api_data: Raw API response data

    Returns:
        JSON string of committee memberships or None
    """
    ausschuesse = api_data.get("ausschuss", [])

    if not ausschuesse or not isinstance(ausschuesse, list):
        return None

    parsed_ausschuesse = []

    for ausschuss in ausschuesse:
        if not isinstance(ausschuss, dict):
            continue

        parsed_ausschuss = {
            "ausschuss": ausschuss.get("ausschuss_name", ausschuss.get("name", "")),
            "rolle": ausschuss.get("rolle", "Mitglied"),
            "von": ausschuss.get("von"),
            "bis": ausschuss.get("bis")
        }

        # Only add if we have at least a name
        if parsed_ausschuss["ausschuss"]:
            parsed_ausschuesse.append(parsed_ausschuss)

    if not parsed_ausschuesse:
        return None

    return json.dumps(parsed_ausschuesse, ensure_ascii=False)


def extract_person_roles(api_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract person_roles information from API data.

    person_roles contains detailed role history with Fraktion and function information.

    Args:
        api_data: Raw API response data

    Returns:
        JSON string of roles or None
    """
    person_roles = api_data.get("person_roles", [])

    if not person_roles or not isinstance(person_roles, list):
        return None

    # person_roles is already well-structured from API
    # Just serialize to JSON
    return json.dumps(person_roles, ensure_ascii=False)


def extract_wahlkreis(api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract Wahlkreis (electoral constituency) information.

    Args:
        api_data: Raw API response data

    Returns:
        Dict with wahlkreis details or None
    """
    wahlkreis_data = api_data.get("wahlkreis")

    if not wahlkreis_data:
        return None

    # Already a dict
    if isinstance(wahlkreis_data, dict):
        return {
            "name": wahlkreis_data.get("name"),
            "nummer": wahlkreis_data.get("nummer"),
            "wahlperiode": wahlkreis_data.get("wahlperiode")
        }

    # String format (just name)
    if isinstance(wahlkreis_data, str):
        return {"name": wahlkreis_data}

    return None


def extract_related_vorgang_ids(api_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract related Vorgang IDs from various entity types.

    Different entities have different field names for Vorgang relationships.

    Args:
        api_data: Raw API response data

    Returns:
        JSON string of Vorgang IDs or None
    """
    # Try different possible field names
    vorgang_ids = []

    # Check vorgangsbezug field
    if "vorgangsbezug" in api_data:
        vorgangsbezug = api_data["vorgangsbezug"]
        if isinstance(vorgangsbezug, list):
            vorgang_ids.extend([v.get("id") for v in vorgangsbezug if isinstance(v, dict) and "id" in v])

    # Check vorgang field directly
    if "vorgang" in api_data:
        vorgang_data = api_data["vorgang"]
        if isinstance(vorgang_data, list):
            vorgang_ids.extend([v.get("id") if isinstance(v, dict) else v for v in vorgang_data])
        elif isinstance(vorgang_data, dict):
            vorgang_ids.append(vorgang_data.get("id"))
        elif isinstance(vorgang_data, (str, int)):
            vorgang_ids.append(str(vorgang_data))

    # Remove None values and deduplicate
    vorgang_ids = list(set([str(vid) for vid in vorgang_ids if vid]))

    if not vorgang_ids:
        return None

    return json.dumps(vorgang_ids, ensure_ascii=False)


def safe_str(value: Any, default: str = "") -> str:
    """
    Safely convert any value to string.

    Args:
        value: Value to convert
        default: Default value if None

    Returns:
        String representation
    """
    if value is None:
        return default
    return str(value)


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert value to integer.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer or default
    """
    if value is None:
        return default

    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_list(value: Any) -> List:
    """
    Safely convert value to list.

    Args:
        value: Value to convert

    Returns:
        List (empty if None or not iterable)
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    # Try to convert to list
    try:
        return list(value)
    except (TypeError, ValueError):
        return [value]


def safe_date(value: Any, default: Optional[str] = None) -> Optional[str]:
    """
    Safely extract and format date string.

    Handles various date formats from Bundestag API:
    - ISO format: "2024-01-15"
    - Datetime strings: "2024-01-15T10:30:00"
    - Timestamp objects

    Args:
        value: Date value to convert
        default: Default value if None or invalid

    Returns:
        ISO format date string (YYYY-MM-DD) or default
    """
    if value is None:
        return default

    # Already a string - try to clean it
    if isinstance(value, str):
        # Remove time component if present
        if 'T' in value:
            value = value.split('T')[0]

        # Basic validation - should be YYYY-MM-DD format
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            return value

        return default

    # Try to convert other types to string
    try:
        date_str = str(value)
        if 'T' in date_str:
            date_str = date_str.split('T')[0]

        # Validate format
        if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
            return date_str
    except (ValueError, TypeError):
        pass

    return default
