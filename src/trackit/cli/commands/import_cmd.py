"""CSV import command."""

import click
from trackit.domain.csv_import import CSVImportService
from trackit.cli.error_handling import handle_domain_error
from trackit.domain.errors import DomainError


@click.command("import")
@click.argument("csv_file", type=click.Path(exists=True))
@click.option("--format", required=True, help="CSV format name")
@click.pass_context
def import_csv(ctx, csv_file: str, format: str):
    """Import transactions from a CSV file."""
    db = ctx.obj["db"]
    service = CSVImportService(db)

    try:
        result = service.import_csv(csv_file_path=csv_file, format_name=format)
        click.echo(f"\nImport complete:")
        click.echo(f"  Imported: {result['imported']} transactions")
        if result["skipped"] > 0:
            click.echo(f"  Skipped: {result['skipped']} duplicates")
            # Show details for each skipped transaction
            for skipped in result.get("skipped_details", []):
                details = skipped["details"]
                click.echo(
                    f"    Row {skipped['row_num']}: Skipped duplicate - "
                    f"Date: {details['date']}, "
                    f"Description: {details['description']}, "
                    f"Amount: {details['amount']}"
                )
        if result["errors"]:
            click.echo(f"  Errors: {len(result['errors'])}")
            for error in result["errors"]:
                click.echo(f"    {error}", err=True)
    except (DomainError, ValueError) as e:
        handle_domain_error(ctx, e)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def register_commands(cli):
    """Register import command with main CLI."""
    cli.add_command(import_csv)
