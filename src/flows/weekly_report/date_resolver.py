"""
Date Resolution for Weekly Report.

Parses user input (calendar week or Monday date) and resolves to a date range.
Supports formats:
- KW48 or KW48/2025 (German calendar week notation)
- 2025-11-25 (ISO date format)
- 25.11.2025 (German date format)
"""

import re
from datetime import datetime, timedelta
from typing import Optional

import structlog

logger = structlog.get_logger()


class DateResolutionError(Exception):
    """Raised when date input cannot be resolved."""

    pass


class DateResolver:
    """Resolves user input to a week date range."""

    # Patterns for different input formats
    PATTERNS = {
        # KW48 or KW48/2025 or KW48/25
        "kw_format": re.compile(
            r"^KW\s*(\d{1,2})(?:/(\d{2,4}))?$", re.IGNORECASE
        ),
        # ISO date: 2025-11-25
        "iso_date": re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"),
        # German date: 25.11.2025
        "german_date": re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$"),
        # Week number only: 48
        "week_number": re.compile(r"^(\d{1,2})$"),
    }

    def __init__(self, default_year: Optional[int] = None):
        """
        Initialize the date resolver.

        Args:
            default_year: Year to use when not specified (defaults to current year)
        """
        self.default_year = default_year or datetime.now().year

    def resolve(self, user_input: str) -> dict:
        """
        Resolve user input to a week date range.

        Args:
            user_input: Calendar week (KW48) or date (2025-11-25)

        Returns:
            Dictionary with week_start, week_end, week_number, year, week_label

        Raises:
            DateResolutionError: If input cannot be parsed
        """
        if not user_input:
            # Default to previous week if no input
            return self._get_previous_week()

        user_input = user_input.strip()

        # Try each pattern
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.match(user_input)
            if match:
                try:
                    if pattern_name == "kw_format":
                        return self._resolve_kw_format(match)
                    elif pattern_name == "iso_date":
                        return self._resolve_iso_date(match)
                    elif pattern_name == "german_date":
                        return self._resolve_german_date(match)
                    elif pattern_name == "week_number":
                        return self._resolve_week_number(match)
                except Exception as e:
                    logger.warning(
                        f"Pattern {pattern_name} matched but resolution failed",
                        error=str(e),
                    )
                    continue

        raise DateResolutionError(
            f"Cannot parse date input: '{user_input}'. "
            "Expected formats: KW48, KW48/2025, 2025-11-25, or 25.11.2025"
        )

    def _resolve_kw_format(self, match: re.Match) -> dict:
        """Resolve KW format (e.g., KW48 or KW48/2025)."""
        week_number = int(match.group(1))
        year_str = match.group(2)

        if year_str:
            year = int(year_str)
            if year < 100:  # Handle 2-digit year
                year = 2000 + year
        else:
            year = self.default_year

        return self._week_to_dates(week_number, year)

    def _resolve_iso_date(self, match: re.Match) -> dict:
        """Resolve ISO date format (YYYY-MM-DD)."""
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        date = datetime(year, month, day)
        return self._date_to_week(date)

    def _resolve_german_date(self, match: re.Match) -> dict:
        """Resolve German date format (DD.MM.YYYY)."""
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        date = datetime(year, month, day)
        return self._date_to_week(date)

    def _resolve_week_number(self, match: re.Match) -> dict:
        """Resolve plain week number."""
        week_number = int(match.group(1))
        return self._week_to_dates(week_number, self.default_year)

    def _week_to_dates(self, week_number: int, year: int) -> dict:
        """
        Convert ISO week number to date range.

        Uses ISO week date system where:
        - Week 1 is the week containing January 4th
        - Weeks start on Monday
        """
        if not 1 <= week_number <= 53:
            raise DateResolutionError(f"Invalid week number: {week_number} (must be 1-53)")

        # ISO week date: Year-Www-D where D is day of week (1=Monday)
        # January 4th is always in week 1
        jan_4 = datetime(year, 1, 4)

        # Find the Monday of week 1
        week_1_monday = jan_4 - timedelta(days=jan_4.weekday())

        # Calculate the Monday of the target week
        week_start = week_1_monday + timedelta(weeks=week_number - 1)

        # Week ends on Sunday at 23:59:59
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # Verify the year is correct (week 1 might start in previous year)
        actual_year = week_start.isocalendar()[0]
        if actual_year != year:
            logger.warning(
                f"Week {week_number} of {year} actually falls in year {actual_year}"
            )

        return {
            "week_start": week_start,
            "week_end": week_end,
            "week_number": week_number,
            "year": year,
            "week_label": f"KW{week_number}/{year}",
        }

    def _date_to_week(self, date: datetime) -> dict:
        """Convert a date to its containing week range."""
        # Get ISO week info
        iso_year, iso_week, iso_day = date.isocalendar()

        # Find Monday of this week
        days_since_monday = iso_day - 1  # ISO weekday: 1=Monday
        week_start = date - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Week ends on Sunday
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return {
            "week_start": week_start,
            "week_end": week_end,
            "week_number": iso_week,
            "year": iso_year,
            "week_label": f"KW{iso_week}/{iso_year}",
        }

    def _get_previous_week(self) -> dict:
        """Get the previous week (last Monday to Sunday)."""
        today = datetime.now()
        # Find last Monday
        days_since_monday = today.weekday()
        this_monday = today - timedelta(days=days_since_monday)
        last_monday = this_monday - timedelta(weeks=1)
        last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)

        return self._date_to_week(last_monday)

    def format_date_range(self, result: dict) -> str:
        """Format the date range for display."""
        week_start = result["week_start"]
        week_end = result["week_end"]

        return (
            f"{result['week_label']} "
            f"({week_start.strftime('%d %B')} - {week_end.strftime('%d %B %Y')})"
        )


def resolve_week_input(user_input: str) -> dict:
    """
    Convenience function to resolve week input.

    Args:
        user_input: Calendar week (KW48) or date string

    Returns:
        Dictionary with week_start, week_end, week_number, year, week_label
    """
    resolver = DateResolver()
    return resolver.resolve(user_input)
