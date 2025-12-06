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

