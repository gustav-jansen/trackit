"""Tests for domain entities."""

import pytest
from datetime import datetime, date, UTC
from decimal import Decimal

from trackit.domain.entities import Account, Category, Transaction, CSVFormat, CSVColumnMapping


class TestAccount:
    """Tests for Account entity."""

    def test_create_account(self):
        """Test creating an Account entity."""
        account = Account(
            id=1,
            name="Test Account",
            bank_name="Test Bank",
            created_at=datetime.now(UTC),
        )
        assert account.id == 1
        assert account.name == "Test Account"
        assert account.bank_name == "Test Bank"
        assert isinstance(account.created_at, datetime)

    def test_account_immutability(self):
        """Test that Account entities are immutable."""
        account = Account(
            id=1,
            name="Test Account",
            bank_name="Test Bank",
            created_at=datetime.now(UTC),
        )
        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            account.name = "New Name"

    def test_account_equality(self):
        """Test Account entity equality."""
        created_at = datetime.now(UTC)
        account1 = Account(id=1, name="Test", bank_name="Bank", created_at=created_at)
        account2 = Account(id=1, name="Test", bank_name="Bank", created_at=created_at)
        account3 = Account(id=2, name="Test", bank_name="Bank", created_at=created_at)

        assert account1 == account2
        assert account1 != account3


class TestCategory:
    """Tests for Category entity."""

    def test_create_category(self):
        """Test creating a Category entity."""
        category = Category(
            id=1,
            name="Food & Dining",
            parent_id=None,
            created_at=datetime.now(UTC),
        )
        assert category.id == 1
        assert category.name == "Food & Dining"
        assert category.parent_id is None
        assert isinstance(category.created_at, datetime)

    def test_create_category_with_parent(self):
        """Test creating a Category with a parent."""
        category = Category(
            id=2,
            name="Groceries",
            parent_id=1,
            created_at=datetime.now(UTC),
        )
        assert category.parent_id == 1

    def test_category_immutability(self):
        """Test that Category entities are immutable."""
        category = Category(
            id=1,
            name="Test",
            parent_id=None,
            created_at=datetime.now(UTC),
        )
        with pytest.raises(Exception):
            category.name = "New Name"


class TestTransaction:
    """Tests for Transaction entity."""

    def test_create_transaction(self):
        """Test creating a Transaction entity."""
        transaction = Transaction(
            id=1,
            unique_id="txn-123",
            account_id=1,
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            description="Grocery store",
            reference_number="REF123",
            category_id=1,
            notes="Test notes",
            imported_at=datetime.now(UTC),
        )
        assert transaction.id == 1
        assert transaction.unique_id == "txn-123"
        assert transaction.account_id == 1
        assert transaction.date == date(2024, 1, 15)
        assert transaction.amount == Decimal("-50.00")
        assert transaction.description == "Grocery store"
        assert transaction.reference_number == "REF123"
        assert transaction.category_id == 1
        assert transaction.notes == "Test notes"
        assert isinstance(transaction.imported_at, datetime)

    def test_create_transaction_with_optional_fields_none(self):
        """Test creating a Transaction with optional fields as None."""
        transaction = Transaction(
            id=1,
            unique_id="txn-123",
            account_id=1,
            date=date(2024, 1, 15),
            amount=Decimal("100.00"),
            description=None,
            reference_number=None,
            category_id=None,
            notes=None,
            imported_at=datetime.now(UTC),
        )
        assert transaction.description is None
        assert transaction.reference_number is None
        assert transaction.category_id is None
        assert transaction.notes is None

    def test_transaction_immutability(self):
        """Test that Transaction entities are immutable."""
        transaction = Transaction(
            id=1,
            unique_id="txn-123",
            account_id=1,
            date=date(2024, 1, 15),
            amount=Decimal("100.00"),
            description=None,
            reference_number=None,
            category_id=None,
            notes=None,
            imported_at=datetime.now(UTC),
        )
        with pytest.raises(Exception):
            transaction.amount = Decimal("200.00")


class TestCSVFormat:
    """Tests for CSVFormat entity."""

    def test_create_csv_format(self):
        """Test creating a CSVFormat entity."""
        csv_format = CSVFormat(
            id=1,
            name="Test Format",
            account_id=1,
            created_at=datetime.now(UTC),
        )
        assert csv_format.id == 1
        assert csv_format.name == "Test Format"
        assert csv_format.account_id == 1
        assert isinstance(csv_format.created_at, datetime)


class TestCSVColumnMapping:
    """Tests for CSVColumnMapping entity."""

    def test_create_csv_column_mapping(self):
        """Test creating a CSVColumnMapping entity."""
        mapping = CSVColumnMapping(
            id=1,
            format_id=1,
            csv_column_name="Transaction ID",
            db_field_name="unique_id",
            is_required=True,
        )
        assert mapping.id == 1
        assert mapping.format_id == 1
        assert mapping.csv_column_name == "Transaction ID"
        assert mapping.db_field_name == "unique_id"
        assert mapping.is_required is True
