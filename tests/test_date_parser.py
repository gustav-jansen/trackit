"""Tests for date parser with relative dates."""

import pytest
from datetime import date, timedelta
from trackit.utils.date_parser import parse_date


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

