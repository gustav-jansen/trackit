"""Transaction management commands."""

import click
from datetime import date
from decimal import Decimal
from trackit.domain.transaction import TransactionService
from trackit.domain.account import AccountService
from trackit.domain.category import CategoryService
from trackit.utils.date_parser import parse_date
from trackit.utils.amount_parser import parse_amount


@click.group()
def transaction_group():
    """Manage transactions."""
    pass


@transaction_group.command("update")
@click.argument("transaction_id", type=int)
@click.option("--account", help="Account name or ID")
@click.option("--date", help="Transaction date (YYYY-MM-DD or relative like 'today', 'yesterday')")
@click.option("--amount", help="Transaction amount (e.g., 123.45 or -123.45)")
@click.option("--description", help="Transaction description")
@click.option("--reference", help="Reference number")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries') or empty string to clear")
@click.option("--notes", help="Notes")
@click.pass_context
def update_transaction(
    ctx,
    transaction_id: int,
    account: str | None,
    date: str | None,
    amount: str | None,
    description: str | None,
    reference: str | None,
    category: str | None,
    notes: str | None,
) -> None:
    """Update a transaction.
    
    Updates only the fields that are provided. Use --category "" to clear the category.
    
    Examples:
        trackit transaction update 1 --amount -75.00
        trackit transaction update 1 --account "Chase" --category "Food & Dining > Groceries"
        trackit transaction update 1 --category ""  # Clear category
    """
    db = ctx.obj["db"]
    transaction_service = TransactionService(db)
    account_service = AccountService(db)
    category_service = CategoryService(db)

    # Resolve account if provided
    account_id = None
    if account is not None:
        try:
            from trackit.utils.account_resolver import resolve_account
            account_id = resolve_account(account_service, account)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)

    # Parse date if provided
    txn_date = None
    if date is not None:
        try:
            txn_date = parse_date(date)
        except ValueError as e:
            click.echo(f"Error: Invalid date format: {e}", err=True)
            ctx.exit(1)

    # Parse amount if provided
    txn_amount = None
    if amount is not None:
        try:
            txn_amount = parse_amount(amount)
        except ValueError as e:
            click.echo(f"Error: Invalid amount format: {e}", err=True)
            ctx.exit(1)

    # Get category ID if provided
    category_id = None
    clear_category = False
    if category is not None:
        if category == "":
            # Empty string means clear category
            clear_category = True
        else:
            category_obj = category_service.get_category_by_path(category)
            if category_obj is None:
                click.echo(f"Error: Category '{category}' not found", err=True)
                ctx.exit(1)
            category_id = category_obj.id

    # Update transaction
    try:
        transaction_service.update_transaction(
            transaction_id=transaction_id,
            account_id=account_id,
            date=txn_date,
            amount=txn_amount,
            description=description,
            reference_number=reference,
            category_id=category_id,
            notes=notes,
            clear_category=clear_category,
        )
        click.echo(f"Updated transaction {transaction_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@transaction_group.command("delete")
@click.argument("transaction_id", type=int)
@click.pass_context
def delete_transaction(ctx, transaction_id: int) -> None:
    """Delete a transaction.
    
    Examples:
        trackit transaction delete 1
    """
    db = ctx.obj["db"]
    transaction_service = TransactionService(db)

    # Get transaction info for display
    txn = transaction_service.get_transaction(transaction_id)
    if txn is None:
        click.echo(f"Error: Transaction {transaction_id} not found", err=True)
        ctx.exit(1)

    # Confirm deletion
    if not click.confirm(f"Are you sure you want to delete transaction {transaction_id}?"):
        click.echo("Deletion cancelled.")
        return

    try:
        transaction_service.delete_transaction(transaction_id)
        click.echo(f"Deleted transaction {transaction_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli: click.Group) -> None:
    """Register transaction commands with main CLI."""
    cli.add_command(transaction_group, name="transaction")
