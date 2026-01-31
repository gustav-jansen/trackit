"""CLI helpers for account resolution and error handling."""

from __future__ import annotations

import click
from trackit.domain.account import AccountService
from trackit.utils.account_resolver import resolve_account


def resolve_account_or_exit(
    ctx: click.Context, account_service: AccountService, account: str | int
) -> int:
    """Resolve account name or ID, or exit with a CLI error.

    This keeps error messaging and exit behavior consistent across commands.
    """
    try:
        return resolve_account(account_service, account)
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(1)
