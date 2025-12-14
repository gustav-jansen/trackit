"""Tests for transaction commands."""

import pytest
from datetime import timedelta
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
        cli, ["--db-path", temp_db.database_path, "transaction", "list"]
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
        cli, ["--db-path", temp_db.database_path, "transaction", "list"]
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
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--verbose"]
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
            "transaction",
            "list",
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
            "transaction",
            "list",
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
            "transaction",
            "list",
            "--uncategorized",
        ],
    )

    assert result.exit_code == 0
    assert "Uncategorized Transaction" in result.output
    if sample_categories:
        assert "Categorized Transaction" not in result.output


def test_view_transactions_shows_totals(cli_runner, temp_db, sample_account, transaction_service):
    """Test that transaction list command shows totals."""
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
            "transaction",
            "list",
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
            "transaction",
            "list",
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


def test_categorize_uncategorized_transaction(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test categorizing an uncategorized transaction (should work without --force)."""
    from datetime import date
    from decimal import Decimal

    # Create uncategorized transaction
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
    assert "Food & Dining > Groceries" in result.output


def test_categorize_already_categorized_without_force(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test attempting to recategorize without --force (should fail)."""
    from datetime import date
    from decimal import Decimal

    # Create and categorize a transaction
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Try to recategorize without --force
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "categorize",
            str(txn_id),
            "Food & Dining > Restaurants",
        ],
    )

    assert result.exit_code == 1
    assert "already has category" in result.output.lower()
    assert "Food & Dining > Groceries" in result.output
    assert "--force" in result.output.lower()


def test_categorize_already_categorized_with_force(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test recategorizing with --force flag (should succeed)."""
    from datetime import date
    from decimal import Decimal

    # Create and categorize a transaction
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Recategorize with --force
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "categorize",
            "--force",
            str(txn_id),
            "Food & Dining > Restaurants",
        ],
    )

    assert result.exit_code == 0
    assert "categorized" in result.output.lower()
    assert "Food & Dining > Restaurants" in result.output

    # Verify the category was actually changed
    txn = transaction_service.get_transaction(txn_id)
    assert txn is not None
    assert txn.category_id == sample_categories["Food & Dining > Restaurants"]


def test_categorize_multiple_mixed_states(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test multiple transactions with mixed states (categorized/uncategorized)."""
    from datetime import date
    from decimal import Decimal

    # Create one uncategorized transaction
    txn1_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Transaction 1",
    )

    # Create one categorized transaction
    txn2_id = transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-30.00"),
        description="Transaction 2",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Try to categorize both without --force (should fail for txn2)
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "categorize",
            str(txn1_id),
            str(txn2_id),
            "Food & Dining > Restaurants",
        ],
    )

    assert result.exit_code == 1
    assert "Categorizing 2 transactions" in result.output
    assert "succeeded" in result.output.lower()
    assert "failed" in result.output.lower()
    assert "already has category" in result.output.lower()
    assert "Food & Dining > Groceries" in result.output

    # Verify txn1 was categorized, txn2 was not
    txn1 = transaction_service.get_transaction(txn1_id)
    txn2 = transaction_service.get_transaction(txn2_id)
    assert txn1 is not None
    assert txn2 is not None
    assert txn1.category_id == sample_categories["Food & Dining > Restaurants"]
    assert txn2.category_id == sample_categories["Food & Dining > Groceries"]  # Unchanged

    # Now try with --force (should succeed for both)
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "categorize",
            "--force",
            str(txn1_id),
            str(txn2_id),
            "Food & Dining > Groceries",
        ],
    )

    assert result.exit_code == 0
    assert "succeeded" in result.output.lower()
    assert "failed" in result.output.lower() or "0 failed" in result.output

    # Verify both were recategorized
    txn1 = transaction_service.get_transaction(txn1_id)
    txn2 = transaction_service.get_transaction(txn2_id)
    assert txn1 is not None
    assert txn2 is not None
    assert txn1.category_id == sample_categories["Food & Dining > Groceries"]
    assert txn2.category_id == sample_categories["Food & Dining > Groceries"]


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


