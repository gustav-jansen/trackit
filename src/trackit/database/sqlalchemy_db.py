"""Generic SQLAlchemy database implementation."""

from typing import Optional, Any
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session

from trackit.database.base import Database
from trackit.database.models import (
    Account,
    CSVFormat,
    CSVColumnMapping,
    Category,
    Transaction,
    create_session_factory,
)
from trackit.database.mappers import (
    account_to_domain,
    category_to_domain,
    transaction_to_domain,
    csv_format_to_domain,
    csv_column_mapping_to_domain,
)
from trackit.domain.entities import (
    Account as DomainAccount,
    Category as DomainCategory,
    Transaction as DomainTransaction,
    CSVFormat as DomainCSVFormat,
    CSVColumnMapping as DomainCSVColumnMapping,
)


class SQLAlchemyDatabase(Database):
    """SQLAlchemy-based implementation of Database interface."""

    def __init__(self, database_url: str):
        """Initialize SQLAlchemy database.

        Args:
            database_url: SQLAlchemy database URL (e.g., 'sqlite:///path/to.db',
                'postgresql://user:pass@host/db', etc.)
        """
        self.database_url = database_url
        self.session_factory = create_session_factory(database_url)
        self._session: Optional[Session] = None

    def _get_session(self) -> Session:
        """Get current session, creating one if needed."""
        if self._session is None:
            self._session = self.session_factory()
        return self._session

    def connect(self) -> None:
        """Connect to the database."""
        # Connection is lazy, so this is a no-op
        pass

    def disconnect(self) -> None:
        """Disconnect from the database."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def initialize_schema(self) -> None:
        """Initialize database schema (create tables)."""
        # Schema is created automatically by create_session_factory
        pass

    # Account operations
    def create_account(self, name: str, bank_name: str) -> int:
        """Create a new account. Returns account ID."""
        session = self._get_session()
        account = Account(name=name, bank_name=bank_name)
        session.add(account)
        session.commit()
        return account.id

    def get_account(self, account_id: int) -> Optional[DomainAccount]:
        """Get account by ID."""
        session = self._get_session()
        account = session.query(Account).filter(Account.id == account_id).first()
        if account is None:
            return None
        return account_to_domain(account)

    def list_accounts(self) -> list[DomainAccount]:
        """List all accounts."""
        session = self._get_session()
        accounts = session.query(Account).order_by(Account.name).all()
        return [account_to_domain(acc) for acc in accounts]

    # CSV Format operations
    def create_csv_format(self, name: str, account_id: int) -> int:
        """Create a new CSV format. Returns format ID."""
        session = self._get_session()
        csv_format = CSVFormat(name=name, account_id=account_id)
        session.add(csv_format)
        session.commit()
        return csv_format.id

    def get_csv_format(self, format_id: int) -> Optional[DomainCSVFormat]:
        """Get CSV format by ID."""
        session = self._get_session()
        fmt = session.query(CSVFormat).filter(CSVFormat.id == format_id).first()
        if fmt is None:
            return None
        return csv_format_to_domain(fmt)

    def get_csv_format_by_name(self, name: str) -> Optional[DomainCSVFormat]:
        """Get CSV format by name."""
        session = self._get_session()
        fmt = session.query(CSVFormat).filter(CSVFormat.name == name).first()
        if fmt is None:
            return None
        return csv_format_to_domain(fmt)

    def list_csv_formats(self, account_id: Optional[int] = None) -> list[DomainCSVFormat]:
        """List CSV formats, optionally filtered by account."""
        session = self._get_session()
        query = session.query(CSVFormat)
        if account_id is not None:
            query = query.filter(CSVFormat.account_id == account_id)
        formats = query.order_by(CSVFormat.name).all()
        return [csv_format_to_domain(fmt) for fmt in formats]

    # CSV Column Mapping operations
    def add_column_mapping(
        self, format_id: int, csv_column_name: str, db_field_name: str, is_required: bool = False
    ) -> int:
        """Add a column mapping to a CSV format. Returns mapping ID."""
        session = self._get_session()
        mapping = CSVColumnMapping(
            format_id=format_id,
            csv_column_name=csv_column_name,
            db_field_name=db_field_name,
            is_required=is_required,
        )
        session.add(mapping)
        session.commit()
        return mapping.id

    def get_column_mappings(self, format_id: int) -> list[DomainCSVColumnMapping]:
        """Get all column mappings for a format."""
        session = self._get_session()
        mappings = (
            session.query(CSVColumnMapping)
            .filter(CSVColumnMapping.format_id == format_id)
            .order_by(CSVColumnMapping.db_field_name)
            .all()
        )
        return [csv_column_mapping_to_domain(m) for m in mappings]

    # Category operations
    def create_category(self, name: str, parent_id: Optional[int] = None) -> int:
        """Create a category. Returns category ID."""
        session = self._get_session()
        category = Category(name=name, parent_id=parent_id)
        session.add(category)
        session.commit()
        return category.id

    def get_category(self, category_id: int) -> Optional[DomainCategory]:
        """Get category by ID."""
        session = self._get_session()
        cat = session.query(Category).filter(Category.id == category_id).first()
        if cat is None:
            return None
        return category_to_domain(cat)

    def get_category_by_path(self, path: str) -> Optional[DomainCategory]:
        """Get category by path (e.g., 'Food & Dining > Groceries')."""
        parts = [p.strip() for p in path.split(">")]
        session = self._get_session()

        current_parent_id = None
        for part in parts:
            query = session.query(Category).filter(Category.name == part)
            if current_parent_id is None:
                query = query.filter(Category.parent_id.is_(None))
            else:
                query = query.filter(Category.parent_id == current_parent_id)

            cat = query.first()
            if cat is None:
                return None
            current_parent_id = cat.id

        if current_parent_id is None:
            return None

        cat = session.query(Category).filter(Category.id == current_parent_id).first()
        if cat is None:
            return None
        return category_to_domain(cat)

    def list_categories(self, parent_id: Optional[int] = None) -> list[DomainCategory]:
        """List categories, optionally filtered by parent."""
        session = self._get_session()
        query = session.query(Category)
        if parent_id is None:
            query = query.filter(Category.parent_id.is_(None))
        else:
            query = query.filter(Category.parent_id == parent_id)
        categories = query.order_by(Category.name).all()
        return [category_to_domain(cat) for cat in categories]

    def get_category_tree(self) -> list[dict[str, Any]]:
        """Get full category tree with hierarchy."""
        session = self._get_session()
        all_categories = session.query(Category).order_by(Category.name).all()

        def build_tree(categories: list[Category], parent_id: Optional[int] = None) -> list[dict[str, Any]]:
            result = []
            for cat in categories:
                if cat.parent_id == parent_id:
                    children = build_tree(categories, cat.id)
                    cat_domain = category_to_domain(cat)
                    result.append(
                        {
                            "id": cat_domain.id,
                            "name": cat_domain.name,
                            "parent_id": cat_domain.parent_id,
                            "created_at": cat_domain.created_at,
                            "children": children,
                        }
                    )
            return result

        return build_tree(all_categories)

    # Transaction operations
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
        session = self._get_session()
        transaction = Transaction(
            unique_id=unique_id,
            account_id=account_id,
            date=date,
            amount=amount,
            description=description,
            reference_number=reference_number,
            category_id=category_id,
            notes=notes,
        )
        session.add(transaction)
        session.commit()
        return transaction.id

    def get_transaction(self, transaction_id: int) -> Optional[DomainTransaction]:
        """Get transaction by ID."""
        session = self._get_session()
        txn = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if txn is None:
            return None
        return transaction_to_domain(txn)

    def transaction_exists(self, account_id: int, unique_id: str) -> bool:
        """Check if a transaction with given unique_id exists for account."""
        session = self._get_session()
        count = (
            session.query(Transaction)
            .filter(Transaction.account_id == account_id, Transaction.unique_id == unique_id)
            .count()
        )
        return count > 0

    def update_transaction_category(self, transaction_id: int, category_id: Optional[int]) -> None:
        """Update transaction category."""
        session = self._get_session()
        transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        transaction.category_id = category_id
        session.commit()

    def update_transaction_notes(self, transaction_id: int, notes: Optional[str]) -> None:
        """Update transaction notes."""
        session = self._get_session()
        transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        transaction.notes = notes
        session.commit()

    def list_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
        uncategorized: bool = False,
    ) -> list[DomainTransaction]:
        """List transactions with optional filters."""
        session = self._get_session()
        query = session.query(Transaction)

        if start_date is not None:
            query = query.filter(Transaction.date >= start_date)
        if end_date is not None:
            query = query.filter(Transaction.date <= end_date)
        if uncategorized:
            query = query.filter(Transaction.category_id.is_(None))
        elif category_id is not None:
            query = query.filter(Transaction.category_id == category_id)
        if account_id is not None:
            query = query.filter(Transaction.account_id == account_id)

        transactions = query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
        return [transaction_to_domain(txn) for txn in transactions]

    def get_category_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Get summary of expenses by category."""
        session = self._get_session()
        from sqlalchemy import func, case

        # Build base query
        query = session.query(
            Transaction.category_id,
            Category.name.label("category_name"),
            func.sum(
                case((Transaction.amount < 0, Transaction.amount), else_=0)
            ).label("expenses"),
            func.sum(
                case((Transaction.amount > 0, Transaction.amount), else_=0)
            ).label("income"),
            func.count(Transaction.id).label("count"),
        ).join(Category, Transaction.category_id == Category.id, isouter=True)

        # Apply filters
        if start_date is not None:
            query = query.filter(Transaction.date >= start_date)
        if end_date is not None:
            query = query.filter(Transaction.date <= end_date)
        if category_id is not None:
            # Include the category and all its descendants
            # For simplicity, we'll filter by exact category_id
            # A more sophisticated implementation would traverse the tree
            query = query.filter(Transaction.category_id == category_id)

        query = query.group_by(Transaction.category_id, Category.name)
        results = query.all()

        return [
            {
                "category_id": r.category_id,
                "category_name": r.category_name or "Uncategorized",
                "expenses": float(r.expenses or 0),
                "income": float(r.income or 0),
                "count": r.count,
            }
            for r in results
        ]

