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
@click.option(
    "--debit-credit-format",
    is_flag=True,
    default=False,
    help="Use separate debit and credit columns instead of a single amount column",
)
@click.option(
    "--negate-debit",
    is_flag=True,
    default=False,
    help="Negate debit values during import (e.g., positive debit -> negative amount)",
)
@click.option(
    "--negate-credit",
    is_flag=True,
    default=False,
    help="Negate credit values during import (e.g., negative credit -> positive amount)",
)
@click.pass_context
def create_format(
    ctx, name: str, account: str, debit_credit_format: bool, negate_debit: bool, negate_credit: bool
):
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
        format_id = service.create_format(
            name=name,
            account_id=account_id,
            is_debit_credit_format=debit_credit_format,
            negate_debit=negate_debit,
            negate_credit=negate_credit,
        )
        click.echo(f"Created CSV format '{name}' (ID: {format_id})")
        if debit_credit_format:
            click.echo("Debit/Credit format enabled")
            if negate_debit:
                click.echo("  Debit values will be negated")
            if negate_credit:
                click.echo("  Credit values will be negated")
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
            format_id=fmt.id,
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
        mappings = service.get_mappings(fmt.id)
        is_valid, missing = service.validate_format(fmt.id)

        status = "✓" if is_valid else "✗"
        click.echo(f"{status} {fmt.name} (ID: {fmt.id}, Account: {fmt.account_id})")
        if fmt.is_debit_credit_format:
            click.echo("  Type: Debit/Credit Format")
            if fmt.negate_debit:
                click.echo("    Debit values will be negated")
            if fmt.negate_credit:
                click.echo("    Credit values will be negated")
        if not is_valid:
            click.echo(f"  Missing required fields: {', '.join(missing)}")
        if mappings:
            click.echo("  Mappings:")
            for m in mappings:
                req = " (required)" if m.is_required else ""
                click.echo(f"    {m.csv_column_name} -> {m.db_field_name}{req}")


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

    mappings = service.get_mappings(fmt.id)
    is_valid, missing = service.validate_format(fmt.id)

    click.echo(f"\nFormat: {fmt.name}")
    click.echo(f"ID: {fmt.id}")
    click.echo(f"Account ID: {fmt.account_id}")
    click.echo(f"Type: {'Debit/Credit Format' if fmt.is_debit_credit_format else 'Standard Format'}")
    if fmt.is_debit_credit_format:
        click.echo(f"  Negate Debit: {'Yes' if fmt.negate_debit else 'No'}")
        click.echo(f"  Negate Credit: {'Yes' if fmt.negate_credit else 'No'}")
    click.echo(f"Valid: {'Yes' if is_valid else 'No'}")
    if not is_valid:
        click.echo(f"Missing required fields: {', '.join(missing)}")

    click.echo("\nColumn Mappings:")
    if not mappings:
        click.echo("  (none)")
    else:
        for m in mappings:
            req = " (required)" if m.is_required else ""
            click.echo(f"  {m.csv_column_name} -> {m.db_field_name}{req}")


@format_group.command("update")
@click.argument("format_name")
@click.option("--name", help="New format name")
@click.option("--account", help="Account name or ID to reassign format to")
@click.option(
    "--debit-credit-format/--no-debit-credit-format",
    default=None,
    help="Enable or disable debit/credit format",
)
@click.option(
    "--negate-debit/--no-negate-debit",
    default=None,
    help="Enable or disable debit negation",
)
@click.option(
    "--negate-credit/--no-negate-credit",
    default=None,
    help="Enable or disable credit negation",
)
@click.pass_context
def update_format(
    ctx,
    format_name: str,
    name: str | None,
    account: str | None,
    debit_credit_format: bool | None,
    negate_debit: bool | None,
    negate_credit: bool | None,
) -> None:
    """Update a CSV format.

    Updates only the fields that are provided.

    Examples:
        trackit format update "Chase Format" --name "Chase New Format"
        trackit format update "Chase Format" --account "Wells Fargo"
        trackit format update "Chase Format" --name "New Name" --account "Chase"
    """
    db = ctx.obj["db"]
    service = CSVFormatService(db)
    account_service = AccountService(db)

    # Get format
    fmt = service.get_format_by_name(format_name)
    if fmt is None:
        click.echo(f"Error: CSV format '{format_name}' not found", err=True)
        ctx.exit(1)

    # Resolve account if provided
    account_id = None
    if account is not None:
        try:
            from trackit.utils.account_resolver import resolve_account
            account_id = resolve_account(account_service, account)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)

    try:
        service.update_format(
            format_id=fmt.id,
            name=name,
            account_id=account_id,
            is_debit_credit_format=debit_credit_format,
            negate_debit=negate_debit,
            negate_credit=negate_credit,
        )
        click.echo(f"Updated format '{format_name}'")
        if name is not None:
            click.echo(f"  New name: '{name}'")
        if account is not None:
            click.echo(f"  Reassigned to account: '{account}'")
        if debit_credit_format is not None:
            click.echo(f"  Debit/Credit format: {'enabled' if debit_credit_format else 'disabled'}")
        if negate_debit is not None:
            click.echo(f"  Negate debit: {'enabled' if negate_debit else 'disabled'}")
        if negate_credit is not None:
            click.echo(f"  Negate credit: {'enabled' if negate_credit else 'disabled'}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@format_group.command("delete")
@click.argument("format_name")
@click.pass_context
def delete_format(ctx, format_name: str) -> None:
    """Delete a CSV format.

    Examples:
        trackit format delete "Chase Format"
    """
    db = ctx.obj["db"]
    service = CSVFormatService(db)

    # Get format
    fmt = service.get_format_by_name(format_name)
    if fmt is None:
        click.echo(f"Error: CSV format '{format_name}' not found", err=True)
        ctx.exit(1)

    # Confirm deletion
    if not click.confirm(f"Are you sure you want to delete format '{format_name}' (ID: {fmt.id})?"):
        click.echo("Deletion cancelled.")
        return

    try:
        service.delete_format(fmt.id)
        click.echo(f"Deleted format '{format_name}'")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register format commands with main CLI."""
    cli.add_command(format_group, name="format")

