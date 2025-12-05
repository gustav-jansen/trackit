"""Category assignment and notes commands."""

import click
from trackit.domain.transaction import TransactionService


@click.command("categorize")
@click.argument("transaction_ids", nargs=-1, required=True, type=int)
@click.argument("category_path", nargs=1)
@click.pass_context
def categorize_transaction(ctx, transaction_ids: tuple[int, ...], category_path: str):
    """Assign a category to one or more transactions.
    
    Examples:
        trackit categorize 1 "Food & Dining > Groceries"
        trackit categorize 1 2 3 4 5 "Food & Dining > Groceries"
    """
    db = ctx.obj["db"]
    service = TransactionService(db)

    # Validate category exists before processing any transactions
    try:
        # Try to get category to validate it exists
        from trackit.domain.category import CategoryService
        category_service = CategoryService(db)
        category = category_service.get_category_by_path(category_path)
        if category is None:
            click.echo(f"Error: Category '{category_path}' not found", err=True)
            ctx.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

    # Remove duplicates while preserving order
    unique_ids = []
    seen = set()
    for txn_id in transaction_ids:
        if txn_id not in seen:
            unique_ids.append(txn_id)
            seen.add(txn_id)

    if not unique_ids:
        click.echo("Error: No transaction IDs provided", err=True)
        ctx.exit(1)

    # Process transactions
    successes = []
    errors = []

    if len(unique_ids) > 1:
        click.echo(f"Categorizing {len(unique_ids)} transactions as '{category_path}'...")

    for txn_id in unique_ids:
        try:
            service.update_category(transaction_id=txn_id, category_path=category_path)
            successes.append(txn_id)
            if len(unique_ids) == 1:
                # Single transaction - use original simple message
                click.echo(f"Transaction {txn_id} categorized as '{category_path}'")
            else:
                click.echo(f"✓ Transaction {txn_id} categorized")
        except ValueError as e:
            errors.append((txn_id, str(e)))
            if len(unique_ids) > 1:
                click.echo(f"✗ Transaction {txn_id}: {e}")

    # Show summary for multiple transactions
    if len(unique_ids) > 1:
        click.echo(f"\nResults: {len(successes)} succeeded, {len(errors)} failed")
        if errors:
            ctx.exit(1)
    elif errors:
        # Single transaction with error
        click.echo(f"Error: {errors[0][1]}", err=True)
        ctx.exit(1)


@click.command("notes")
@click.argument("transaction_id", type=int)
@click.argument("notes", required=False)
@click.option("--clear", is_flag=True, help="Clear notes")
@click.pass_context
def update_notes(ctx, transaction_id: int, notes: str, clear: bool):
    """Update transaction notes."""
    db = ctx.obj["db"]
    service = TransactionService(db)

    if clear:
        notes = None
    elif not notes:
        # If no notes provided and not clearing, prompt or show current notes
        txn = service.get_transaction(transaction_id)
        if txn is None:
            click.echo(f"Error: Transaction {transaction_id} not found", err=True)
            ctx.exit(1)
        current_notes = txn.get("notes")
        if current_notes:
            click.echo(f"Current notes: {current_notes}")
        else:
            click.echo("No notes set. Provide notes text to update.")
        return

    try:
        service.update_notes(transaction_id=transaction_id, notes=notes)
        if notes:
            click.echo(f"Updated notes for transaction {transaction_id}")
        else:
            click.echo(f"Cleared notes for transaction {transaction_id}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register categorize and notes commands with main CLI."""
    cli.add_command(categorize_transaction)
    cli.add_command(update_notes)

