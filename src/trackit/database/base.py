"""Abstract database interface."""

from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import date
from decimal import Decimal

# Import entities directly to avoid circular import through domain/__init__.py
from trackit.domain.entities import (
    Account,
    Category,
    Transaction,
    CSVFormat,
    CSVColumnMapping,
)


class Database(ABC):
    """Abstract database interface for trackit."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the database."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the database."""
        pass

    @abstractmethod
    def initialize_schema(self) -> None:
        """Initialize database schema (create tables)."""
        pass

    # Account operations
    @abstractmethod
    def create_account(self, name: str, bank_name: str) -> int:
        """Create a new account. Returns account ID."""
        pass

    @abstractmethod
    def get_account(self, account_id: int) -> Optional[Account]:
        """Get account by ID."""
        pass

    @abstractmethod
    def list_accounts(self) -> list[Account]:
        """List all accounts."""
        pass

    @abstractmethod
    def update_account_name(
        self, account_id: int, name: str, bank_name: Optional[str] = None
    ) -> None:
        """Update account name and optionally bank name.

        Args:
            account_id: Account ID to update
            name: New account name
            bank_name: Optional new bank name (if None, bank_name is not updated)

        Raises:
            ValueError: If account not found or name already exists
        """
        pass

    @abstractmethod
    def delete_account(self, account_id: int) -> None:
        """Delete an account.

        Args:
            account_id: Account ID to delete

        Raises:
            ValueError: If account not found or has associated transactions/formats
        """
        pass

    @abstractmethod
    def get_account_transaction_count(self, account_id: int) -> int:
        """Get count of transactions associated with an account.

        Args:
            account_id: Account ID

        Returns:
            Number of transactions
        """
        pass

    @abstractmethod
    def get_account_format_count(self, account_id: int) -> int:
        """Get count of CSV formats associated with an account.

        Args:
            account_id: Account ID

        Returns:
            Number of CSV formats
        """
        pass

    # CSV Format operations
    @abstractmethod
    def create_csv_format(
        self,
        name: str,
        account_id: int,
        is_debit_credit_format: bool = False,
        negate_debit: bool = False,
        negate_credit: bool = False,
    ) -> int:
        """Create a new CSV format. Returns format ID.

        Args:
            name: Format name
            account_id: Associated account ID
            is_debit_credit_format: Whether this format uses separate debit/credit columns
            negate_debit: Whether to negate debit values during import
            negate_credit: Whether to negate credit values during import
        """
        pass

    @abstractmethod
    def get_csv_format(self, format_id: int) -> Optional[CSVFormat]:
        """Get CSV format by ID."""
        pass

    @abstractmethod
    def get_csv_format_by_name(self, name: str) -> Optional[CSVFormat]:
        """Get CSV format by name."""
        pass

    @abstractmethod
    def list_csv_formats(self, account_id: Optional[int] = None) -> list[CSVFormat]:
        """List CSV formats, optionally filtered by account."""
        pass

    # CSV Column Mapping operations
    @abstractmethod
    def add_column_mapping(
        self,
        format_id: int,
        csv_column_name: str,
        db_field_name: str,
        is_required: bool = False,
    ) -> int:
        """Add a column mapping to a CSV format. Returns mapping ID."""
        pass

    @abstractmethod
    def get_column_mappings(self, format_id: int) -> list[CSVColumnMapping]:
        """Get all column mappings for a format."""
        pass

    @abstractmethod
    def update_csv_format(
        self,
        format_id: int,
        name: Optional[str] = None,
        account_id: Optional[int] = None,
        is_debit_credit_format: Optional[bool] = None,
        negate_debit: Optional[bool] = None,
        negate_credit: Optional[bool] = None,
    ) -> None:
        """Update CSV format fields.

        Args:
            format_id: Format ID to update
            name: Optional new format name
            account_id: Optional new account ID
            is_debit_credit_format: Optional flag to enable/disable debit/credit format
            negate_debit: Optional flag to enable/disable debit negation
            negate_credit: Optional flag to enable/disable credit negation

        Raises:
            ValueError: If format not found or name already exists
        """
        pass

    @abstractmethod
    def delete_csv_format(self, format_id: int) -> None:
        """Delete a CSV format.

        Args:
            format_id: Format ID to delete

        Raises:
            ValueError: If format not found
        """
        pass

    # Category operations
    @abstractmethod
    def create_category(
        self,
        name: str,
        parent_id: Optional[int] = None,
        category_type: Optional[int] = None,
    ) -> int:
        """Create a category. Returns category ID.

        Args:
            name: Category name
            parent_id: Optional parent category ID
            category_type: Optional category type (0=Expense, 1=Income, 2=Transfer). Defaults to 0 (Expense).
        """
        pass

    @abstractmethod
    def get_category(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        pass

    @abstractmethod
    def get_category_by_path(self, path: str) -> Optional[Category]:
        """Get category by path (e.g., 'Food & Dining > Groceries')."""
        pass

    @abstractmethod
    def list_categories(self, parent_id: Optional[int] = None) -> list[Category]:
        """List categories, optionally filtered by parent."""
        pass

    @abstractmethod
    def get_category_tree(self) -> list[dict[str, Any]]:
        """Get full category tree with hierarchy.

        Returns a list of dictionaries with category data and nested 'children' lists.
        This structure is used for hierarchical display and is kept as dict for convenience.
        """
        pass

    # Transaction operations
    @abstractmethod
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
        """Create a transaction. Returns transaction ID."""
        pass

    @abstractmethod
    def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        """Get transaction by ID."""
        pass

    @abstractmethod
    def transaction_exists(self, account_id: int, unique_id: str) -> bool:
        """Check if a transaction with given unique_id exists for account."""
        pass

    @abstractmethod
    def update_transaction_category(
        self, transaction_id: int, category_id: Optional[int]
    ) -> None:
        """Update transaction category."""
        pass

    @abstractmethod
    def update_transaction_notes(
        self, transaction_id: int, notes: Optional[str]
    ) -> None:
        """Update transaction notes."""
        pass

    @abstractmethod
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
        update_category: bool = False,
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
            update_category: If True, update category_id even if it's None (to clear it)

        Raises:
            ValueError: If transaction not found
        """
        pass

    @abstractmethod
    def delete_transaction(self, transaction_id: int) -> None:
        """Delete a transaction.

        Args:
            transaction_id: Transaction ID to delete

        Raises:
            ValueError: If transaction not found
        """
        pass

    @abstractmethod
    def list_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
        uncategorized: bool = False,
    ) -> list[Transaction]:
        """List transactions with optional filters.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category_id: Optional category ID filter
            account_id: Optional account ID filter
            uncategorized: If True, only return transactions without a category
        """
        pass

    @abstractmethod
    def get_summary_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        include_transfers: bool = False,
    ) -> list[Transaction]:
        """Get transactions for summary views.

        Includes descendant categories when category_id is provided.
        """
        pass

    @abstractmethod
    def get_category_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        include_transfers: bool = False,
    ) -> list[dict[str, Any]]:
        """Get summary of expenses by category.

        Returns a list of dictionaries with summary data (category_id, category_name,
        expenses, income, count). This structure is kept as dict for aggregation results.
        """
        pass
