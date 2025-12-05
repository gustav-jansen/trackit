"""Abstract database interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import date, datetime
from decimal import Decimal


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
    def get_account(self, account_id: int) -> Optional[dict[str, Any]]:
        """Get account by ID."""
        pass

    @abstractmethod
    def list_accounts(self) -> list[dict[str, Any]]:
        """List all accounts."""
        pass

    # CSV Format operations
    @abstractmethod
    def create_csv_format(self, name: str, account_id: int) -> int:
        """Create a new CSV format. Returns format ID."""
        pass

    @abstractmethod
    def get_csv_format(self, format_id: int) -> Optional[dict[str, Any]]:
        """Get CSV format by ID."""
        pass

    @abstractmethod
    def get_csv_format_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """Get CSV format by name."""
        pass

    @abstractmethod
    def list_csv_formats(self, account_id: Optional[int] = None) -> list[dict[str, Any]]:
        """List CSV formats, optionally filtered by account."""
        pass

    # CSV Column Mapping operations
    @abstractmethod
    def add_column_mapping(
        self, format_id: int, csv_column_name: str, db_field_name: str, is_required: bool = False
    ) -> int:
        """Add a column mapping to a CSV format. Returns mapping ID."""
        pass

    @abstractmethod
    def get_column_mappings(self, format_id: int) -> list[dict[str, Any]]:
        """Get all column mappings for a format."""
        pass

    # Category operations
    @abstractmethod
    def create_category(self, name: str, parent_id: Optional[int] = None) -> int:
        """Create a category. Returns category ID."""
        pass

    @abstractmethod
    def get_category(self, category_id: int) -> Optional[dict[str, Any]]:
        """Get category by ID."""
        pass

    @abstractmethod
    def get_category_by_path(self, path: str) -> Optional[dict[str, Any]]:
        """Get category by path (e.g., 'Food & Dining > Groceries')."""
        pass

    @abstractmethod
    def list_categories(self, parent_id: Optional[int] = None) -> list[dict[str, Any]]:
        """List categories, optionally filtered by parent."""
        pass

    @abstractmethod
    def get_category_tree(self) -> list[dict[str, Any]]:
        """Get full category tree with hierarchy."""
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
    def get_transaction(self, transaction_id: int) -> Optional[dict[str, Any]]:
        """Get transaction by ID."""
        pass

    @abstractmethod
    def transaction_exists(self, account_id: int, unique_id: str) -> bool:
        """Check if a transaction with given unique_id exists for account."""
        pass

    @abstractmethod
    def update_transaction_category(self, transaction_id: int, category_id: Optional[int]) -> None:
        """Update transaction category."""
        pass

    @abstractmethod
    def update_transaction_notes(self, transaction_id: int, notes: Optional[str]) -> None:
        """Update transaction notes."""
        pass

    @abstractmethod
    def list_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
        uncategorized: bool = False,
    ) -> list[dict[str, Any]]:
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
    def get_category_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get summary of expenses by category."""
        pass

