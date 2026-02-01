"""Add transaction command."""

import click
from datetime import date
from decimal import Decimal
from trackit.domain.transaction import TransactionService
from trackit.domain.account import AccountService
from trackit.domain.category import CategoryService
from trackit.cli.account_resolution import resolve_account_or_exit
from trackit.utils.date_parser import parse_date
from trackit.utils.amount_parser import parse_amount


@click.command("add")
@click.option("--account", required=True, help="Account name or ID")
@click.option(
    "--date",
    required=True,
    help="Transaction date (YYYY-MM-DD or relative like 'today', 'yesterday')",
)
@click.option(
    "--amount", required=True, help="Transaction amount (e.g., 123.45 or -123.45)"
)
@click.option("--description", help="Transaction description")
@click.option("--reference", help="Reference number")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.option("--notes", help="Notes")
@click.option(
    "--unique-id", help="Unique transaction ID (auto-generated if not provided)"
)
@click.pass_context
def add_transaction(
    ctx,
    account: str,
    date: str,
    amount: str,
    description: str | None,
    reference: str | None,
    category: str | None,
    notes: str | None,
    unique_id: str | None,
):
    """Add a transaction manually.

    Examples:
        trackit add --account 1 --date 2024-01-15 --amount -50.00 --description "Grocery store"
        trackit add --account 1 --date 2024-01-15 --amount 1000.00 --category "Income > Salary"
    """
    db = ctx.obj["db"]
    transaction_service = TransactionService(db)
    account_service = AccountService(db)
    category_service = CategoryService(db)

    # Resolve account name to ID
    account_id = resolve_account_or_exit(ctx, account_service, account)
    account_obj = account_service.get_account(account_id)

    # Parse date
    try:
        txn_date = parse_date(date)
    except ValueError as e:
        click.echo(f"Error: Invalid date format: {e}", err=True)
        ctx.exit(1)

    # Parse amount
    try:
        txn_amount = parse_amount(amount)
    except ValueError as e:
        click.echo(f"Error: Invalid amount format: {e}", err=True)
        ctx.exit(1)

    # Get category ID if provided
    category_id = None
    if category:
        try:
            category_obj = category_service.require_category_by_path(category)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)
        category_id = category_obj.id

    # Generate unique_id if not provided
    if unique_id is None:
        # Generate a unique ID based on timestamp and account
        import time

        unique_id = f"manual_{account_id}_{int(time.time() * 1000000)}"

    # Create transaction
    try:
        transaction_id = transaction_service.create_transaction(
            unique_id=unique_id,
            account_id=account_id,
            date=txn_date,
            amount=txn_amount,
            description=description,
            reference_number=reference,
            category_id=category_id,
            notes=notes,
        )
        click.echo(f"Created transaction {transaction_id}")
        click.echo(f"  Account: {account_obj.name}")
        click.echo(f"  Date: {txn_date}")
        click.echo(f"  Amount: ${txn_amount:,.2f}")
        if description:
            click.echo(f"  Description: {description}")
        if category:
            click.echo(f"  Category: {category}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register add command with main CLI."""
    cli.add_command(add_transaction)
