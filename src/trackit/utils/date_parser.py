"""Date parsing utilities."""

from datetime import date, datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


def parse_date(date_str: str) -> date:
    """Parse a date string into a date object.

    Supports various formats including relative dates:
    - Absolute dates: "2024-01-15", "January 15, 2024", etc.
    - Relative dates: "today", "yesterday", "last month", "this year", etc.

    Args:
        date_str: Date string in various formats

    Returns:
        Date object

    Raises:
        ValueError: If date string cannot be parsed
    """
    date_str = date_str.strip().lower()
    today = date.today()
    
    # Handle relative dates
    relative_dates = {
        "today": today,
        "yesterday": today - timedelta(days=1),
        "tomorrow": today + timedelta(days=1),
    }
    
    if date_str in relative_dates:
        return relative_dates[date_str]
    
    # Handle "last/this/next" + time period
    if date_str.startswith("last "):
        period = date_str[5:]
        if period == "month":
            return (today - relativedelta(months=1)).replace(day=1)
        elif period == "year":
            return today.replace(month=1, day=1) - relativedelta(years=1)
        elif period == "week":
            # Return Monday of last week (for consistency with "this week" and "next week")
            days_since_monday = today.weekday()
            return today - timedelta(days=days_since_monday + 7)
        elif period in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            # Last Monday, etc.
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            target_day = days.index(period)
            days_ago = (today.weekday() - target_day) % 7
            if days_ago == 0:
                days_ago = 7
            return today - timedelta(days=days_ago)
    
    elif date_str.startswith("this "):
        period = date_str[5:]
        if period == "month":
            return today.replace(day=1)
        elif period == "year":
            return today.replace(month=1, day=1)
        elif period == "week":
            return today - timedelta(days=today.weekday())
    
    elif date_str.startswith("next "):
        period = date_str[5:]
        if period == "month":
            return (today + relativedelta(months=1)).replace(day=1)
        elif period == "year":
            return (today.replace(month=1, day=1) + relativedelta(years=1))
        elif period == "week":
            return today + timedelta(days=(7 - today.weekday()))
    
    # Try parsing as absolute date
    try:
        dt = date_parser.parse(date_str)
        return dt.date()
    except (ValueError, TypeError) as e:
        raise ValueError(f"Could not parse date '{date_str}': {e}")
