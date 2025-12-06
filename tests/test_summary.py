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
    """Test basic summary."""
    from datetime import date
    from decimal import Decimal
    
    # Add some transactions
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
    
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )
    
    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "Groceries" in result.output or "Food & Dining" in result.output


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
    """Test summary with category filter."""
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
    
    # Filter by the exact category path that the transaction has
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

