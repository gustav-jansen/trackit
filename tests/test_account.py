"""Tests for account commands."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_account_create_with_bank(cli_runner, temp_db, monkeypatch):
    """Test creating an account with --bank option."""
    # Set database path
    monkeypatch.setenv("TRACKIT_DB_PATH", temp_db.database_path)
    
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "create", "Test Account", "--bank", "Test Bank"]
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
        cli, ["--db-path", temp_db.database_path, "account", "create", "Test Account", "--bank", "Bank1"]
    )
    assert result1.exit_code == 0
    
    # Try to create duplicate
    result2 = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "account", "create", "Test Account", "--bank", "Bank2"]
    )
    
    assert result2.exit_code == 1
    assert "already exists" in result2.output.lower()

