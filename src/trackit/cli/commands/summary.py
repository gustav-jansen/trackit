"""Summary commands."""

import click
from trackit.domain.transaction import TransactionService
from trackit.utils.date_parser import parse_date


@click.command("summary")
@click.option("--start-date", help="Start date (YYYY-MM-DD or relative like 'last month', 'this year')")
@click.option("--end-date", help="End date (YYYY-MM-DD or relative like 'today', 'this month')")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.pass_context
def summary(ctx, start_date: str, end_date: str, category: str):
    """Show category summary."""
    db = ctx.obj["db"]
    service = TransactionService(db)

    # Parse dates
    start = None
    if start_date:
        try:
            start = parse_date(start_date)
        except ValueError as e:
            click.echo(f"Error: Invalid start date: {e}", err=True)
            ctx.exit(1)

    end = None
    if end_date:
        try:
            end = parse_date(end_date)
        except ValueError as e:
            click.echo(f"Error: Invalid end date: {e}", err=True)
            ctx.exit(1)

    # Get summary
    summaries = service.get_summary(
        start_date=start, end_date=end, category_path=category
    )

    if not summaries:
        click.echo("No transactions found.")
        return

    # Calculate totals
    total_expenses = sum(s["expenses"] for s in summaries)
    total_income = sum(s["income"] for s in summaries)
    total_count = sum(s["count"] for s in summaries)

    # Display summary
    click.echo("\nCategory Summary:")
    click.echo("-" * 80)
    click.echo(f"{'Category':<40} {'Expenses':<15} {'Income':<15} {'Count':<10}")
    click.echo("-" * 80)

    for s in sorted(summaries, key=lambda x: abs(x["expenses"]), reverse=True):
        category_name = s["category_name"] or "Uncategorized"
        expenses_str = f"${s['expenses']:,.2f}" if s["expenses"] != 0 else "-"
        income_str = f"${s['income']:,.2f}" if s["income"] != 0 else "-"
        click.echo(
            f"{category_name:<40} {expenses_str:<15} {income_str:<15} {s['count']:<10}"
        )

    click.echo("-" * 80)
    click.echo(
        f"{'TOTAL':<40} ${total_expenses:,.2f}     ${total_income:,.2f}     {total_count:<10}"
    )


def register_commands(cli):
    """Register summary command with main CLI."""
    cli.add_command(summary)

