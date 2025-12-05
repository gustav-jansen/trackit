"""Category assignment and notes commands."""

import click
from trackit.domain.transaction import TransactionService


@click.command("categorize")
@click.argument("transaction_id", type=int)
@click.argument("category_path")
@click.pass_context
def categorize_transaction(ctx, transaction_id: int, category_path: str):
    """Assign a category to a transaction."""
    db = ctx.obj["db"]
    service = TransactionService(db)

    try:
        service.update_category(transaction_id=transaction_id, category_path=category_path)
        click.echo(f"Transaction {transaction_id} categorized as '{category_path}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
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

