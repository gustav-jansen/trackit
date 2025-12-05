"""Transaction viewing commands."""

import click
from datetime import date
from trackit.domain.transaction import TransactionService
from trackit.domain.category import CategoryService
from trackit.domain.account import AccountService
from trackit.utils.date_parser import parse_date


@click.command("view")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--category", help="Category path (e.g., 'Food & Dining > Groceries')")
@click.option("--account", type=int, help="Account ID")
@click.option("--verbose", "-v", is_flag=True, help="Show all columns including notes, reference, and unique_id")
@click.pass_context
def view_transactions(
    ctx, start_date: str, end_date: str, category: str, account: int, verbose: bool
):
    """View transactions with optional filters.
    
    Use --verbose to show all columns including notes, reference number, and unique_id.
    """
    db = ctx.obj["db"]
    service = TransactionService(db)
    category_service = CategoryService(db)
    account_service = AccountService(db)

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

    # Get transactions
    transactions = service.list_transactions(
        start_date=start, end_date=end, category_path=category, account_id=account
    )

    if not transactions:
        click.echo("No transactions found.")
        return

    # Get account names for display
    accounts = {acc["id"]: acc["name"] for acc in account_service.list_accounts()}

    if verbose:
        # Verbose mode: show all columns in a detailed format
        click.echo(f"\nFound {len(transactions)} transaction(s):")
        click.echo("=" * 120)
        
        for txn in transactions:
            account_name = accounts.get(txn["account_id"], "Unknown")
            category_name = ""
            if txn["category_id"]:
                category_name = category_service.format_category_path(txn["category_id"])
            else:
                category_name = "Uncategorized"
            
            amount_str = f"${txn['amount']:,.2f}"
            
            click.echo(f"\nTransaction ID: {txn['id']}")
            click.echo(f"  Date: {txn['date']}")
            click.echo(f"  Amount: {amount_str}")
            click.echo(f"  Account: {account_name} (ID: {txn['account_id']})")
            click.echo(f"  Category: {category_name}")
            if txn["description"]:
                click.echo(f"  Description: {txn['description']}")
            if txn["reference_number"]:
                click.echo(f"  Reference: {txn['reference_number']}")
            click.echo(f"  Unique ID: {txn['unique_id']}")
            if txn["notes"]:
                click.echo(f"  Notes: {txn['notes']}")
            click.echo(f"  Imported: {txn['imported_at']}")
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
            account_name = accounts.get(txn["account_id"], "Unknown")
            category_name = ""
            if txn["category_id"]:
                category_name = category_service.format_category_path(txn["category_id"])

            amount_str = f"${txn['amount']:,.2f}"
            description = (txn["description"] or "")[:30]

            click.echo(
                f"{txn['id']:<6} {str(txn['date']):<12} {amount_str:<12} {account_name:<20} "
                f"{category_name:<30} {description:<30}"
            )


def register_commands(cli):
    """Register view command with main CLI."""
    cli.add_command(view_transactions)

