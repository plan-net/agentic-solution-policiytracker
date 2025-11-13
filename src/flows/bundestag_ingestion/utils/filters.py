"""
Filter builder for Bundestag DIP API queries.

Constructs and validates filter parameters for API requests.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class FilterBuilder:
    """
    Builder class for constructing Bundestag API filter parameters.

    Provides methods for building valid filter dictionaries with proper
    parameter names and validation. Supports common filters like date ranges,
    legislative periods, and subject areas.

    Example:
        >>> builder = FilterBuilder()
        >>> filters = builder.build_filters(
        ...     wahlperiode="20",
        ...     datum_von="2024-01-01",
        ...     datum_bis="2024-12-31",
        ...     limit=100
        ... )
    """

    # Valid filter parameter names for the API
    VALID_FILTER_PARAMS = {
        "wahlperiode",       # Legislative period (e.g., "20")
        "datum",             # Specific date
        "datum_von",         # Date from (start of range)
        "datum_bis",         # Date to (end of range)
        "sachgebiet",        # Subject area
        "drucksachetyp",     # Document type
        "dokumentart",       # Document category
        "aktivitaetsart",    # Activity type
        "vorgangstyp",       # Process type
        "institution",       # Institution
    }

    # API-specific parameter names
    API_PARAM_MAPPING = {
        "wahlperiode": "f.wahlperiode",
        "datum": "f.datum",
        "datum_von": "f.datum.start",
        "datum_bis": "f.datum.end",
        "sachgebiet": "f.sachgebiet",
        "drucksachetyp": "f.drucksachetyp",
        "dokumentart": "f.dokumentart",
        "aktivitaetsart": "f.aktivitaetsart",
        "vorgangstyp": "f.vorgangstyp",
        "institution": "f.institution",
    }

    def __init__(self):
        """Initialize the filter builder."""
        logger.debug("Initialized FilterBuilder")

    def build_filters(
        self,
        wahlperiode: Optional[str] = None,
        datum_von: Optional[str] = None,
        datum_bis: Optional[str] = None,
        sachgebiet: Optional[str] = None,
        format: str = "json",
        limit: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build filter parameters for API requests.

        Args:
            wahlperiode: Legislative period (e.g., "20" for 20th period)
            datum_von: Start date in ISO 8601 format (YYYY-MM-DD)
            datum_bis: End date in ISO 8601 format (YYYY-MM-DD)
            sachgebiet: Subject area code or name
            format: Response format (default: "json")
            limit: Maximum number of results (API parameter: "num")
            **kwargs: Additional filter parameters

        Returns:
            Dictionary of validated filter parameters

        Raises:
            ValueError: If date formats are invalid or date range is invalid
        """
        filters = {}

        # Add format parameter
        filters["format"] = format

        # Add limit if specified
        if limit is not None:
            if limit <= 0:
                raise ValueError("Limit must be a positive integer")
            filters["num"] = limit

        # Add wahlperiode if specified
        if wahlperiode:
            filters[self.API_PARAM_MAPPING["wahlperiode"]] = wahlperiode
            logger.debug("Added wahlperiode filter", wahlperiode=wahlperiode)

        # Add date filters with validation
        if datum_von:
            self._validate_date_format(datum_von, "datum_von")
            filters[self.API_PARAM_MAPPING["datum_von"]] = datum_von
            logger.debug("Added datum_von filter", datum_von=datum_von)

        if datum_bis:
            self._validate_date_format(datum_bis, "datum_bis")
            filters[self.API_PARAM_MAPPING["datum_bis"]] = datum_bis
            logger.debug("Added datum_bis filter", datum_bis=datum_bis)

        # Validate date range if both dates provided
        if datum_von and datum_bis:
            self._validate_date_range(datum_von, datum_bis)

        # Add sachgebiet if specified
        if sachgebiet:
            filters[self.API_PARAM_MAPPING["sachgebiet"]] = sachgebiet
            logger.debug("Added sachgebiet filter", sachgebiet=sachgebiet)

        # Add any additional filter parameters
        for key, value in kwargs.items():
            if key in self.VALID_FILTER_PARAMS:
                api_param = self.API_PARAM_MAPPING.get(key, f"f.{key}")
                filters[api_param] = value
                logger.debug("Added custom filter", param=key, value=value)
            else:
                logger.warning(
                    "Unknown filter parameter ignored",
                    param=key,
                    value=value
                )

        logger.info(
            "Built filter parameters",
            filter_count=len(filters),
            has_date_range=bool(datum_von and datum_bis)
        )

        return filters

    def _validate_date_format(self, date_str: str, param_name: str):
        """
        Validate that date string is in ISO 8601 format.

        Args:
            date_str: Date string to validate
            param_name: Parameter name for error messages

        Raises:
            ValueError: If date format is invalid
        """
        try:
            # Try parsing as ISO 8601 date
            datetime.fromisoformat(date_str)
        except ValueError as e:
            raise ValueError(
                f"Invalid date format for {param_name}: {date_str}. "
                f"Expected ISO 8601 format (YYYY-MM-DD). Error: {str(e)}"
            )

    def _validate_date_range(self, start_date: str, end_date: str):
        """
        Validate that date range is valid (start before end).

        Args:
            start_date: Start date in ISO 8601 format
            end_date: End date in ISO 8601 format

        Raises:
            ValueError: If date range is invalid
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        if start > end:
            raise ValueError(
                f"Invalid date range: start_date ({start_date}) is after end_date ({end_date})"
            )

        logger.debug(
            "Validated date range",
            start_date=start_date,
            end_date=end_date,
            days=(end - start).days
        )

    def build_wahlperiode_filter(self, period: int) -> Dict[str, Any]:
        """
        Build filter for a specific legislative period.

        Args:
            period: Legislative period number (e.g., 20)

        Returns:
            Filter dictionary for the specified period
        """
        return self.build_filters(wahlperiode=str(period))

    def build_date_range_filter(
        self,
        start_date: str,
        end_date: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Build filter for a date range.

        Args:
            start_date: Start date in ISO 8601 format
            end_date: End date in ISO 8601 format
            format: Response format (default: "json")

        Returns:
            Filter dictionary for the date range
        """
        return self.build_filters(
            datum_von=start_date,
            datum_bis=end_date,
            format=format
        )

    def build_current_period_filter(
        self,
        days_back: int = 30,
        format: str = "json"
    ) -> Dict[str, Any]:
        """
        Build filter for recent documents (last N days).

        Args:
            days_back: Number of days to look back from today
            format: Response format (default: "json")

        Returns:
            Filter dictionary for recent documents
        """
        from datetime import timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        return self.build_filters(
            datum_von=start_date.strftime("%Y-%m-%d"),
            datum_bis=end_date.strftime("%Y-%m-%d"),
            format=format
        )

    def build_sachgebiet_filter(
        self,
        sachgebiet: str,
        wahlperiode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build filter for a specific subject area.

        Args:
            sachgebiet: Subject area code or name
            wahlperiode: Optional legislative period to filter by

        Returns:
            Filter dictionary for the subject area
        """
        return self.build_filters(
            sachgebiet=sachgebiet,
            wahlperiode=wahlperiode
        )

    def combine_filters(self, *filter_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine multiple filter dictionaries.

        Later dictionaries override earlier ones for conflicting keys.

        Args:
            *filter_dicts: Variable number of filter dictionaries to combine

        Returns:
            Combined filter dictionary
        """
        combined = {}

        for filter_dict in filter_dicts:
            combined.update(filter_dict)

        logger.debug(
            "Combined filters",
            input_count=len(filter_dicts),
            output_param_count=len(combined)
        )

        return combined

    @staticmethod
    def get_available_filters() -> List[str]:
        """
        Get list of available filter parameter names.

        Returns:
            List of valid filter parameter names
        """
        return sorted(FilterBuilder.VALID_FILTER_PARAMS)
