"""Tests for date parser with relative dates."""

import pytest
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from trackit.utils.date_parser import parse_date, get_date_range


def test_parse_absolute_date():
    """Test parsing absolute dates."""
    result = parse_date("2024-01-15")
    assert result == date(2024, 1, 15)


def test_parse_today():
    """Test parsing 'today'."""
    result = parse_date("today")
    assert result == date.today()


def test_parse_yesterday():
    """Test parsing 'yesterday'."""
    result = parse_date("yesterday")
    assert result == date.today() - timedelta(days=1)


def test_parse_tomorrow():
    """Test parsing 'tomorrow'."""
    result = parse_date("tomorrow")
    assert result == date.today() + timedelta(days=1)


def test_parse_last_month():
    """Test parsing 'last month'."""
    result = parse_date("last month")
    # Should be first day of last month
    today = date.today()
    if today.month == 1:
        expected = date(today.year - 1, 12, 1)
    else:
        expected = date(today.year, today.month - 1, 1)
    assert result == expected


def test_parse_last_week():
    """Test parsing 'last week'."""
    result = parse_date("last week")
    # Should be Monday of last week (for consistency with "this week" and "next week")
    today = date.today()
    days_since_monday = today.weekday()
    expected = today - timedelta(days=days_since_monday + 7)
    assert result == expected
    # Verify it's a Monday (weekday 0)
    assert result.weekday() == 0


def test_parse_this_month():
    """Test parsing 'this month'."""
    result = parse_date("this month")
    today = date.today()
    assert result == date(today.year, today.month, 1)


def test_parse_this_year():
    """Test parsing 'this year'."""
    result = parse_date("this year")
    today = date.today()
    assert result == date(today.year, 1, 1)


def test_parse_last_year():
    """Test parsing 'last year'."""
    result = parse_date("last year")
    today = date.today()
    assert result == date(today.year - 1, 1, 1)


def test_parse_invalid_relative():
    """Test parsing invalid relative date."""
    with pytest.raises(ValueError):
        parse_date("last invalid")


def test_parse_standard_formats():
    """Test parsing various standard date formats."""
    # These should all work via dateutil parser
    assert parse_date("January 15, 2024") == date(2024, 1, 15)
    assert parse_date("15/01/2024") == date(2024, 1, 15)


def test_get_date_range_this_month():
    """Test get_date_range for this-month."""
    today = date.today()
    start, end = get_date_range("this-month")
    assert start == date(today.year, today.month, 1)
    assert end == today


def test_get_date_range_this_year():
    """Test get_date_range for this-year."""
    today = date.today()
    start, end = get_date_range("this-year")
    assert start == date(today.year, 1, 1)
    assert end == today


def test_get_date_range_this_week():
    """Test get_date_range for this-week."""
    today = date.today()
    start, end = get_date_range("this-week")
    expected_start = today - timedelta(days=today.weekday())
    assert start == expected_start
    assert start.weekday() == 0  # Should be Monday
    assert end == today


def test_get_date_range_last_month():
    """Test get_date_range for last-month."""
    today = date.today()
    start, end = get_date_range("last-month")
    # First day of last month
    expected_start = (today - relativedelta(months=1)).replace(day=1)
    # Last day of last month (day before first day of current month)
    expected_end = today.replace(day=1) - timedelta(days=1)
    assert start == expected_start
    assert end == expected_end
    # Verify end is the last day of last month
    assert end.month == expected_start.month
    assert end.year == expected_start.year


def test_get_date_range_last_year():
    """Test get_date_range for last-year."""
    today = date.today()
    start, end = get_date_range("last-year")
    # January 1 of last year
    expected_start = today.replace(month=1, day=1) - relativedelta(years=1)
    # December 31 of last year
    expected_end = today.replace(month=1, day=1) - timedelta(days=1)
    assert start == expected_start
    assert end == expected_end
    assert start.month == 1
    assert start.day == 1
    assert end.month == 12
    assert end.day == 31
    assert start.year == end.year == today.year - 1


def test_get_date_range_last_week():
    """Test get_date_range for last-week."""
    today = date.today()
    start, end = get_date_range("last-week")
    # Monday of last week
    days_since_monday = today.weekday()
    expected_start = today - timedelta(days=days_since_monday + 7)
    # Sunday of last week (Monday + 6 days)
    expected_end = expected_start + timedelta(days=6)
    assert start == expected_start
    assert end == expected_end
    assert start.weekday() == 0  # Monday
    assert end.weekday() == 6  # Sunday
    assert (end - start).days == 6


def test_get_date_range_invalid_period():
    """Test get_date_range with invalid period."""
    with pytest.raises(ValueError, match="Unknown period"):
        get_date_range("invalid-period")


def test_get_date_range_edge_case_month_boundary():
    """Test get_date_range handles month boundaries correctly."""
    # Test on first day of month
    # This is a bit tricky to test without mocking, but we can verify the logic
    today = date.today()
    start, end = get_date_range("this-month")
    # If today is the first day of the month, start and end should be the same
    if today.day == 1:
        assert start == end == today

    # Test last-month when current month is January
    if today.month == 1:
        start, end = get_date_range("last-month")
        assert start.month == 12
        assert start.year == today.year - 1
        assert end.month == 12
        assert end.year == today.year - 1


def test_get_date_range_edge_case_year_boundary():
    """Test get_date_range handles year boundaries correctly."""
    today = date.today()
    # Test last-year
    start, end = get_date_range("last-year")
    assert start.year == today.year - 1
    assert end.year == today.year - 1
    assert start == date(today.year - 1, 1, 1)
    assert end == date(today.year - 1, 12, 31)

