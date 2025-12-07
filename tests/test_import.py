"""Tests for CSV import command."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_import_successful(cli_runner, temp_db, sample_account, sample_csv_format, fixtures_dir):
    """Test successful CSV import."""
    csv_file = fixtures_dir / "sample_transactions.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Format",
        ],
    )

    assert result.exit_code == 0
    assert "Import complete" in result.output
    assert "Imported:" in result.output


def test_import_duplicate_detection(cli_runner, temp_db, sample_account, sample_csv_format, fixtures_dir, transaction_service):
    """Test duplicate detection during import."""
    from datetime import date
    from decimal import Decimal

    # Create existing transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Existing",
    )

    csv_file = fixtures_dir / "sample_transactions_duplicates.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Format",
        ],
    )

    assert result.exit_code == 0
    assert "Skipped:" in result.output
    assert "duplicate" in result.output.lower() or "1" in result.output


def test_import_missing_columns(cli_runner, temp_db, sample_account, sample_csv_format, fixtures_dir):
    """Test import with missing required columns."""
    csv_file = fixtures_dir / "sample_transactions_missing_cols.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Format",
        ],
    )

    assert result.exit_code == 1
    assert "missing required columns" in result.output.lower()


def test_import_invalid_format(cli_runner, temp_db, fixtures_dir):
    """Test import with non-existent format."""
    csv_file = fixtures_dir / "sample_transactions.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Non Existent Format",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_import_invalid_file(cli_runner, temp_db, sample_csv_format):
    """Test import with non-existent file."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            "/nonexistent/file.csv",
            "--format",
            "Test Format",
        ],
    )

    # Click may return exit code 2 for file not found errors
    assert result.exit_code != 0
    assert "does not exist" in result.output.lower() or "not found" in result.output.lower()


def test_import_without_unique_id(cli_runner, temp_db, sample_account, sample_csv_format_no_id, fixtures_dir):
    """Test successful CSV import without unique_id field (generated ID)."""
    csv_file = fixtures_dir / "sample_transactions_no_id.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Format No ID",
        ],
    )

    assert result.exit_code == 0
    assert "Import complete" in result.output
    assert "Imported:" in result.output
    assert "5" in result.output  # Should import 5 transactions


def test_import_duplicate_detection_generated_id(cli_runner, temp_db, sample_account, sample_csv_format_no_id, fixtures_dir, transaction_service):
    """Test duplicate detection with generated IDs."""
    from datetime import date
    from decimal import Decimal
    from trackit.domain.csv_import import CSVImportService

    # Create a transaction that will match one in the CSV
    # The CSV has: 2024-01-15,Grocery Store,-50.00
    import_service = CSVImportService(temp_db)
    generated_id = import_service._generate_unique_id(
        date(2024, 1, 15),
        "Grocery Store",
        Decimal("-50.00")
    )

    transaction_service.create_transaction(
        unique_id=generated_id,
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Grocery Store",
    )

    csv_file = fixtures_dir / "sample_transactions_no_id.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Format No ID",
        ],
    )

    assert result.exit_code == 0
    assert "Skipped:" in result.output
    assert "duplicate" in result.output.lower()
    assert "Row 2" in result.output  # Should show row number
    assert "Grocery Store" in result.output  # Should show description
    assert "-50.00" in result.output  # Should show amount


def test_import_missing_description_without_unique_id(cli_runner, temp_db, sample_account, sample_csv_format_no_id, fixtures_dir):
    """Test that missing description errors when unique_id is not provided."""
    # Create a CSV file with missing description
    import tempfile
    import csv

    csv_content = [
        ["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"],
        ["2024-01-15", "2024-01-15", "", "Food", "Debit", "-50.00", "REF001"],
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerows(csv_content)
        temp_csv = f.name

    try:
        result = cli_runner.invoke(
            cli,
            [
                "--db-path",
                temp_db.database_path,
                "import",
                temp_csv,
                "--format",
                "Test Format No ID",
            ],
        )

        assert result.exit_code == 0  # Import completes but with error
        assert "Missing description" in result.output
        assert "required when unique_id is not provided" in result.output
    finally:
        import os
        if os.path.exists(temp_csv):
            os.unlink(temp_csv)


def test_import_skipped_details_reported(cli_runner, temp_db, sample_account, sample_csv_format, fixtures_dir, transaction_service):
    """Test that skipped duplicates are reported with details."""
    from datetime import date
    from decimal import Decimal

    # Create existing transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Grocery Store",
    )

    csv_file = fixtures_dir / "sample_transactions_duplicates.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Format",
        ],
    )

    assert result.exit_code == 0
    assert "Skipped:" in result.output
    # Check that details are shown
    assert "Row" in result.output
    assert "Date:" in result.output or "2024-01-15" in result.output
    assert "Description:" in result.output or "Grocery Store" in result.output
    assert "Amount:" in result.output or "-50.00" in result.output


