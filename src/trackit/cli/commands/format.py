"""CSV format management commands."""

import click
from trackit.domain.csv_format import CSVFormatService
from trackit.domain.account import AccountService


@click.group()
def format_group():
    """Manage CSV formats."""
    pass


@format_group.command("create")
@click.argument("name")
@click.option("--account", required=True, help="Account name or ID")
@click.pass_context
def create_format(ctx, name: str, account: str):
    """Create a new CSV format."""
    db = ctx.obj["db"]
    service = CSVFormatService(db)
    account_service = AccountService(db)

    # Resolve account name to ID
    try:
        from trackit.utils.account_resolver import resolve_account
        account_id = resolve_account(account_service, account)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

    try:
        format_id = service.create_format(name=name, account_id=account_id)
        click.echo(f"Created CSV format '{name}' (ID: {format_id})")
        click.echo("Use 'format map' to add column mappings.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@format_group.command("map")
@click.argument("format_name")
@click.argument("csv_column")
@click.argument("db_field")
@click.option("--required", is_flag=True, help="Mark this mapping as required")
@click.pass_context
def map_column(ctx, format_name: str, csv_column: str, db_field: str, required: bool):
    """Map a CSV column to a database field."""
    db = ctx.obj["db"]
    service = CSVFormatService(db)

    fmt = service.get_format_by_name(format_name)
    if fmt is None:
        click.echo(f"Error: CSV format '{format_name}' not found", err=True)
        ctx.exit(1)

    try:
        mapping_id = service.add_mapping(
            format_id=fmt["id"],
            csv_column_name=csv_column,
            db_field_name=db_field,
            is_required=required,
        )
        click.echo(
            f"Mapped CSV column '{csv_column}' to '{db_field}' "
            f"(ID: {mapping_id}, Required: {required})"
        )
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@format_group.command("list")
@click.option("--account", help="Filter by account name or ID")
@click.pass_context
def list_formats(ctx, account):
    """List CSV formats."""
    db = ctx.obj["db"]
    service = CSVFormatService(db)
    account_service = AccountService(db)

    account_id = None
    if account:
        try:
            from trackit.utils.account_resolver import resolve_account
            account_id = resolve_account(account_service, account)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)

    formats = service.list_formats(account_id=account_id)
    if not formats:
        click.echo("No CSV formats found.")
        return

    click.echo("\nCSV Formats:")
    click.echo("-" * 60)
    for fmt in formats:
        mappings = service.get_mappings(fmt["id"])
        is_valid, missing = service.validate_format(fmt["id"])

        status = "✓" if is_valid else "✗"
        click.echo(f"{status} {fmt['name']} (ID: {fmt['id']}, Account: {fmt['account_id']})")
        if not is_valid:
            click.echo(f"  Missing required fields: {', '.join(missing)}")
        if mappings:
            click.echo("  Mappings:")
            for m in mappings:
                req = " (required)" if m["is_required"] else ""
                click.echo(f"    {m['csv_column_name']} -> {m['db_field_name']}{req}")


@format_group.command("show")
@click.argument("format_name")
@click.pass_context
def show_format(ctx, format_name: str):
    """Show details of a CSV format."""
    db = ctx.obj["db"]
    service = CSVFormatService(db)

    fmt = service.get_format_by_name(format_name)
    if fmt is None:
        click.echo(f"Error: CSV format '{format_name}' not found", err=True)
        ctx.exit(1)

    mappings = service.get_mappings(fmt["id"])
    is_valid, missing = service.validate_format(fmt["id"])

    click.echo(f"\nFormat: {fmt['name']}")
    click.echo(f"ID: {fmt['id']}")
    click.echo(f"Account ID: {fmt['account_id']}")
    click.echo(f"Valid: {'Yes' if is_valid else 'No'}")
    if not is_valid:
        click.echo(f"Missing required fields: {', '.join(missing)}")

    click.echo("\nColumn Mappings:")
    if not mappings:
        click.echo("  (none)")
    else:
        for m in mappings:
            req = " (required)" if m["is_required"] else ""
            click.echo(f"  {m['csv_column_name']} -> {m['db_field_name']}{req}")


def register_commands(cli):
    """Register format commands with main CLI."""
    cli.add_command(format_group, name="format")

