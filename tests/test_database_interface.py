"""Tests for Database interface returning domain models."""

import pytest
from datetime import date, datetime, UTC
from decimal import Decimal

from trackit.database.factories import create_sqlite_database
from trackit.domain import entities


class TestDatabaseInterface:
    """Tests to verify Database interface returns domain models."""

    def test_get_account_returns_domain_model(self, temp_db):
        """Test that get_account returns a domain Account entity."""
        # Create an account
        account_id = temp_db.create_account(name="Test Account", bank_name="Test Bank")

        # Get the account
        account = temp_db.get_account(account_id)

        # Verify it's a domain model
        assert isinstance(account, entities.Account)
        assert account.id == account_id
        assert account.name == "Test Account"
        assert account.bank_name == "Test Bank"
        assert isinstance(account.created_at, datetime)

    def test_list_accounts_returns_domain_models(self, temp_db):
        """Test that list_accounts returns domain Account entities."""
        # Create multiple accounts
        temp_db.create_account(name="Account 1", bank_name="Bank 1")
        temp_db.create_account(name="Account 2", bank_name="Bank 2")

        # List accounts
        accounts = temp_db.list_accounts()

        # Verify they are domain models
        assert len(accounts) == 2
        for account in accounts:
            assert isinstance(account, entities.Account)
            assert isinstance(account.id, int)
            assert isinstance(account.name, str)
            assert isinstance(account.bank_name, str)

    def test_get_category_returns_domain_model(self, temp_db):
        """Test that get_category returns a domain Category entity."""
        # Create a category
        category_id = temp_db.create_category(name="Food & Dining", parent_id=None)

        # Get the category
        category = temp_db.get_category(category_id)

        # Verify it's a domain model
        assert isinstance(category, entities.Category)
        assert category.id == category_id
        assert category.name == "Food & Dining"
        assert category.parent_id is None

    def test_list_categories_returns_domain_models(self, temp_db):
        """Test that list_categories returns domain Category entities."""
        # Create categories
        temp_db.create_category(name="Category 1", parent_id=None)
        temp_db.create_category(name="Category 2", parent_id=None)

        # List categories
        categories = temp_db.list_categories(parent_id=None)

        # Verify they are domain models
        assert len(categories) >= 2
        for category in categories:
            assert isinstance(category, entities.Category)

    def test_get_transaction_returns_domain_model(self, temp_db, sample_account):
        """Test that get_transaction returns a domain Transaction entity."""
        # Create a transaction
        txn_id = temp_db.create_transaction(
            unique_id="TXN001",
            account_id=sample_account.id,
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            description="Test transaction",
        )

        # Get the transaction
        transaction = temp_db.get_transaction(txn_id)

        # Verify it's a domain model
        assert isinstance(transaction, entities.Transaction)
        assert transaction.id == txn_id
        assert transaction.unique_id == "TXN001"
        assert transaction.account_id == sample_account.id
        assert transaction.date == date(2024, 1, 15)
        assert transaction.amount == Decimal("-50.00")
        assert transaction.description == "Test transaction"
        assert isinstance(transaction.imported_at, datetime)

    def test_list_transactions_returns_domain_models(self, temp_db, sample_account):
        """Test that list_transactions returns domain Transaction entities."""
        # Create transactions
        temp_db.create_transaction(
            unique_id="TXN001",
            account_id=sample_account.id,
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
        )
        temp_db.create_transaction(
            unique_id="TXN002",
            account_id=sample_account.id,
            date=date(2024, 1, 16),
            amount=Decimal("100.00"),
        )

        # List transactions
        transactions = temp_db.list_transactions()

        # Verify they are domain models
        assert len(transactions) >= 2
        for transaction in transactions:
            assert isinstance(transaction, entities.Transaction)
            assert isinstance(transaction.id, int)
            assert isinstance(transaction.unique_id, str)
            assert isinstance(transaction.amount, Decimal)

    def test_get_csv_format_returns_domain_model(self, temp_db, sample_account):
        """Test that get_csv_format returns a domain CSVFormat entity."""
        # Create a CSV format
        format_id = temp_db.create_csv_format(
            name="Test Format", account_id=sample_account.id
        )

        # Get the format
        csv_format = temp_db.get_csv_format(format_id)

        # Verify it's a domain model
        assert isinstance(csv_format, entities.CSVFormat)
        assert csv_format.id == format_id
        assert csv_format.name == "Test Format"
        assert csv_format.account_id == sample_account.id

    def test_get_column_mappings_returns_domain_models(self, temp_db, sample_account):
        """Test that get_column_mappings returns domain CSVColumnMapping entities."""
        # Create a CSV format and mapping
        format_id = temp_db.create_csv_format(
            name="Test Format", account_id=sample_account.id
        )
        mapping_id = temp_db.add_column_mapping(
            format_id=format_id,
            csv_column_name="Transaction ID",
            db_field_name="unique_id",
            is_required=True,
        )

        # Get mappings
        mappings = temp_db.get_column_mappings(format_id)

        # Verify they are domain models
        assert len(mappings) == 1
        mapping = mappings[0]
        assert isinstance(mapping, entities.CSVColumnMapping)
        assert mapping.id == mapping_id
        assert mapping.format_id == format_id
        assert mapping.csv_column_name == "Transaction ID"
        assert mapping.db_field_name == "unique_id"
        assert mapping.is_required is True

    def test_get_category_by_path_returns_domain_model(self, temp_db):
        """Test that get_category_by_path returns a domain Category entity."""
        # Create categories with hierarchy
        parent_id = temp_db.create_category(name="Food & Dining", parent_id=None)
        child_id = temp_db.create_category(name="Groceries", parent_id=parent_id)

        # Get by path
        category = temp_db.get_category_by_path("Food & Dining > Groceries")

        # Verify it's a domain model
        assert isinstance(category, entities.Category)
        assert category.id == child_id
        assert category.name == "Groceries"
        assert category.parent_id == parent_id

    def test_get_summary_transactions_returns_raw_results(
        self, temp_db, sample_account
    ):
        """Test summary transactions are filtered by exact category only."""
        parent_id = temp_db.create_category(name="Food & Dining", parent_id=None)
        child_id = temp_db.create_category(name="Groceries", parent_id=parent_id)
        transfer_id = temp_db.create_category(
            name="Transfer", parent_id=None, category_type=2
        )

        temp_db.create_transaction(
            unique_id="TXN001",
            account_id=sample_account.id,
            date=date(2024, 1, 15),
            amount=Decimal("-50.00"),
            description="Parent",
            category_id=parent_id,
        )
        temp_db.create_transaction(
            unique_id="TXN002",
            account_id=sample_account.id,
            date=date(2024, 1, 16),
            amount=Decimal("-25.00"),
            description="Child",
            category_id=child_id,
        )
        temp_db.create_transaction(
            unique_id="TXN003",
            account_id=sample_account.id,
            date=date(2024, 1, 17),
            amount=Decimal("-10.00"),
            description="Transfer",
            category_id=transfer_id,
        )

        parent_only = temp_db.get_summary_transactions(category_id=parent_id)
        parent_ids = {txn.category_id for txn in parent_only}

        assert parent_ids == {parent_id}

        all_txns = temp_db.get_summary_transactions(include_transfers=False)
        all_category_ids = {txn.category_id for txn in all_txns}

        assert parent_id in all_category_ids
        assert child_id in all_category_ids
        assert transfer_id in all_category_ids
