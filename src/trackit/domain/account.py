"""Account domain service."""

from typing import Optional
from trackit.database.base import Database
from trackit.domain.entities import Account as AccountEntity


class AccountService:
    """Service for managing accounts."""

    def __init__(self, db: Database):
        """Initialize account service.

        Args:
            db: Database instance
        """
        self.db = db

    def create_account(self, name: str, bank_name: str) -> int:
        """Create a new account.

        Args:
            name: Account name
            bank_name: Bank name

        Returns:
            Account ID

        Raises:
            ValueError: If account name already exists
        """
        # Check if account with same name exists
        accounts = self.db.list_accounts()
        for acc in accounts:
            if acc.name == name:
                raise ValueError(f"Account with name '{name}' already exists")

        return self.db.create_account(name=name, bank_name=bank_name)

    def get_account(self, account_id: int) -> Optional[AccountEntity]:
        """Get account by ID.

        Args:
            account_id: Account ID

        Returns:
            Account entity or None if not found
        """
        return self.db.get_account(account_id)

    def list_accounts(self) -> list[AccountEntity]:
        """List all accounts.

        Returns:
            List of account entities
        """
        return self.db.list_accounts()

    def rename_account(self, account_id: int, name: str, bank_name: Optional[str] = None) -> None:
        """Rename an account.

        Args:
            account_id: Account ID to rename
            name: New account name
            bank_name: Optional new bank name (if None, bank_name is not updated)

        Raises:
            ValueError: If account not found or name already exists
        """
        # Validate account exists
        account = self.db.get_account(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")

        # Check for duplicate names (excluding current account)
        accounts = self.db.list_accounts()
        for acc in accounts:
            if acc.id != account_id and acc.name == name:
                raise ValueError(f"Account with name '{name}' already exists")

        self.db.update_account_name(account_id=account_id, name=name, bank_name=bank_name)

    def delete_account(self, account_id: int) -> None:
        """Delete an account.

        Args:
            account_id: Account ID to delete

        Raises:
            ValueError: If account not found or has associated transactions/formats
        """
        # Validate account exists
        account = self.db.get_account(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")

        # Check for associated transactions and formats
        transaction_count = self.db.get_account_transaction_count(account_id)
        format_count = self.db.get_account_format_count(account_id)

        if transaction_count > 0 or format_count > 0:
            parts = []
            if transaction_count > 0:
                parts.append(f"{transaction_count} transaction{'s' if transaction_count != 1 else ''}")
            if format_count > 0:
                parts.append(f"{format_count} CSV format{'s' if format_count != 1 else ''}")
            raise ValueError(
                f"Cannot delete account {account_id}: it has {', '.join(parts)}. "
                f"Please reassign or delete them first."
            )

        self.db.delete_account(account_id)

