"""Account management commands."""

import click
from trackit.domain.account import AccountService


@click.group()
def account_group():
    """Manage accounts."""
    pass


@account_group.command("create")
@click.argument("name", metavar="ACCOUNT_NAME")
@click.option("--bank", help="Bank name (defaults to account name if not provided)")
@click.pass_context
def create_account(ctx, name: str, bank: str | None):
    """Create a new account.

    If --bank is not provided, the bank name will be set to the account name.

    Examples:
        trackit account create "Chase"
        trackit account create "My Checking" --bank "Chase"
        trackit account create "Savings Account" --bank "Wells Fargo"
    """
    db = ctx.obj["db"]
    service = AccountService(db)

    # If bank not provided, use account name as bank name
    bank_name = bank if bank is not None else name

    try:
        account_id = service.create_account(name=name, bank_name=bank_name)
        click.echo(f"Created account '{name}' (ID: {account_id})")
        if bank is None:
            click.echo(f"Bank name set to '{bank_name}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@account_group.command("list")
@click.pass_context
def list_accounts(ctx):
    """List all accounts."""
    db = ctx.obj["db"]
    service = AccountService(db)

    accounts = service.list_accounts()
    if not accounts:
        click.echo("No accounts found.")
        return

    click.echo("\nAccounts:")
    click.echo("-" * 60)
    for acc in accounts:
        click.echo(f"ID: {acc.id:3d} | {acc.name:20s} | Bank: {acc.bank_name}")


@account_group.command("rename")
@click.argument("account", metavar="ACCOUNT")
@click.argument("new_name", metavar="NEW_NAME")
@click.option("--bank", help="New bank name (optional)")
@click.pass_context
def rename_account(ctx, account: str, new_name: str, bank: str | None) -> None:
    """Rename an account.

    ACCOUNT can be an account name or ID.
    NEW_NAME is the new name for the account.

    Examples:
        trackit account rename "Chase" "Chase Checking"
        trackit account rename 1 "My Account" --bank "Wells Fargo"
    """
    db = ctx.obj["db"]
    service = AccountService(db)

    # Resolve account
    try:
        from trackit.utils.account_resolver import resolve_account
        account_id = resolve_account(service, account)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

    try:
        service.rename_account(account_id=account_id, name=new_name, bank_name=bank)
        click.echo(f"Renamed account to '{new_name}'")
        if bank is not None:
            click.echo(f"Bank name updated to '{bank}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@account_group.command("delete")
@click.argument("account", metavar="ACCOUNT")
@click.pass_context
def delete_account(ctx, account: str) -> None:
    """Delete an account.

    ACCOUNT can be an account name or ID.

    The account can only be deleted if it has no associated transactions
    or CSV formats. Use 'transaction delete' and 'format delete' commands
    to remove them first, or reassign them to other accounts.

    Examples:
        trackit account delete "Chase"
        trackit account delete 1
    """
    db = ctx.obj["db"]
    service = AccountService(db)

    # Resolve account
    try:
        from trackit.utils.account_resolver import resolve_account
        account_id = resolve_account(service, account)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

    # Get account info for display
    account_obj = service.get_account(account_id)
    if account_obj is None:
        click.echo(f"Error: Account not found", err=True)
        ctx.exit(1)

    # Check for dependencies
    transaction_count = db.get_account_transaction_count(account_id)
    format_count = db.get_account_format_count(account_id)

    if transaction_count > 0 or format_count > 0:
        parts = []
        if transaction_count > 0:
            parts.append(f"{transaction_count} transaction{'s' if transaction_count != 1 else ''}")
        if format_count > 0:
            parts.append(f"{format_count} CSV format{'s' if format_count != 1 else ''}")
        click.echo(
            f"Error: Cannot delete account '{account_obj.name}': it has {', '.join(parts)}.",
            err=True
        )
        click.echo("Please reassign or delete them first.", err=True)
        ctx.exit(1)

    # Confirm deletion
    if not click.confirm(f"Are you sure you want to delete account '{account_obj.name}' (ID: {account_id})?"):
        click.echo("Deletion cancelled.")
        return

    try:
        service.delete_account(account_id)
        click.echo(f"Deleted account '{account_obj.name}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register account commands with main CLI."""
    cli.add_command(account_group, name="account")

