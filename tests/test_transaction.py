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
            str(sample_account.id),
            "--date",
            "2024-01-15",
            "--amount",
            "-50.00",
        ],
    )
    
    assert result.exit_code == 0
    assert "Created transaction" in result.output
    assert "Test Account" in result.output


def test_add_transaction_with_account_name(cli_runner, temp_db, sample_account):
    """Test adding a transaction using account name instead of ID."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "add",
            "--account",
            "Test Account",
            "--date",
            "2024-01-15",
            "--amount",
            "-50.00",
        ],
    )
    
    assert result.exit_code == 0
    assert "Created transaction" in result.output
    assert "Test Account" in result.output


def test_add_transaction_with_relative_date(cli_runner, temp_db, sample_account):
    """Test adding a transaction with relative date."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "add",
            "--account",
            "Test Account",
            "--date",
            "today",
            "--amount",
            "-50.00",
        ],
    )
    
    assert result.exit_code == 0
    assert "Created transaction" in result.output


def test_add_transaction_full(cli_runner, temp_db, sample_account, sample_categories):
    """Test adding a transaction with all fields."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "add",
            "--account",
            str(sample_account.id),
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
        account_id=sample_account.id,
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
        account_id=sample_account.id,
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
        account_id=sample_account.id,
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


def test_view_transactions_with_account_name(cli_runner, temp_db, sample_account, transaction_service):
    """Test viewing transactions using account name."""
    from datetime import date
    from decimal import Decimal
    
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
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
            "--account",
            "Test Account",
        ],
    )
    
    assert result.exit_code == 0
    assert "TXN001" in result.output or "Test Transaction" in result.output


def test_view_transactions_uncategorized(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test viewing uncategorized transactions."""
    from datetime import date
    from decimal import Decimal
    
    # Create uncategorized transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Uncategorized Transaction",
    )
    
    # Create categorized transaction (use a valid category from sample_categories)
    if sample_categories:
        first_category_id = list(sample_categories.values())[0]
        transaction_service.create_transaction(
            unique_id="TXN002",
            account_id=sample_account.id,
            date=date(2024, 1, 16),
            amount=Decimal("-25.00"),
            description="Categorized Transaction",
            category_id=first_category_id,
        )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "view",
            "--uncategorized",
        ],
    )
    
    assert result.exit_code == 0
    assert "Uncategorized Transaction" in result.output
    if sample_categories:
        assert "Categorized Transaction" not in result.output


def test_view_transactions_shows_totals(cli_runner, temp_db, sample_account, transaction_service):
    """Test that view command shows totals."""
    from datetime import date
    from decimal import Decimal
    
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Expense",
    )
    
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("100.00"),
        description="Income",
    )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "view",
        ],
    )
    
    assert result.exit_code == 0
    assert "TOTAL" in result.output
    assert "Expenses:" in result.output
    assert "Income:" in result.output
    assert "Count:" in result.output


def test_view_transactions_with_relative_dates(cli_runner, temp_db, sample_account, transaction_service):
    """Test viewing transactions with relative dates."""
    from datetime import date, timedelta
    from decimal import Decimal
    
    # Create transaction from yesterday
    yesterday = date.today() - timedelta(days=1)
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=yesterday,
        amount=Decimal("-50.00"),
        description="Yesterday's Transaction",
    )
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "view",
            "--start-date",
            "yesterday",
            "--end-date",
            "today",
        ],
    )
    
    assert result.exit_code == 0
    assert "transaction" in result.output.lower() or "Yesterday's Transaction" in result.output


def test_categorize_transaction(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test categorizing a single transaction (backward compatibility)."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
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


def test_categorize_multiple_transactions(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test categorizing multiple transactions."""
    from datetime import date
    from decimal import Decimal
    
    # Create multiple transactions
    txn_ids = []
    for i in range(3):
        txn_id = transaction_service.create_transaction(
            unique_id=f"TXN{i+1:03d}",
            account_id=sample_account.id,
            date=date(2024, 1, 15 + i),
            amount=Decimal(f"-{10 * (i+1)}.00"),
            description=f"Transaction {i+1}",
        )
        txn_ids.append(txn_id)
    
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "categorize",
            str(txn_ids[0]),
            str(txn_ids[1]),
            str(txn_ids[2]),
            "Food & Dining > Groceries",
        ],
    )
    
    assert result.exit_code == 0
    assert "Categorizing 3 transactions" in result.output
    assert "succeeded" in result.output.lower()
    assert "failed" in result.output.lower() or "0 failed" in result.output


def test_categorize_with_invalid_ids(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test categorizing with mix of valid and invalid transaction IDs."""
    from datetime import date
    from decimal import Decimal
    
    # Create one valid transaction
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
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
            "99999",  # Invalid ID
            "Food & Dining > Groceries",
        ],
    )
    
    assert result.exit_code == 1  # Should exit with error due to failures
    assert "Categorizing 2 transactions" in result.output
    assert "succeeded" in result.output.lower()
    assert "failed" in result.output.lower()


def test_categorize_with_invalid_category(cli_runner, temp_db, sample_account, transaction_service):
    """Test categorizing with invalid category."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
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
            "Non Existent Category",
        ],
    )
    
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_categorize_with_duplicate_ids(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test categorizing with duplicate transaction IDs."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
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
            str(txn_id),  # Duplicate
            str(txn_id),  # Another duplicate
            "Food & Dining > Groceries",
        ],
    )
    
    assert result.exit_code == 0
    # After removing duplicates, only one unique ID remains, so it uses single-transaction format
    assert "categorized" in result.output.lower()
    assert "Food & Dining > Groceries" in result.output
    # Should only process once despite duplicates (no error about duplicate processing)


def test_notes_add(cli_runner, temp_db, sample_account, transaction_service):
    """Test adding notes to a transaction."""
    from datetime import date
    from decimal import Decimal
    
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
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
        account_id=sample_account.id,
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

