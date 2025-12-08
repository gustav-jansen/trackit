"""Transaction domain service."""

from typing import Optional
from datetime import date
from decimal import Decimal
from trackit.database.base import Database
from trackit.domain.entities import Transaction as TransactionEntity


class TransactionService:
    """Service for managing transactions."""

    def __init__(self, db: Database):
        """Initialize transaction service.

        Args:
            db: Database instance
        """
        self.db = db

    def create_transaction(
        self,
        unique_id: str,
        account_id: int,
        date: date,
        amount: Decimal,
        description: Optional[str] = None,
        reference_number: Optional[str] = None,
        category_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Create a transaction.

        Args:
            unique_id: Unique transaction ID from CSV
            account_id: Account ID
            date: Transaction date
            amount: Transaction amount
            description: Optional description
            reference_number: Optional reference number
            category_id: Optional category ID
            notes: Optional notes

        Returns:
            Transaction ID

        Raises:
            ValueError: If account doesn't exist or transaction already exists
        """
        # Verify account exists
        account = self.db.get_account(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")

        # Check for duplicate
        if self.db.transaction_exists(account_id, unique_id):
            raise ValueError(
                f"Transaction with unique_id '{unique_id}' already exists for account {account_id}"
            )

        # Verify category if provided
        if category_id is not None:
            category = self.db.get_category(category_id)
            if category is None:
                raise ValueError(f"Category {category_id} not found")

        return self.db.create_transaction(
            unique_id=unique_id,
            account_id=account_id,
            date=date,
            amount=amount,
            description=description,
            reference_number=reference_number,
            category_id=category_id,
            notes=notes,
        )

    def get_transaction(self, transaction_id: int) -> Optional[TransactionEntity]:
        """Get transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction entity or None if not found
        """
        return self.db.get_transaction(transaction_id)

    def update_category(self, transaction_id: int, category_path: Optional[str]) -> None:
        """Update transaction category.

        Args:
            transaction_id: Transaction ID
            category_path: Category path (e.g., "Food & Dining > Groceries") or None

        Raises:
            ValueError: If transaction or category doesn't exist
        """
        # Verify transaction exists
        txn = self.db.get_transaction(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        category_id = None
        if category_path is not None:
            category = self.db.get_category_by_path(category_path)
            if category is None:
                raise ValueError(f"Category '{category_path}' not found")
            category_id = category.id

        self.db.update_transaction_category(transaction_id, category_id)

    def update_notes(self, transaction_id: int, notes: Optional[str]) -> None:
        """Update transaction notes.

        Args:
            transaction_id: Transaction ID
            notes: Notes text or None

        Raises:
            ValueError: If transaction doesn't exist
        """
        # Verify transaction exists
        txn = self.db.get_transaction(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        self.db.update_transaction_notes(transaction_id, notes)

    def update_transaction(
        self,
        transaction_id: int,
        account_id: Optional[int] = None,
        date: Optional[date] = None,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None,
        reference_number: Optional[str] = None,
        category_id: Optional[int] = None,
        notes: Optional[str] = None,
        clear_category: bool = False,
    ) -> None:
        """Update transaction fields.

        Args:
            transaction_id: Transaction ID to update
            account_id: Optional new account ID
            date: Optional new date
            amount: Optional new amount
            description: Optional new description
            reference_number: Optional new reference number
            category_id: Optional new category ID
            notes: Optional new notes
            clear_category: If True, clear the category (category_id must be None)

        Raises:
            ValueError: If transaction doesn't exist or account/category doesn't exist
        """
        # Verify transaction exists
        txn = self.db.get_transaction(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Verify account if provided
        if account_id is not None:
            account = self.db.get_account(account_id)
            if account is None:
                raise ValueError(f"Account {account_id} not found")

        # Handle category update or clear
        if clear_category:
            if category_id is not None:
                raise ValueError("Cannot set both category_id and clear_category")
            category_id_to_update = None
            update_category_flag = True
        elif category_id is not None:
            # Verify category exists
            category = self.db.get_category(category_id)
            if category is None:
                raise ValueError(f"Category {category_id} not found")
            category_id_to_update = category_id
            update_category_flag = False
        else:
            # category_id not provided, don't update
            category_id_to_update = None
            update_category_flag = False

        self.db.update_transaction(
            transaction_id=transaction_id,
            account_id=account_id,
            date=date,
            amount=amount,
            description=description,
            reference_number=reference_number,
            category_id=category_id_to_update,
            notes=notes,
            update_category=update_category_flag,
        )

    def delete_transaction(self, transaction_id: int) -> None:
        """Delete a transaction.

        Args:
            transaction_id: Transaction ID to delete

        Raises:
            ValueError: If transaction doesn't exist
        """
        # Verify transaction exists
        txn = self.db.get_transaction(transaction_id)
        if txn is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        self.db.delete_transaction(transaction_id)

    def list_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> list[TransactionEntity]:
        """List transactions with filters.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category_path: Optional category path filter (empty string for uncategorized)
            account_id: Optional account ID filter

        Returns:
            List of transaction entities
        """
        category_id = None
        uncategorized = False
        if category_path is not None:
            if category_path == "":
                # Empty string means uncategorized
                uncategorized = True
            else:
                category = self.db.get_category_by_path(category_path)
                if category is None:
                    # Category doesn't exist, return empty list
                    return []
                category_id = category.id

        return self.db.list_transactions(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            account_id=account_id,
            uncategorized=uncategorized,
        )

    def get_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        include_transfers: bool = False,
    ) -> list[dict]:
        """Get category summary.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category_path: Optional category path filter
            include_transfers: If True, include transactions with Transfer category

        Returns:
            List of summary dicts
        """
        category_id = None
        if category_path is not None:
            category = self.db.get_category_by_path(category_path)
            if category is not None:
                category_id = category.id

        return self.db.get_category_summary(
            start_date=start_date, end_date=end_date, category_id=category_id, include_transfers=include_transfers
        )

