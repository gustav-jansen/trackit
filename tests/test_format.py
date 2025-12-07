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


def test_format_update_name(cli_runner, temp_db, sample_account, sample_csv_format):
    """Test updating format name."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "update",
            "Test Format",
            "--name",
            "Updated Format Name",
        ],
    )

    assert result.exit_code == 0
    assert "Updated format 'Test Format'" in result.output
    assert "New name: 'Updated Format Name'" in result.output

    # Verify the update worked
    list_result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "format", "list"]
    )
    assert "Updated Format Name" in list_result.output


def test_format_update_account(cli_runner, temp_db, sample_account, sample_csv_format):
    """Test updating format account."""
    # Create second account
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Account 2",
            "--bank",
            "Bank 2",
        ],
    )
    assert result1.exit_code == 0

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "update",
            "Test Format",
            "--account",
            "Account 2",
        ],
    )

    assert result.exit_code == 0
    assert "Updated format 'Test Format'" in result.output
    assert "Reassigned to account: 'Account 2'" in result.output


def test_format_update_both(cli_runner, temp_db, sample_account, sample_csv_format):
    """Test updating both format name and account."""
    # Create second account
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Account 2",
            "--bank",
            "Bank 2",
        ],
    )
    assert result1.exit_code == 0

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "update",
            "Test Format",
            "--name",
            "New Format Name",
            "--account",
            "Account 2",
        ],
    )

    assert result.exit_code == 0
    assert "Updated format 'Test Format'" in result.output
    assert "New name: 'New Format Name'" in result.output
    assert "Reassigned to account: 'Account 2'" in result.output


def test_format_update_duplicate_name(cli_runner, temp_db, sample_account):
    """Test updating format to duplicate name fails."""
    # Create two formats
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Format 1",
            "--account",
            str(sample_account.id),
        ],
    )
    assert result1.exit_code == 0

    result2 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Format 2",
            "--account",
            str(sample_account.id),
        ],
    )
    assert result2.exit_code == 0

    # Try to rename Format 2 to Format 1
    result3 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "update",
            "Format 2",
            "--name",
            "Format 1",
        ],
    )

    assert result3.exit_code == 1
    assert "already exists" in result3.output.lower()


def test_format_update_not_found(cli_runner, temp_db):
    """Test updating non-existent format fails."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "update",
            "NonExistent Format",
            "--name",
            "New Name",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_format_delete(cli_runner, temp_db, sample_account, sample_csv_format):
    """Test deleting a format with confirmation."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "delete",
            "Test Format",
        ],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Deleted format 'Test Format'" in result.output

    # Verify format is deleted
    list_result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "format", "list"]
    )
    assert "Test Format" not in list_result.output


def test_format_delete_without_confirmation(cli_runner, temp_db, sample_account, sample_csv_format):
    """Test that deletion is cancelled without confirmation."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "delete",
            "Test Format",
        ],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Deletion cancelled" in result.output

    # Verify format still exists
    list_result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "format", "list"]
    )
    assert "Test Format" in list_result.output


def test_format_delete_not_found(cli_runner, temp_db):
    """Test deleting non-existent format fails."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "delete",
            "NonExistent Format",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()

