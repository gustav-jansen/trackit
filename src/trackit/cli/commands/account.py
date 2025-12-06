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


def register_commands(cli):
    """Register account commands with main CLI."""
    cli.add_command(account_group, name="account")

