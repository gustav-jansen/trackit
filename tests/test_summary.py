"""Tests for summary command."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_summary_empty(cli_runner, temp_db):
    """Test summary when no transactions exist."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )

    assert result.exit_code == 0
    assert "No transactions found" in result.output


def test_summary_basic(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test basic summary groups by top-level category."""
    from datetime import date
    from decimal import Decimal

    # Add some transactions in subcategories
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    # Add a transaction in a different top-level category
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 17),
        amount=Decimal("-30.00"),
        description="Gas",
        category_id=sample_categories["Transportation > Gas"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show top-level categories, not subcategories
    assert "Food & Dining" in result.output
    assert "Transportation" in result.output
    # Should NOT show subcategory names in default summary
    assert "Groceries" not in result.output
    assert "Coffee & Snacks" not in result.output
    # Should show combined totals for Food & Dining (50.00 + 25.50 = 75.50)
    assert "75.50" in result.output or "75.5" in result.output


def test_summary_with_date_filter(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test summary with date filters."""
    from datetime import date
    from decimal import Decimal

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output


def test_summary_with_category_filter(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test summary with category filter groups by subcategories."""
    from datetime import date
    from decimal import Decimal

    # Add transactions in different subcategories of Food & Dining
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    # Filter by the parent category - should show subcategories
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show subcategory names, not full paths
    assert "Groceries" in result.output
    assert "Coffee & Snacks" in result.output or "Coffee" in result.output
    # Should show individual amounts for each subcategory
    assert "50.00" in result.output
    assert "25.50" in result.output or "25.5" in result.output


def test_summary_with_subcategory_filter(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test summary when filtering by a specific subcategory."""
    from datetime import date
    from decimal import Decimal

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Filter by the subcategory itself
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Food & Dining > Groceries",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show the subcategory name
    assert "Groceries" in result.output
    assert "50.00" in result.output


def test_summary_excludes_transfers_by_default(cli_runner, temp_db, sample_account, sample_categories, transaction_service, category_service):
    """Test that Transfer category transactions are excluded by default."""
    from datetime import date
    from decimal import Decimal

    # Create Transfer category and subcategory
    transfer_id = category_service.create_category(name="Transfer", parent_path=None)
    transfer_sub_id = category_service.create_category(name="Between Accounts", parent_path="Transfer")

    # Add a regular transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add a transfer transaction
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub_id,
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show Food & Dining
    assert "Food & Dining" in result.output
    assert "50.00" in result.output
    # Should NOT show Transfer
    assert "Transfer" not in result.output
    assert "100.00" not in result.output


def test_summary_includes_transfers_with_flag(cli_runner, temp_db, sample_account, sample_categories, transaction_service, category_service):
    """Test that Transfer category transactions are included with --include-transfers flag."""
    from datetime import date
    from decimal import Decimal

    # Create Transfer category and subcategory
    transfer_id = category_service.create_category(name="Transfer", parent_path=None)
    transfer_sub_id = category_service.create_category(name="Between Accounts", parent_path="Transfer")

    # Add a regular transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add a transfer transaction
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub_id,
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--include-transfers"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show Food & Dining
    assert "Food & Dining" in result.output
    assert "50.00" in result.output
    # Should show Transfer
    assert "Transfer" in result.output
    assert "100.00" in result.output


def test_summary_excludes_transfers_with_subcategories(cli_runner, temp_db, sample_account, sample_categories, transaction_service, category_service):
    """Test that Transfer category and all its subcategories are excluded by default."""
    from datetime import date
    from decimal import Decimal

    # Create Transfer category with multiple subcategories
    transfer_id = category_service.create_category(name="Transfer", parent_path=None)
    transfer_sub1_id = category_service.create_category(name="Between Accounts", parent_path="Transfer")
    transfer_sub2_id = category_service.create_category(name="To Investment", parent_path="Transfer")

    # Add regular transactions
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add transfer transactions in different subcategories
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub1_id,
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 17),
        amount=Decimal("-200.00"),
        description="Transfer to investment",
        category_id=transfer_sub2_id,
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show Food & Dining
    assert "Food & Dining" in result.output
    assert "50.00" in result.output
    # Should NOT show Transfer or any of its subcategories
    assert "Transfer" not in result.output
    assert "Between Accounts" not in result.output
    assert "To Investment" not in result.output
    assert "100.00" not in result.output
    assert "200.00" not in result.output

