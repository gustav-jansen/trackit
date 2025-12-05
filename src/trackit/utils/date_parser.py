"""Date parsing utilities."""

from datetime import date
from dateutil import parser as date_parser


def parse_date(date_str: str) -> date:
    """Parse a date string into a date object.

    Args:
        date_str: Date string in various formats

    Returns:
        Date object

    Raises:
        ValueError: If date string cannot be parsed
    """
    try:
        dt = date_parser.parse(date_str)
        return dt.date()
    except (ValueError, TypeError) as e:
        raise ValueError(f"Could not parse date '{date_str}': {e}")

