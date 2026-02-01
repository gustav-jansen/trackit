"""Generic SQLAlchemy database implementation."""

from typing import Optional
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import or_

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
    category_tree_to_domain,
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
    CategoryTreeNode as DomainCategoryTreeNode,
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

    def update_account_name(
        self, account_id: int, name: str, bank_name: Optional[str] = None
    ) -> None:
        """Update account name and optionally bank name."""
        session = self._get_session()
        account = session.query(Account).filter(Account.id == account_id).first()
        if account is None:
            raise ValueError(f"Account {account_id} not found")

        # Check for duplicate name (excluding current account)
        existing = (
            session.query(Account)
            .filter(Account.name == name, Account.id != account_id)
            .first()
        )
        if existing is not None:
            raise ValueError(f"Account with name '{name}' already exists")

        account.name = name
        if bank_name is not None:
            account.bank_name = bank_name
        session.commit()

    def delete_account(self, account_id: int) -> None:
        """Delete an account."""
        session = self._get_session()
        account = session.query(Account).filter(Account.id == account_id).first()
        if account is None:
            raise ValueError(f"Account {account_id} not found")

        # Check for associated transactions
        transaction_count = (
            session.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .count()
        )
        # Check for associated formats
        format_count = (
            session.query(CSVFormat).filter(CSVFormat.account_id == account_id).count()
        )

        if transaction_count > 0 or format_count > 0:
            parts = []
            if transaction_count > 0:
                parts.append(
                    f"{transaction_count} transaction{'s' if transaction_count != 1 else ''}"
                )
            if format_count > 0:
                parts.append(
                    f"{format_count} CSV format{'s' if format_count != 1 else ''}"
                )
            raise ValueError(
                f"Cannot delete account {account_id}: it has {', '.join(parts)}. "
                f"Please reassign or delete them first."
            )

        session.delete(account)
        session.commit()

    def get_account_transaction_count(self, account_id: int) -> int:
        """Get count of transactions associated with an account."""
        session = self._get_session()
        return (
            session.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .count()
        )

    def get_account_format_count(self, account_id: int) -> int:
        """Get count of CSV formats associated with an account."""
        session = self._get_session()
        return (
            session.query(CSVFormat).filter(CSVFormat.account_id == account_id).count()
        )

    # CSV Format operations
    def create_csv_format(
        self,
        name: str,
        account_id: int,
        is_debit_credit_format: bool = False,
        negate_debit: bool = False,
        negate_credit: bool = False,
    ) -> int:
        """Create a new CSV format. Returns format ID."""
        session = self._get_session()
        csv_format = CSVFormat(
            name=name,
            account_id=account_id,
            is_debit_credit_format=is_debit_credit_format,
            negate_debit=negate_debit,
            negate_credit=negate_credit,
        )
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

    def list_csv_formats(
        self, account_id: Optional[int] = None
    ) -> list[DomainCSVFormat]:
        """List CSV formats, optionally filtered by account."""
        session = self._get_session()
        query = session.query(CSVFormat)
        if account_id is not None:
            query = query.filter(CSVFormat.account_id == account_id)
        formats = query.order_by(CSVFormat.name).all()
        return [csv_format_to_domain(fmt) for fmt in formats]

    # CSV Column Mapping operations
    def add_column_mapping(
        self,
        format_id: int,
        csv_column_name: str,
        db_field_name: str,
        is_required: bool = False,
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

    def update_csv_format(
        self,
        format_id: int,
        name: Optional[str] = None,
        account_id: Optional[int] = None,
        is_debit_credit_format: Optional[bool] = None,
        negate_debit: Optional[bool] = None,
        negate_credit: Optional[bool] = None,
    ) -> None:
        """Update CSV format fields."""
        session = self._get_session()
        fmt = session.query(CSVFormat).filter(CSVFormat.id == format_id).first()
        if fmt is None:
            raise ValueError(f"CSV format {format_id} not found")

        if name is not None:
            # Check for duplicate name (excluding current format)
            existing = (
                session.query(CSVFormat)
                .filter(CSVFormat.name == name, CSVFormat.id != format_id)
                .first()
            )
            if existing is not None:
                raise ValueError(f"CSV format with name '{name}' already exists")
            fmt.name = name

        if account_id is not None:
            fmt.account_id = account_id

        if is_debit_credit_format is not None:
            fmt.is_debit_credit_format = is_debit_credit_format

        if negate_debit is not None:
            fmt.negate_debit = negate_debit

        if negate_credit is not None:
            fmt.negate_credit = negate_credit

        session.commit()

    def delete_csv_format(self, format_id: int) -> None:
        """Delete a CSV format."""
        session = self._get_session()
        fmt = session.query(CSVFormat).filter(CSVFormat.id == format_id).first()
        if fmt is None:
            raise ValueError(f"CSV format {format_id} not found")
        session.delete(fmt)
        session.commit()

    # Category operations
    def create_category(
        self,
        name: str,
        parent_id: Optional[int] = None,
        category_type: Optional[int] = None,
    ) -> int:
        """Create a category. Returns category ID."""
        session = self._get_session()
        # Default to Expense (0) if not specified
        cat_type = category_type if category_type is not None else 0
        category = Category(name=name, parent_id=parent_id, category_type=cat_type)
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

    def get_category_tree(self) -> list[DomainCategoryTreeNode]:
        """Get full category tree with hierarchy."""
        session = self._get_session()
        all_categories = session.query(Category).order_by(Category.name).all()
        return category_tree_to_domain(all_categories)

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
        txn = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if txn is None:
            return None
        return transaction_to_domain(txn)

    def transaction_exists(self, account_id: int, unique_id: str) -> bool:
        """Check if a transaction with given unique_id exists for account."""
        session = self._get_session()
        count = (
            session.query(Transaction)
            .filter(
                Transaction.account_id == account_id, Transaction.unique_id == unique_id
            )
            .count()
        )
        return count > 0

    def update_transaction_category(
        self, transaction_id: int, category_id: Optional[int]
    ) -> None:
        """Update transaction category."""
        session = self._get_session()
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        transaction.category_id = category_id
        session.commit()

    def update_transaction_notes(
        self, transaction_id: int, notes: Optional[str]
    ) -> None:
        """Update transaction notes."""
        session = self._get_session()
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        transaction.notes = notes
        session.commit()

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
            update_category: If True, update category_id even if it's None (to clear it)
        """
        session = self._get_session()
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        if account_id is not None:
            transaction.account_id = account_id
        if date is not None:
            transaction.date = date
        if amount is not None:
            transaction.amount = amount
        if description is not None:
            transaction.description = description
        if reference_number is not None:
            transaction.reference_number = reference_number
        if update_category:
            transaction.category_id = category_id
        elif category_id is not None:
            transaction.category_id = category_id
        if notes is not None:
            transaction.notes = notes

        session.commit()

    def delete_transaction(self, transaction_id: int) -> None:
        """Delete a transaction."""
        session = self._get_session()
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if transaction is None:
            raise ValueError(f"Transaction {transaction_id} not found")
        session.delete(transaction)
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

        transactions = query.order_by(
            Transaction.date.desc(), Transaction.id.desc()
        ).all()
        return [transaction_to_domain(txn) for txn in transactions]

    def get_summary_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        include_transfers: bool = False,
    ) -> list[DomainTransaction]:
        """Get transactions for summary views."""
        session = self._get_session()
        query = session.query(Transaction)

        if start_date is not None:
            query = query.filter(Transaction.date >= start_date)
        if end_date is not None:
            query = query.filter(Transaction.date <= end_date)
        if category_id is not None:
            descendant_ids = self._get_all_descendant_ids(category_id)
            query = query.filter(Transaction.category_id.in_(descendant_ids))
        if not include_transfers:
            transfer_categories = (
                session.query(Category).filter(Category.category_type == 2).all()
            )
            transfer_ids = set()
            for cat in transfer_categories:
                transfer_ids.update(self._get_all_descendant_ids(cat.id))

            if transfer_ids:
                query = query.filter(
                    or_(
                        Transaction.category_id.is_(None),
                        ~Transaction.category_id.in_(transfer_ids),
                    )
                )

        transactions = query.order_by(
            Transaction.date.desc(), Transaction.id.desc()
        ).all()
        return [transaction_to_domain(txn) for txn in transactions]

    def _get_all_descendant_ids(self, category_id: int) -> set[int]:
        """Get all descendant category IDs (including the category itself).

        Args:
            category_id: Category ID to get descendants for

        Returns:
            Set of category IDs including the category and all its descendants
        """
        session = self._get_session()
        result = {category_id}

        def collect_children(parent_id: int):
            children = (
                session.query(Category).filter(Category.parent_id == parent_id).all()
            )
            for child in children:
                result.add(child.id)
                collect_children(child.id)

        collect_children(category_id)
        return result