def test_transaction_update_all_fields(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test updating all transaction fields."""
    from datetime import date
    from decimal import Decimal

    # Create second account
    from trackit.domain.account import AccountService
    account_service = AccountService(temp_db)
    account2_id = account_service.create_account("Account 2", "Bank 2")

    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Original Description",
        reference_number="REF001",
        notes="Original notes",
    )

    # Get a category ID if available
    category_path = None
    if sample_categories:
        category_path = "Food & Dining > Groceries"

    cmd = [
        "--db-path",
        temp_db.database_path,
        "transaction",
        "update",
        str(txn_id),
        "--account",
        "Account 2",
        "--date",
        "2024-02-20",
        "--amount",
        "-75.00",
        "--description",
        "Updated Description",
        "--reference",
        "REF002",
        "--notes",
        "Updated notes",
    ]
    if category_path:
        cmd.extend(["--category", category_path])

    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 0
    assert "Updated transaction" in result.output


def test_transaction_update_partial(cli_runner, temp_db, sample_account, transaction_service):
    """Test updating only some transaction fields."""
    from datetime import date
    from decimal import Decimal

    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Original Description",
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "update",
            str(txn_id),
            "--amount",
            "-75.00",
            "--description",
            "Updated Description",
        ],
    )

    assert result.exit_code == 0
    assert "Updated transaction" in result.output


def test_transaction_update_not_found(cli_runner, temp_db):
    """Test updating non-existent transaction fails."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "update",
            "99999",
            "--amount",
            "-75.00",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_transaction_update_clear_category(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test clearing category by setting it to empty string."""
    from datetime import date
    from decimal import Decimal

    # Get a category ID
    category_id = None
    if sample_categories:
        category_id = list(sample_categories.values())[0]

    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Test Transaction",
        category_id=category_id,
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "update",
            str(txn_id),
            "--category",
            "",
        ],
    )

    assert result.exit_code == 0
    assert "Updated transaction" in result.output


def test_transaction_delete(cli_runner, temp_db, sample_account, transaction_service):
    """Test deleting a transaction with confirmation."""
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
            "transaction",
            "delete",
            str(txn_id),
        ],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Deleted transaction" in result.output

    # Verify transaction is deleted
    txn = transaction_service.get_transaction(txn_id)
    assert txn is None


def test_transaction_delete_without_confirmation(cli_runner, temp_db, sample_account, transaction_service):
    """Test that deletion is cancelled without confirmation."""
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
            "transaction",
            "delete",
            str(txn_id),
        ],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Deletion cancelled" in result.output

    # Verify transaction still exists
    txn = transaction_service.get_transaction(txn_id)
    assert txn is not None


def test_transaction_delete_not_found(cli_runner, temp_db):
    """Test deleting non-existent transaction fails."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "delete",
            "99999",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_transaction_list_this_month(cli_runner, temp_db, sample_account, transaction_service):
    """Test transaction list with --this-month option."""
    from datetime import date, timedelta
    from decimal import Decimal

    today = date.today()
    # Create transaction in current month
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="This month transaction",
    )

    # Create transaction in previous month (should be excluded)
    last_month_date = (today - timedelta(days=32)).replace(day=1)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=last_month_date,
        amount=Decimal("-25.00"),
        description="Last month transaction",
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--this-month"]
    )

    assert result.exit_code == 0
    assert "This month transaction" in result.output
    # Should not include last month's transaction
    assert "Last month transaction" not in result.output


def test_transaction_list_this_year(cli_runner, temp_db, sample_account, transaction_service):
    """Test transaction list with --this-year option."""
    from datetime import date
    from decimal import Decimal

    today = date.today()
    # Create transaction in current year
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(today.year, 1, 15),
        amount=Decimal("-50.00"),
        description="This year transaction",
    )

    # Create transaction in previous year (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(today.year - 1, 12, 15),
        amount=Decimal("-25.00"),
        description="Last year transaction",
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--this-year"]
    )

    assert result.exit_code == 0
    assert "This year transaction" in result.output
    # Should not include last year's transaction
    assert "Last year transaction" not in result.output


