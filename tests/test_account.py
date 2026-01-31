"""Tests for account commands."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_account_create_with_bank(cli_runner, temp_db, monkeypatch):
    """Test creating an account with --bank option."""
    # Set database path
    monkeypatch.setenv("TRACKIT_DB_PATH", temp_db.database_path)

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Test Account",
            "--bank",
            "Test Bank",
        ],
    )

    assert result.exit_code == 0
    assert "Created account 'Test Account'" in result.output
    assert "ID:" in result.output


def test_account_create_without_bank(cli_runner, temp_db):
    """Test creating an account without --bank option (short form)."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "create", "Chase"]
    )

    assert result.exit_code == 0
    assert "Created account 'Chase'" in result.output
    assert "Bank name set to 'Chase'" in result.output


def test_account_list_empty(cli_runner, temp_db):
    """Test listing accounts when none exist."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "list"]
    )

    assert result.exit_code == 0
    assert "No accounts found" in result.output


def test_account_list_with_data(cli_runner, temp_db, sample_account):
    """Test listing accounts with data."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "list"]
    )

    assert result.exit_code == 0
    assert "Test Account" in result.output
    assert "Test Bank" in result.output


def test_account_create_duplicate(cli_runner, temp_db):
    """Test creating duplicate account name fails."""
    # Create first account
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Test Account",
            "--bank",
            "Bank1",
        ],
    )
    assert result1.exit_code == 0

    # Try to create duplicate
    result2 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Test Account",
            "--bank",
            "Bank2",
        ],
    )

    assert result2.exit_code == 1
    assert "already exists" in result2.output.lower()


def test_account_name_resolution(cli_runner, temp_db, sample_account):
    """Test that account names can be used in commands."""
    # Test that we can use account name in add command
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
            "-10.00",
        ],
    )

    assert result.exit_code == 0
    assert "Created transaction" in result.output


def test_account_rename_name_only(cli_runner, temp_db, sample_account):
    """Test renaming account name only."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "rename",
            "Test Account",
            "New Account Name",
        ],
    )

    assert result.exit_code == 0
    assert "Renamed account to 'New Account Name'" in result.output

    # Verify the rename worked
    list_result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "list"]
    )
    assert "New Account Name" in list_result.output
    assert "Test Account" not in list_result.output


def test_account_rename_name_and_bank(cli_runner, temp_db, sample_account):
    """Test renaming both account name and bank name."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "rename",
            "Test Account",
            "New Account Name",
            "--bank",
            "New Bank Name",
        ],
    )

    assert result.exit_code == 0
    assert "Renamed account to 'New Account Name'" in result.output
    assert "Bank name updated to 'New Bank Name'" in result.output


def test_account_rename_duplicate_name(cli_runner, temp_db):
    """Test renaming to duplicate name fails."""
    # Create two accounts
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Account 1",
            "--bank",
            "Bank1",
        ],
    )
    assert result1.exit_code == 0

    result2 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Account 2",
            "--bank",
            "Bank2",
        ],
    )
    assert result2.exit_code == 0

    # Try to rename Account 2 to Account 1
    result3 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "rename",
            "Account 2",
            "Account 1",
        ],
    )

    assert result3.exit_code == 1
    assert "already exists" in result3.output.lower()


def test_account_rename_not_found(cli_runner, temp_db):
    """Test renaming non-existent account fails."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "rename",
            "NonExistent",
            "New Name",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_account_rename_invalid_id(cli_runner, temp_db):
    """Test renaming with an invalid account ID fails."""
    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "account", "rename", "999", "New Name"],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_account_rename_by_id(cli_runner, temp_db, sample_account):
    """Test renaming account using account ID."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "rename",
            "1",
            "Renamed Account",
        ],
    )

    assert result.exit_code == 0
    assert "Renamed account to 'Renamed Account'" in result.output


def test_account_delete_with_confirmation(cli_runner, temp_db, sample_account):
    """Test deleting account with confirmation."""
    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "account", "delete", "Test Account"],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Deleted account 'Test Account'" in result.output

    # Verify account is deleted
    list_result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "list"]
    )
    assert "Test Account" not in list_result.output


def test_account_delete_without_confirmation(cli_runner, temp_db, sample_account):
    """Test that deletion is cancelled without confirmation."""
    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "account", "delete", "Test Account"],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Deletion cancelled" in result.output

    # Verify account still exists
    list_result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "list"]
    )
    assert "Test Account" in list_result.output


def test_account_delete_invalid_id(cli_runner, temp_db):
    """Test deleting with an invalid account ID fails."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "delete", "999"]
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_account_delete_with_transactions(cli_runner, temp_db, sample_account):
    """Test that deleting account with transactions fails."""
    # Create a transaction
    result1 = cli_runner.invoke(
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
            "-10.00",
        ],
    )
    assert result1.exit_code == 0

    # Try to delete account
    result2 = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "delete", "Test Account"]
    )

    assert result2.exit_code == 1
    assert "Cannot delete account" in result2.output
    assert "transaction" in result2.output.lower()


def test_account_delete_with_formats(cli_runner, temp_db, sample_account):
    """Test that deleting account with CSV formats fails."""
    # Create a CSV format
    result1 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format",
            "--account",
            "Test Account",
        ],
    )
    assert result1.exit_code == 0

    # Try to delete account
    result2 = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "delete", "Test Account"]
    )

    assert result2.exit_code == 1
    assert "Cannot delete account" in result2.output
    assert "csv format" in result2.output.lower()


def test_account_delete_with_both(cli_runner, temp_db, sample_account):
    """Test that deleting account with both transactions and formats fails."""
    # Create a transaction
    result1 = cli_runner.invoke(
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
            "-10.00",
        ],
    )
    assert result1.exit_code == 0

    # Create a CSV format
    result2 = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format",
            "--account",
            "Test Account",
        ],
    )
    assert result2.exit_code == 0

    # Try to delete account
    result3 = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "delete", "Test Account"]
    )

    assert result3.exit_code == 1
    assert "Cannot delete account" in result3.output
    assert "transaction" in result3.output.lower()
    assert "csv format" in result3.output.lower()


def test_account_delete_not_found(cli_runner, temp_db):
    """Test deleting non-existent account fails."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "delete", "NonExistent"]
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_account_delete_by_id(cli_runner, temp_db, sample_account):
    """Test deleting account using account ID."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "delete", "1"], input="y\n"
    )

    assert result.exit_code == 0
    assert "Deleted account" in result.output
