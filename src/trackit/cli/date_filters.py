"""CLI helpers for date range resolution."""

from datetime import date

import click

from trackit.utils.date_parser import get_date_range, parse_date


def resolve_cli_date_range(
    ctx,
    *,
    start_date: str | None,
    end_date: str | None,
    period_flags: dict[str, bool],
    default_range: tuple[date, date] | None = None,
) -> tuple[date | None, date | None]:
    """Resolve CLI date range from period flags or explicit dates."""
    period_count = sum(1 for is_set in period_flags.values() if is_set)

    if period_count > 1:
        click.echo(
            "Error: Only one period option (--this-month, --this-year, --this-week, --last-month, --last-year, --last-week) can be specified at a time.",
            err=True,
        )
        ctx.exit(1)

    if period_count > 0 and (start_date or end_date):
        click.echo(
            "Error: Period options (--this-month, --this-year, etc.) cannot be combined with --start-date or --end-date.",
            err=True,
        )
        ctx.exit(1)

    start = None
    end = None

    if period_count == 1:
        for period, is_set in period_flags.items():
            if is_set:
                start, end = get_date_range(period)
                break
    else:
        if start_date:
            try:
                start = parse_date(start_date)
            except ValueError as e:
                click.echo(f"Error: Invalid start date: {e}", err=True)
                ctx.exit(1)

        if end_date:
            try:
                end = parse_date(end_date)
            except ValueError as e:
                click.echo(f"Error: Invalid end date: {e}", err=True)
                ctx.exit(1)

        if start is None and end is None and default_range is not None:
            start, end = default_range

    return start, end
