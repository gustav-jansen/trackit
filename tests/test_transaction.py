"""Tests for transaction commands."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_add_transaction_minimal(cli_runner, temp_db, sample_account):
    """Test adding a transaction with minimal fields."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "add",
            "--account",
            str(sample_account["id"]),
            "--date",
            "2024-01-15",
            "--amount",
            "-50.00",
        ],
    )
    
    assert result.exit_code == 0
    assert "Created transaction" in result.output
    assert "Test Account" in result.output


def test_add_transaction_full(cli_runner, temp_db, sample_account, sample_categories):
    """Test adding a transaction with all fields."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "add",
            "--account",
            str(sample_account["id"]),
            "--date",
            "2024-01-15",
            "--amount",
            "-50.00",
            "--description",
            "Grocery Store",
            "--reference",
            "REF001",
            "--category",
            "Food & Dining > Groceries",
            "--notes",
            "Weekly shopping",
        ],
    )
    
    assert result.exit_code == 0
    assert "Created transaction" in result.output
    assert "Grocery Store" in result.output


def test_add_transaction_invalid_account(cli_runner, temp_db):
    """Test adding transaction with invalid account."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "add",
            "--account",
            "999",
            "--date",
            "2024-01-15",
            "--amount",
            "-50.00",
        ],
    )
    
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_view_transactions_empty(cli_runner, temp_db):
    """Test viewing transactions when none exist."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "view"]
    )
    
    assert result.exit_code == 0
    assert "No transactions found" in result.output


def test_view_transactions(cli_runner, temp_db, sample_account, transaction_service):
    """Test viewing transactions."""
    # Add a transaction
    from datetime import date
    from decimal import Decimal
    
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
    )
    
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "view"]
    )
    
    assert result.exit_code == 0
    assert "TXN001" in result.output or "Test Transaction" in result.output


def test_view_transactions_verbose(cli_runner, temp_db, sample_account, transaction_service):
    """Test viewing transactions in verbose mode."""
    from datetime import date
    from decimal import Decimal
    
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
        notes="Test notes",
    )
    
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "view", "--verbose"]
    )
    
    assert result.exit_code == 0
    assert "Transaction ID:" in result.output
    assert "Notes:" in result.output
    assert "Unique ID:" in result.output


def test_view_transactions_with_filters(cli_runner, temp_db, sample_account, transaction_service):
    """Test viewing transactions with date filters."""
    from datetime import date
    from decimal import Decimal
    
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
    )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "view",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
        ],
    )
    
    assert result.exit_code == 0
    assert "transaction" in result.output.lower()


def test_categorize_transaction(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test categorizing a transaction."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
    )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "categorize",
            str(txn_id),
            "Food & Dining > Groceries",
        ],
    )
    
    assert result.exit_code == 0
    assert "categorized" in result.output.lower()


def test_notes_add(cli_runner, temp_db, sample_account, transaction_service):
    """Test adding notes to a transaction."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
    )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "notes",
            str(txn_id),
            "Test notes",
        ],
    )
    
    assert result.exit_code == 0
    assert "Updated notes" in result.output


def test_notes_clear(cli_runner, temp_db, sample_account, transaction_service):
    """Test clearing notes from a transaction."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
        notes="Existing notes",
    )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "notes",
            str(txn_id),
            "--clear",
        ],
    )
    
    assert result.exit_code == 0
    assert "Cleared notes" in result.output