def test_transaction_list_last_month(cli_runner, temp_db, sample_account, transaction_service):
    """Test transaction list with --last-month option."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    today = date.today()
    last_month_start = (today - relativedelta(months=1)).replace(day=1)

    # Create transaction in last month
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=last_month_start,
        amount=Decimal("-50.00"),
        description="Last month transaction",
    )

    # Create transaction in current month (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-25.00"),
        description="This month transaction",
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--last-month"]
    )

    assert result.exit_code == 0
    assert "Last month transaction" in result.output
    # Should not include this month's transaction
    assert "This month transaction" not in result.output


def test_transaction_list_last_year(cli_runner, temp_db, sample_account, transaction_service):
    """Test transaction list with --last-year option."""
    from datetime import date
    from decimal import Decimal

    today = date.today()
    # Create transaction in last year
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(today.year - 1, 6, 15),
        amount=Decimal("-50.00"),
        description="Last year transaction",
    )

    # Create transaction in current year (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-25.00"),
        description="This year transaction",
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--last-year"]
    )

    assert result.exit_code == 0
    assert "Last year transaction" in result.output
    # Should not include this year's transaction
    assert "This year transaction" not in result.output


def test_transaction_list_this_week(cli_runner, temp_db, sample_account, transaction_service):
    """Test transaction list with --this-week option."""
    from datetime import date, timedelta
    from decimal import Decimal

    today = date.today()
    # Create transaction in current week
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="This week transaction",
    )

    # Create transaction in previous week (should be excluded)
    days_since_monday = today.weekday()
    last_week_monday = today - timedelta(days=days_since_monday + 7)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=last_week_monday,
        amount=Decimal("-25.00"),
        description="Last week transaction",
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--this-week"]
    )

    assert result.exit_code == 0
    assert "This week transaction" in result.output
    # Should not include last week's transaction
    assert "Last week transaction" not in result.output


def test_transaction_list_last_week(cli_runner, temp_db, sample_account, transaction_service):
    """Test transaction list with --last-week option."""
    from datetime import date, timedelta
    from decimal import Decimal

    today = date.today()
    # Create transaction in last week
    days_since_monday = today.weekday()
    last_week_monday = today - timedelta(days=days_since_monday + 7)
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=last_week_monday,
        amount=Decimal("-50.00"),
        description="Last week transaction",
    )

    # Create transaction in current week (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-25.00"),
        description="This week transaction",
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "transaction", "list", "--last-week"]
    )

    assert result.exit_code == 0
    assert "Last week transaction" in result.output
    # Should not include this week's transaction
    assert "This week transaction" not in result.output


def test_transaction_list_period_options_validation_multiple(cli_runner, temp_db):
    """Test that multiple period options are rejected."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "list",
            "--this-month",
            "--last-month",
        ],
    )

    assert result.exit_code == 1
    assert "Only one period option" in result.output


def test_transaction_list_period_options_validation_with_start_date(cli_runner, temp_db):
    """Test that period options cannot be combined with --start-date."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "list",
            "--this-month",
            "--start-date",
            "2024-01-01",
        ],
    )

    assert result.exit_code == 1
    assert "cannot be combined" in result.output


def test_transaction_list_period_options_validation_with_end_date(cli_runner, temp_db):
    """Test that period options cannot be combined with --end-date."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "list",
            "--this-month",
            "--end-date",
            "2024-01-31",
        ],
    )

    assert result.exit_code == 1
    assert "cannot be combined" in result.output


def test_transaction_list_period_options_with_category(cli_runner, temp_db, sample_account, sample_categories, transaction_service):
    """Test that period options work with --category filter."""
    from datetime import date
    from decimal import Decimal

    today = date.today()
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-30.00"),
        description="Gas",
        category_id=sample_categories["Transportation > Gas"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "list",
            "--this-month",
            "--category",
            "Food & Dining > Groceries",
        ],
    )

    assert result.exit_code == 0
    assert "Groceries" in result.output
    # Should not show Transportation transaction
    assert "Gas" not in result.output


def test_transaction_list_period_options_with_account(cli_runner, temp_db, sample_account, transaction_service):
    """Test that period options work with --account filter."""
    from datetime import date
    from decimal import Decimal
    from trackit.domain.account import AccountService

    account_service = AccountService(temp_db)
    account2_id = account_service.create_account("Account 2", "Bank 2")

    today = date.today()
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Account 1 transaction",
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=account2_id,
        date=today,
        amount=Decimal("-30.00"),
        description="Account 2 transaction",
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "transaction",
            "list",
            "--this-month",
            "--account",
            "Test Account",
        ],
    )

    assert result.exit_code == 0
    assert "Account 1 transaction" in result.output
    # Should not show Account 2 transaction
    assert "Account 2 transaction" not in result.output

