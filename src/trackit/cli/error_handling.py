"""CLI error handling helpers."""

import click

from trackit.domain.errors import DomainError


def handle_domain_error(ctx: click.Context, error: DomainError | ValueError) -> None:
    """Render a domain error and exit with failure."""
    click.echo(f"Error: {error}", err=True)
    ctx.exit(1)
