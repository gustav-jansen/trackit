"""Tests for CSV format commands."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_format_create(cli_runner, temp_db, sample_account):
    """Test creating a CSV format."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format",
            "--account",
            str(sample_account.id),
        ],
    )
    
    assert result.exit_code == 0
    assert "Created CSV format 'Test Format'" in result.output
    assert "Use 'format map'" in result.output


def test_format_map(cli_runner, temp_db, sample_account):
    """Test mapping CSV columns."""
    # Create format first
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format",
            "--account",
            str(sample_account.id),
        ],
    )
    assert result1.exit_code == 0
    
    # Add mappings
    result2 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "map",
            "Test Format",
            "Transaction ID",
            "unique_id",
            "--required",
        ],
    )
    
    assert result2.exit_code == 0
    assert "Mapped CSV column 'Transaction ID'" in result2.output


def test_format_list_empty(cli_runner, temp_db):
    """Test listing formats when none exist."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "format", "list"]
    )
    
    assert result.exit_code == 0
    assert "No CSV formats found" in result.output


def test_format_list_with_data(cli_runner, temp_db, sample_csv_format):
    """Test listing formats with data."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "format", "list"]
    )
    
    assert result.exit_code == 0
    assert "Test Format" in result.output


def test_format_show(cli_runner, temp_db, sample_csv_format):
    """Test showing format details."""
    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "format", "show", "Test Format"],
    )
    
    assert result.exit_code == 0
    assert "Format: Test Format" in result.output
    assert "Column Mappings" in result.output


def test_format_map_invalid_field(cli_runner, temp_db, sample_account):
    """Test mapping with invalid db_field_name."""
    # Create format first
    cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format",
            "--account",
            str(sample_account.id),
        ],
    )
    
    # Try invalid field
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "map",
            "Test Format",
            "Some Column",
            "invalid_field",
        ],
    )
    
    assert result.exit_code == 1
    assert "Invalid db_field_name" in result.output


def test_format_create_with_account_name(cli_runner, temp_db, sample_account):
    """Test creating format with account name instead of ID."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format 2",
            "--account",
            "Test Account",
        ],
    )
    
    assert result.exit_code == 0
    assert "Created CSV format 'Test Format 2'" in result.output


def test_format_list_with_account_name(cli_runner, temp_db, sample_account, sample_csv_format):
    """Test listing formats filtered by account name."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "list",
            "--account",
            "Test Account",
        ],
    )
    
    assert result.exit_code == 0
    assert "Test Format" in result.output

