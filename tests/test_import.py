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
        account_id=sample_account["id"],
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

