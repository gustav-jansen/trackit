"""Main CLI entry point."""

import click
from trackit.database.factories import create_sqlite_database

# Import and register all commands at module level
from trackit.cli.commands import (
    account,
    format,
    import_cmd,
    categorize,
    summary,
    init_categories,
    category,
    add,
    transaction,
)


@click.group()
@click.option(
    "--db-path",
    type=click.Path(),
    help="Path to database file (overrides TRACKIT_DB_PATH environment variable)",
    envvar="TRACKIT_DB_PATH",
)
@click.pass_context
def cli(ctx, db_path: str | None):
    """Trackit - Expense tracking application.

    Track and categorize your expenses with support for importing CSV files
    from multiple banks with different formats.
    """
    ctx.ensure_object(dict)

    # Initialize database connection only when actually running a command
    # (not when showing help)
    if ctx.invoked_subcommand is not None:
        db = create_sqlite_database(database_path=db_path)
        db.connect()
        db.initialize_schema()
        ctx.obj["db"] = db


# Register all commands
account.register_commands(cli)
format.register_commands(cli)
import_cmd.register_commands(cli)
categorize.register_commands(cli)
summary.register_commands(cli)
init_categories.register_commands(cli)
category.register_commands(cli)
add.register_commands(cli)
transaction.register_commands(cli)


def main():
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()

