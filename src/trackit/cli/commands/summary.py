"""Summary commands."""

import click
from trackit.cli.date_filters import resolve_cli_date_range
from trackit.domain.summary import SummaryService
from trackit.domain.entities import SummaryGroupBy
from trackit.utils.date_parser import get_last_six_months_range


def _display_columnar_summary_standard(
    sections,
    period_keys,
    period_overall_totals,
):
    """Display columnar summary for standard view.

    Args:
        sections: Ordered SummarySection list
        period_keys: Sorted list of period keys (e.g., ["2024-01", "2024-02"])
        period_overall_totals: Dict mapping period key to total
    """
    # Column widths
    CATEGORY_WIDTH = 50
    PERIOD_COLUMN_WIDTH = 14  # Enough for single digit millions: -$9,999,999.99

    # Build header
    header = f"{'Category':<{CATEGORY_WIDTH}}"
    for period_key in period_keys:
        header += f"   {period_key:>{PERIOD_COLUMN_WIDTH}}"
    click.echo(header)

    # Separator line
    separator = "-" * CATEGORY_WIDTH
    for _ in period_keys:
        separator += "-" * (PERIOD_COLUMN_WIDTH + 3)
    click.echo(separator)

    for section in sections:
        click.echo(section.name)
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        for row in section.rows:
            category_name = row.category_name or "Uncategorized"
            row_display = f"    {category_name:<{CATEGORY_WIDTH - 4}}"
            for period_key in period_keys:
                total = row.period_totals.get(period_key, 0.0)
                if total == 0:
                    row_display += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
                else:
                    row_display += f"   ${total:>13,.2f}"
            click.echo(row_display)

        click.echo(separator)
        subtotal_row = f"{section.name} Subtotal".ljust(CATEGORY_WIDTH)
        for period_key in period_keys:
            subtotal = section.period_subtotals.get(period_key, 0.0)
            if subtotal == 0:
                subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                subtotal_row += f"   ${subtotal:>13,.2f}"
        click.echo(subtotal_row)
        click.echo(
            "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        if section.name in ("Income", "Transfer"):
            click.echo()

    # Overall total
    total_row = f"{'TOTAL':<{CATEGORY_WIDTH}}"
    for i, period_key in enumerate(period_keys):
        total = period_overall_totals.get(period_key, 0.0)
        if total == 0:
            total_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
        else:
            total_row += f"   ${total:>13,.2f}"
    click.echo(total_row)


def _display_columnar_summary_expanded(
    sections,
    period_keys,
    period_overall_totals,
):
    """Display columnar summary for expanded view.

    Args:
        sections: Ordered SummarySection list
        period_keys: Sorted list of period keys
        period_overall_totals: Dict mapping period key to total
    """
    # Column widths
    CATEGORY_WIDTH = 50
    PERIOD_COLUMN_WIDTH = 14  # Enough for single digit millions: -$9,999,999.99
    INDENT_SIZE = 4

    # Build header
    header = f"{'Category':<{CATEGORY_WIDTH}}"
    for period_key in period_keys:
        header += f"   {period_key:>{PERIOD_COLUMN_WIDTH}}"
    click.echo(header)

    # Separator line
    separator = "-" * CATEGORY_WIDTH
    for _ in period_keys:
        separator += "-" * (PERIOD_COLUMN_WIDTH + 3)
    click.echo(separator)

    for section in sections:
        click.echo(section.name)
        click.echo(
            "*" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        _display_columnar_summary_rows(
            section.rows,
            period_keys,
            indent=1,
        )
        click.echo(separator)
        subtotal_row = f"{section.name} Subtotal".ljust(CATEGORY_WIDTH)
        for period_key in period_keys:
            subtotal = section.period_subtotals.get(period_key, 0.0)
            if subtotal == 0:
                subtotal_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                subtotal_row += f"   ${subtotal:>13,.2f}"
        click.echo(subtotal_row)
        click.echo(
            "=" * (CATEGORY_WIDTH + len(period_keys) * (PERIOD_COLUMN_WIDTH + 3))
        )
        if section.name in ("Income", "Transfer"):
            click.echo()

    # Overall total
    total_row = f"{'TOTAL':<{CATEGORY_WIDTH}}"
    for i, period_key in enumerate(period_keys):
        total = period_overall_totals.get(period_key, 0.0)
        if total == 0:
            total_row += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
        else:
            total_row += f"   ${total:>13,.2f}"
    click.echo(total_row)


def _display_columnar_summary_rows(
    rows,
    period_keys,
    indent=0,
):
    """Recursively display summary rows in columnar format."""
    PERIOD_COLUMN_WIDTH = 14  # Enough for single digit millions: -$9,999,999.99
    CATEGORY_WIDTH = 50
    INDENT_SIZE = 4
    for row in rows:
        indent_str = " " * (INDENT_SIZE * indent)
        category_width = CATEGORY_WIDTH - (INDENT_SIZE * indent)
        display = f"{indent_str}{row.category_name:<{category_width}}"
        for period_key in period_keys:
            total = row.period_totals.get(period_key, 0.0)
            if total == 0:
                display += f"   {'-':>{PERIOD_COLUMN_WIDTH}}"
            else:
                display += f"   ${total:>13,.2f}"
        click.echo(display)

        if row.children:
            _display_columnar_summary_rows(
                row.children,
                period_keys,
                indent + 1,
            )


def _display_expanded_summary(
    rows,
    indent=0,
    is_first=True,
):
    """Recursively display category tree with totals, sorted by value (highest first)."""
    INDENT_SIZE = 4
    for i, row in enumerate(rows):
        if row.total == 0:
            continue

        if indent == 0 and not (is_first and i == 0):
            click.echo()

        indent_str = " " * (INDENT_SIZE * indent)
        total_str = f"${row.total:,.2f}"
        category_width = 50 - (INDENT_SIZE * indent)
        amount_width = 20 + (INDENT_SIZE * indent)
        click.echo(
            f"{indent_str}{row.category_name:<{category_width}} {total_str:>{amount_width}}"
        )

        if row.children:
            _display_expanded_summary(
                row.children,
                indent + 1,
                is_first=False,
            )


@click.command("summary")
@click.option(
    "--start-date",
    help="Start date (YYYY-MM-DD or relative like 'last month', 'this year')",
)
@click.option(
    "--end-date", help="End date (YYYY-MM-DD or relative like 'today', 'this month')"
)
@click.option("--this-month", is_flag=True, help="Filter to current month")
@click.option("--this-year", is_flag=True, help="Filter to current year")
@click.option("--this-week", is_flag=True, help="Filter to current week")
@click.option("--last-month", is_flag=True, help="Filter to previous month")
@click.option("--last-year", is_flag=True, help="Filter to previous year")
@click.option("--last-week", is_flag=True, help="Filter to previous week")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.option(
    "--include-transfers",
    is_flag=True,
    help="Include transactions with Transfer category",
)
@click.option(
    "--expand", is_flag=True, help="Expand entire category tree with subtotals"
)
@click.option(
    "--group-by-month", is_flag=True, help="Group summary by month in columnar format"
)
@click.option(
    "--group-by-year", is_flag=True, help="Group summary by year in columnar format"
)
@click.pass_context
def summary(
    ctx,
    start_date: str,
    end_date: str,
    this_month: bool,
    this_year: bool,
    this_week: bool,
    last_month: bool,
    last_year: bool,
    last_week: bool,
    category: str,
    include_transfers: bool,
    expand: bool,
    group_by_month: bool,
    group_by_year: bool,
):
    """Show category summary."""
    db = ctx.obj["db"]
    summary_service = SummaryService(db)

    # Validate grouping options
    if group_by_month and group_by_year:
        click.echo(
            "Error: --group-by-month and --group-by-year cannot be specified at the same time.",
            err=True,
        )
        ctx.exit(1)

    # Set default grouping to month if no grouping option specified
    if not group_by_month and not group_by_year:
        group_by_month = True

    period_flags = {
        "this-month": this_month,
        "this-year": this_year,
        "this-week": this_week,
        "last-month": last_month,
        "last-year": last_year,
        "last-week": last_week,
    }
    start, end = resolve_cli_date_range(
        ctx,
        start_date=start_date,
        end_date=end_date,
        period_flags=period_flags,
        default_range=get_last_six_months_range(),
    )

    group_by = (
        SummaryGroupBy.CATEGORY_YEAR if group_by_year else SummaryGroupBy.CATEGORY_MONTH
    )
    report = summary_service.build_summary_report(
        start_date=start,
        end_date=end,
        category_path=category,
        include_transfers=include_transfers,
        group_by=group_by,
    )

    if not report.transactions:
        click.echo("No transactions found.")
        return

    # Check if grouping is enabled
    if group_by_month or group_by_year:
        # Group transactions by period
        period_transactions_map = report.period_transactions_map

        # Get sorted list of period keys (chronologically ascending)
        period_keys = list(report.period_keys)

        if not period_keys:
            click.echo("No transactions found.")
            return

        if expand:
            # Expanded columnar view
            click.echo("\nCategory Summary (Expanded):")
            _display_columnar_summary_expanded(
                report.period_expanded_sections,
                period_keys,
                report.period_overall_totals,
            )
        else:
            # Standard columnar view
            click.echo("\nCategory Summary:")
            _display_columnar_summary_standard(
                report.period_sections,
                period_keys,
                report.period_overall_totals,
            )
        return

    # Calculate overall total from all filtered transactions
    overall_total = report.overall_total

    if expand:
        # Expanded view: show full category tree
        click.echo("\nCategory Summary (Expanded):")
        click.echo("-" * 80)
        click.echo(f"{'Category':<50} {'Total':>20}")
        click.echo("-" * 80)
        for section in report.expanded_sections:
            click.echo(section.name)
            click.echo("*" * 80)
            _display_expanded_summary(
                section.rows,
                indent=1,
                is_first=True,
            )
            click.echo("-" * 80)
            subtotal_str = f"${section.subtotal:,.2f}"
            click.echo(f"{section.name} Subtotal".ljust(50) + f" {subtotal_str:>20}")
            click.echo("=" * 80)
            if section.name in ("Income", "Transfer"):
                click.echo()
    else:
        # Standard view: show top-level categories (or subcategories if category filter is specified)
        # Display summary
        click.echo("\nCategory Summary:")
        click.echo("-" * 80)
        click.echo(f"{'Category':<50} {'Total':>20}")
        click.echo("-" * 80)
        has_expense_section = False
        for section in report.sections:
            click.echo(section.name)
            click.echo("*" * 80)
            for row in section.rows:
                total_str = f"${row.total:,.2f}"
                click.echo(f"    {row.category_name:<46} {total_str:>20}")

            click.echo("-" * 80)
            subtotal_str = f"${section.subtotal:,.2f}"
            click.echo(f"{section.name} Subtotal".ljust(50) + f" {subtotal_str:>20}")
            click.echo("=" * 80)
            if section.name in ("Income", "Transfer"):
                click.echo()
            if section.name == "Expense":
                has_expense_section = True

        if not has_expense_section:
            click.echo("-" * 80)

    total_str = f"${overall_total:,.2f}" if overall_total != 0 else "-"
    click.echo(f"{'TOTAL':<50} {total_str:>20}")


def register_commands(cli):
    """Register summary command with main CLI."""
    cli.add_command(summary)
