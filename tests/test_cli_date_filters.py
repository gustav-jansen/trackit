"""Tests for CLI date filter helper."""

from datetime import date

import click
import pytest

from trackit.cli.date_filters import resolve_cli_date_range
from trackit.utils.date_parser import get_date_range, parse_date


def _ctx() -> click.Context:
    return click.Context(click.Command("test"))


def test_resolve_cli_date_range_rejects_multiple_periods(capsys):
    period_flags = {"this-month": True, "last-month": True}

    with pytest.raises(click.exceptions.Exit) as excinfo:
        resolve_cli_date_range(
            _ctx(),
            start_date=None,
            end_date=None,
            period_flags=period_flags,
        )

    assert excinfo.value.exit_code == 1
    err = capsys.readouterr().err
    assert "Only one period option" in err


def test_resolve_cli_date_range_rejects_period_with_start_end(capsys):
    period_flags = {"this-month": True}

    with pytest.raises(click.exceptions.Exit) as excinfo:
        resolve_cli_date_range(
            _ctx(),
            start_date="2024-01-01",
            end_date=None,
            period_flags=period_flags,
        )

    assert excinfo.value.exit_code == 1
    err = capsys.readouterr().err
    assert "cannot be combined" in err


def test_resolve_cli_date_range_returns_period_range():
    period_flags = {"this-month": True}

    expected_start, expected_end = get_date_range("this-month")
    start, end = resolve_cli_date_range(
        _ctx(),
        start_date=None,
        end_date=None,
        period_flags=period_flags,
    )

    assert start == expected_start
    assert end == expected_end


def test_resolve_cli_date_range_parses_explicit_dates():
    period_flags = {}

    start, end = resolve_cli_date_range(
        _ctx(),
        start_date="2024-01-02",
        end_date="2024-01-05",
        period_flags=period_flags,
    )

    assert start == parse_date("2024-01-02")
    assert end == parse_date("2024-01-05")


def test_resolve_cli_date_range_applies_default_range():
    period_flags = {}
    default_range = (date(2020, 1, 1), date(2020, 1, 31))

    start, end = resolve_cli_date_range(
        _ctx(),
        start_date=None,
        end_date=None,
        period_flags=period_flags,
        default_range=default_range,
    )

    assert (start, end) == default_range


def test_resolve_cli_date_range_no_default_range():
    period_flags = {}

    start, end = resolve_cli_date_range(
        _ctx(),
        start_date=None,
        end_date=None,
        period_flags=period_flags,
        default_range=None,
    )

    assert start is None
    assert end is None


def test_resolve_cli_date_range_invalid_start_date(capsys):
    period_flags = {}

    with pytest.raises(click.exceptions.Exit) as excinfo:
        resolve_cli_date_range(
            _ctx(),
            start_date="not-a-date",
            end_date=None,
            period_flags=period_flags,
        )

    assert excinfo.value.exit_code == 1
    err = capsys.readouterr().err
    assert "Invalid start date" in err
