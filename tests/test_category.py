"""Tests for category commands."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_init_categories(cli_runner, temp_db):
    """Test initializing categories."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "init-categories"]
    )

    assert result.exit_code == 0
    assert "Successfully created" in result.output or "Created" in result.output
    assert "categories" in result.output


def test_init_categories_duplicate(cli_runner, temp_db):
    """Test initializing categories twice."""
    # First init
    result1 = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "init-categories"]
    )
    assert result1.exit_code == 0

    # Second init (should warn)
    result2 = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "init-categories"]
    )

    assert "already exist" in result2.output.lower()


def test_category_list(cli_runner, temp_db, sample_categories):
    """Test listing categories."""
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "category", "list"]
    )

    assert result.exit_code == 0
    assert "Income" in result.output
    assert "Food & Dining" in result.output


def test_category_create_root(cli_runner, temp_db):
    """Test creating a root category."""
    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "category", "create", "Test Category"],
    )

    assert result.exit_code == 0
    assert "Created category 'Test Category'" in result.output


def test_category_create_child(cli_runner, temp_db, sample_categories):
    """Test creating a child category."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "category",
            "create",
            "Test Subcategory",
            "--parent",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0
    assert "Created category 'Test Subcategory'" in result.output
    assert "under 'Food & Dining'" in result.output


def test_category_create_invalid_parent(cli_runner, temp_db):
    """Test creating category with invalid parent."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "category",
            "create",
            "Test Category",
            "--parent",
            "Non Existent",
        ],
    )

    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_category_create_with_type_expense(cli_runner, temp_db):
    """Test creating a category with expense type (default)."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "category",
            "create",
            "Test Expense",
            "--type",
            "expense",
        ],
    )

    assert result.exit_code == 0
    assert "Created category 'Test Expense'" in result.output


def test_category_create_with_type_income(cli_runner, temp_db):
    """Test creating a category with income type."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "category",
            "create",
            "Test Income",
            "--type",
            "income",
        ],
    )

    assert result.exit_code == 0
    assert "Created category 'Test Income'" in result.output


def test_category_create_with_type_transfer(cli_runner, temp_db):
    """Test creating a category with transfer type."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "category",
            "create",
            "Test Transfer",
            "--type",
            "transfer",
        ],
    )

    assert result.exit_code == 0
    assert "Created category 'Test Transfer'" in result.output


def test_category_create_defaults_to_expense(cli_runner, temp_db):
    """Test that category defaults to expense type when not specified."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "category",
            "create",
            "Test Default",
        ],
    )

    assert result.exit_code == 0
    assert "Created category 'Test Default'" in result.output

