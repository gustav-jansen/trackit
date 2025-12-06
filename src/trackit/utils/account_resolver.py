"""Utility for resolving account names to IDs."""

from typing import Optional
from trackit.domain.account import AccountService


def resolve_account(account_service: AccountService, account: str | int) -> int:
    """Resolve account name or ID to account ID.
    
    Args:
        account_service: AccountService instance
        account: Account name (str) or ID (int or string representation of int)
    
    Returns:
        Account ID
    
    Raises:
        ValueError: If account is not found
    """
    # If it's already an integer, use it as ID
    if isinstance(account, int):
        account_obj = account_service.get_account(account)
        if account_obj is None:
            raise ValueError(f"Account ID {account} not found")
        return account
    
    # Try to parse as integer (handles string IDs like "1")
    try:
        account_id = int(account)
        # Successfully parsed as int, treat as ID
        account_obj = account_service.get_account(account_id)
        if account_obj is None:
            raise ValueError(f"Account ID {account_id} not found")
        return account_id
    except (ValueError, TypeError):
        # Not a number, treat as name
        pass
    
    # Try to find by name
    accounts = account_service.list_accounts()
    for acc in accounts:
        if acc.name == account:
            return acc.id
    
    raise ValueError(f"Account '{account}' not found")

