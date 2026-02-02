"""Transaction management commands."""

import click
from datetime import date
from decimal import Decimal
from trackit.domain.transaction import TransactionService
from trackit.domain.account import AccountService
from trackit.domain.category import CategoryService
from trackit.cli.date_filters import resolve_cli_date_range
from trackit.cli.account_resolution import resolve_account_or_exit
from trackit.cli.error_handling import handle_domain_error
from trackit.domain.errors import DomainError
from trackit.utils.date_parser import parse_date
from trackit.utils.amount_parser import parse_amount


@click.group()
def transaction_group():
    """Manage transactions."""
    pass


@transaction_group.command("update")
@click.argument("transaction_id", type=int)
@click.option("--account", help="Account name or ID")
@click.option(
    "--date", help="Transaction date (YYYY-MM-DD or relative like 'today', 'yesterday')"
)
@click.option("--amount", help="Transaction amount (e.g., 123.45 or -123.45)")
@click.option("--description", help="Transaction description")
@click.option("--reference", help="Reference number")
@click.option(
    "--category",
    help="Category path (e.g., 'Food & Dining > Groceries') or empty string to clear",
)
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
        account_id = resolve_account_or_exit(ctx, account_service, account)

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
    except (DomainError, ValueError) as e:
        handle_domain_error(ctx, e)


@transaction_group.command("list")
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
@click.option("--account", help="Account name or ID")
@click.option(
    "--uncategorized", is_flag=True, help="Show only uncategorized transactions"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all columns including notes, reference, and unique_id",
)
@click.pass_context
def list_transactions(
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
    account: str,
    uncategorized: bool,
    verbose: bool,
):
    """View transactions with optional filters.

    Use --verbose to show all columns including notes, reference number, and unique_id.
    Use --uncategorized to show only transactions without a category.
    Account can be specified by name or ID.
    """
    db = ctx.obj["db"]
    service = TransactionService(db)
    category_service = CategoryService(db)
    account_service = AccountService(db)

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
    )

    # Resolve account name to ID if provided
    account_id = None
    if account:
        account_id = resolve_account_or_exit(ctx, account_service, account)

    # Handle uncategorized filter
    if uncategorized:
        category = ""  # Empty category path means uncategorized

    # Get transactions
    transactions = service.list_transactions(
        start_date=start, end_date=end, category_path=category, account_id=account_id
    )

    if not transactions:
        click.echo("No transactions found.")
        return

    # Get account names for display
    accounts = {acc.id: acc.name for acc in account_service.list_accounts()}

    if verbose:
        # Verbose mode: show all columns in a detailed format
        click.echo(f"\nFound {len(transactions)} transaction(s):")
        click.echo("=" * 120)

        for txn in transactions:
            account_name = accounts.get(txn.account_id, "Unknown")
            category_name = ""
            if txn.category_id:
                category_name = category_service.format_category_path(txn.category_id)
            else:
                category_name = "Uncategorized"

            amount_str = f"${txn.amount:,.2f}"

            click.echo(f"\nTransaction ID: {txn.id}")
            click.echo(f"  Date: {txn.date}")
            click.echo(f"  Amount: {amount_str}")
            click.echo(f"  Account: {account_name} (ID: {txn.account_id})")
            click.echo(f"  Category: {category_name}")
            if txn.description:
                click.echo(f"  Description: {txn.description}")
            if txn.reference_number:
                click.echo(f"  Reference: {txn.reference_number}")
            click.echo(f"  Unique ID: {txn.unique_id}")
            if txn.notes:
                click.echo(f"  Notes: {txn.notes}")
            click.echo(f"  Imported: {txn.imported_at}")
            click.echo("-" * 120)
    else:
        # Compact mode: show key columns in a table
        click.echo(f"\nFound {len(transactions)} transaction(s):")
        click.echo("-" * 100)
        click.echo(
            f"{'ID':<6} {'Date':<12} {'Amount':<12} {'Account':<20} {'Category':<30} {'Description':<30}"
        )
        click.echo("-" * 100)

        for txn in transactions:
            account_name = accounts.get(txn.account_id, "Unknown")
            category_name = ""
            if txn.category_id:
                category_name = category_service.format_category_path(txn.category_id)

            amount_str = f"${txn.amount:,.2f}"
            description = (txn.description or "")[:30]

            click.echo(
                f"{txn.id:<6} {str(txn.date):<12} {amount_str:<12} {account_name:<20} "
                f"{category_name:<30} {description:<30}"
            )

    # Show totals
    if transactions:
        total_expenses = sum(txn.amount for txn in transactions if txn.amount < 0)
        total_income = sum(txn.amount for txn in transactions if txn.amount > 0)
        click.echo("-" * 100)
        click.echo(
            f"{'TOTAL':<6} {'':<12} Expenses: ${abs(total_expenses):,.2f} | "
            f"Income: ${total_income:,.2f} | Count: {len(transactions)}"
        )


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
    if not click.confirm(
        f"Are you sure you want to delete transaction {transaction_id}?"
    ):
        click.echo("Deletion cancelled.")
        return

    try:
        transaction_service.delete_transaction(transaction_id)
        click.echo(f"Deleted transaction {transaction_id}")
    except (DomainError, ValueError) as e:
        handle_domain_error(ctx, e)


def register_commands(cli: click.Group) -> None:
    """Register transaction commands with main CLI."""
    cli.add_command(transaction_group, name="transaction")
