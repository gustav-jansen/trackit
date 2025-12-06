"""Tests for database mappers."""

import pytest
from datetime import datetime, date, UTC
from decimal import Decimal

from trackit.database.models import (
    Account as ORMAccount,
    Category as ORMCategory,
    Transaction as ORMTransaction,
    CSVFormat as ORMCSVFormat,
    CSVColumnMapping as ORMCSVColumnMapping,
)
from trackit.database.mappers import (
    account_to_domain,
    category_to_domain,
    transaction_to_domain,
    csv_format_to_domain,
    csv_column_mapping_to_domain,
)
from trackit.domain.entities import (
    Account,
    Category,
    Transaction,
    CSVFormat,
    CSVColumnMapping,
)


class TestAccountMapper:
    """Tests for Account mapper."""

    def test_account_to_domain(self):
        """Test converting ORM Account to domain Account."""
        orm_account = ORMAccount(
            id=1,
            name="Test Account",
            bank_name="Test Bank",
            created_at=datetime.now(UTC),
        )
        domain_account = account_to_domain(orm_account)

        assert isinstance(domain_account, Account)
        assert domain_account.id == 1
        assert domain_account.name == "Test Account"
        assert domain_account.bank_name == "Test Bank"
        assert domain_account.created_at == orm_account.created_at


class TestCategoryMapper:
    """Tests for Category mapper."""

    def test_category_to_domain(self):
        """Test converting ORM Category to domain Category."""
        orm_category = ORMCategory(
            id=1,
            name="Food & Dining",
            parent_id=None,
            created_at=datetime.now(UTC),
        )
        domain_category = category_to_domain(orm_category)

        assert isinstance(domain_category, Category)
        assert domain_category.id == 1
        assert domain_category.name == "Food & Dining"
        assert domain_category.parent_id is None
        assert domain_category.created_at == orm_category.created_at

    def test_category_to_domain_with_parent(self):
        """Test converting ORM Category with parent to domain Category."""
        orm_category = ORMCategory(
            id=2,
            name="Groceries",
            parent_id=1,
            created_at=datetime.now(UTC),
        )
        domain_category = category_to_domain(orm_category)

        assert domain_category.parent_id == 1


class TestTransactionMapper:
    """Tests for Transaction mapper."""

    def test_transaction_to_domain(self):
        """Test converting ORM Transaction to domain Transaction."""
        orm_transaction = ORMTransaction(
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
        domain_transaction = transaction_to_domain(orm_transaction)

        assert isinstance(domain_transaction, Transaction)
        assert domain_transaction.id == 1
        assert domain_transaction.unique_id == "txn-123"
        assert domain_transaction.account_id == 1
        assert domain_transaction.date == date(2024, 1, 15)
        assert domain_transaction.amount == Decimal("-50.00")
        assert domain_transaction.description == "Grocery store"
        assert domain_transaction.reference_number == "REF123"
        assert domain_transaction.category_id == 1
        assert domain_transaction.notes == "Test notes"
        assert domain_transaction.imported_at == orm_transaction.imported_at

    def test_transaction_to_domain_with_none_fields(self):
        """Test converting ORM Transaction with None optional fields."""
        orm_transaction = ORMTransaction(
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
        domain_transaction = transaction_to_domain(orm_transaction)

        assert domain_transaction.description is None
        assert domain_transaction.reference_number is None
        assert domain_transaction.category_id is None
        assert domain_transaction.notes is None


class TestCSVFormatMapper:
    """Tests for CSVFormat mapper."""

    def test_csv_format_to_domain(self):
        """Test converting ORM CSVFormat to domain CSVFormat."""
        orm_format = ORMCSVFormat(
            id=1,
            name="Test Format",
            account_id=1,
            created_at=datetime.now(UTC),
        )
        domain_format = csv_format_to_domain(orm_format)

        assert isinstance(domain_format, CSVFormat)
        assert domain_format.id == 1
        assert domain_format.name == "Test Format"
        assert domain_format.account_id == 1
        assert domain_format.created_at == orm_format.created_at


class TestCSVColumnMappingMapper:
    """Tests for CSVColumnMapping mapper."""

    def test_csv_column_mapping_to_domain(self):
        """Test converting ORM CSVColumnMapping to domain CSVColumnMapping."""
        orm_mapping = ORMCSVColumnMapping(
            id=1,
            format_id=1,
            csv_column_name="Transaction ID",
            db_field_name="unique_id",
            is_required=True,
        )
        domain_mapping = csv_column_mapping_to_domain(orm_mapping)

        assert isinstance(domain_mapping, CSVColumnMapping)
        assert domain_mapping.id == 1
        assert domain_mapping.format_id == 1
        assert domain_mapping.csv_column_name == "Transaction ID"
        assert domain_mapping.db_field_name == "unique_id"
        assert domain_mapping.is_required is True

    def test_csv_column_mapping_to_domain_not_required(self):
        """Test converting ORM CSVColumnMapping with is_required=False."""
        orm_mapping = ORMCSVColumnMapping(
            id=1,
            format_id=1,
            csv_column_name="Description",
            db_field_name="description",
            is_required=False,
        )
        domain_mapping = csv_column_mapping_to_domain(orm_mapping)

        assert domain_mapping.is_required is False