def test_import_debit_credit_format(cli_runner, temp_db, sample_account, sample_debit_credit_format, fixtures_dir):
    """Test successful CSV import with debit/credit format."""
    csv_file = fixtures_dir / "sample_transactions_debit_credit.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Debit Credit Format",
        ],
    )

    assert result.exit_code == 0
    assert "Import complete" in result.output
    assert "Imported:" in result.output
    assert "5" in result.output  # Should import 5 transactions


def test_import_debit_credit_amounts(cli_runner, temp_db, sample_account, sample_debit_credit_format, fixtures_dir, transaction_service):
    """Test that debit/credit amounts are correctly converted."""
    from datetime import date
    from decimal import Decimal

    csv_file = fixtures_dir / "sample_transactions_debit_credit.csv"

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Debit Credit Format",
        ],
    )

    assert result.exit_code == 0

    # Check that amounts were correctly converted:
    # Debit 19.74 (positive) -> -19.74 (negative) with negate_debit=True
    # Credit -1482.17 (negative) -> 1482.17 (positive) with negate_credit=True
    transactions = transaction_service.list_transactions()

    # Find the Microsoft transaction (debit)
    microsoft_txn = next((t for t in transactions if "Microsoft" in (t.description or "")), None)
    assert microsoft_txn is not None
    assert microsoft_txn.amount == Decimal("-19.74")

    # Find the payment transaction (credit)
    payment_txn = next((t for t in transactions if "ONLINE PAYMENT" in (t.description or "")), None)
    assert payment_txn is not None
    assert payment_txn.amount == Decimal("1482.17")


def test_import_debit_credit_both_empty(cli_runner, temp_db, sample_account, sample_debit_credit_format, fixtures_dir):
    """Test import error when both debit and credit are empty."""
    import tempfile
    import csv

    # Create a CSV with a row where both debit and credit are empty
    csv_content = [
        ["Status", "Date", "Description", "Debit", "Credit", "Member Name"],
        ["Cleared", "11/26/2025", "Test Transaction", "", "", "GUSTAV R JANSEN"],
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerows(csv_content)
        temp_csv = f.name

    try:
        result = cli_runner.invoke(
            cli,
            [
                "--db-path",
                temp_db.database_path,
                "import",
                temp_csv,
                "--format",
                "Test Debit Credit Format",
            ],
        )

        assert result.exit_code == 0  # Import completes but with error
        assert "Missing both debit and credit values" in result.output
        assert "exactly one required" in result.output
    finally:
        import os
        if os.path.exists(temp_csv):
            os.unlink(temp_csv)


def test_import_debit_credit_both_filled(cli_runner, temp_db, sample_account, sample_debit_credit_format, fixtures_dir):
    """Test import error when both debit and credit have values."""
    import tempfile
    import csv

    # Create a CSV with a row where both debit and credit have values
    csv_content = [
        ["Status", "Date", "Description", "Debit", "Credit", "Member Name"],
        ["Cleared", "11/26/2025", "Test Transaction", "10.00", "-20.00", "GUSTAV R JANSEN"],
    ]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.writer(f)
        writer.writerows(csv_content)
        temp_csv = f.name

    try:
        result = cli_runner.invoke(
            cli,
            [
                "--db-path",
                temp_db.database_path,
                "import",
                temp_csv,
                "--format",
                "Test Debit Credit Format",
            ],
        )

        assert result.exit_code == 0  # Import completes but with error
        assert "Both debit and credit have values" in result.output
        assert "exactly one required" in result.output
    finally:
        import os
        if os.path.exists(temp_csv):
            os.unlink(temp_csv)


def test_import_debit_credit_unique_id_generation(cli_runner, temp_db, sample_account, sample_debit_credit_format, fixtures_dir, transaction_service):
    """Test unique ID generation with debit/credit format."""
    from trackit.domain.csv_import import CSVImportService
    from datetime import date
    from decimal import Decimal

    csv_file = fixtures_dir / "sample_transactions_debit_credit.csv"

    # Import once
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Debit Credit Format",
        ],
    )

    assert result.exit_code == 0
    assert "Imported: 5" in result.output

    # Import again - should skip duplicates
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "import",
            str(csv_file),
            "--format",
            "Test Debit Credit Format",
        ],
    )

    assert result.exit_code == 0
    assert "Skipped:" in result.output
    assert "5" in result.output  # Should skip 5 duplicates

