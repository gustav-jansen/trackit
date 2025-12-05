"""Integration tests for end-to-end workflows."""

import pytest
from click.testing import CliRunner
from trackit.cli.main import cli


def test_full_workflow(cli_runner, temp_db, fixtures_dir):
    """Test complete workflow: account → format → import → categorize → view → summary."""
    # Step 1: Initialize categories
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "init-categories"]
    )
    assert result.exit_code == 0
    
    # Step 2: Create account
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "account",
            "create",
            "Test Bank",
            "--bank",
            "Test Bank",
        ],
    )
    assert result.exit_code == 0
    account_id = None
    for line in result.output.split("\n"):
        if "ID:" in line:
            # Extract account ID from output like "Created account 'Test Bank' (ID: 1)"
            parts = line.split("ID:")
            if len(parts) > 1:
                account_id = parts[1].strip().rstrip(")")
                break
    
    assert account_id is not None
    
    # Step 3: Create CSV format (use account name for easier testing)
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "format",
            "create",
            "Test Format",
            "--account",
            "Test Bank",
        ],
    )
    assert result.exit_code == 0
    
    # Step 4: Map CSV columns
    mappings = [
        ("Transaction ID", "unique_id", True),
        ("Date", "date", True),
        ("Amount", "amount", True),
        ("Description", "description", False),
    ]
    
    for csv_col, db_field, required in mappings:
        args = [
            "--db-path",
            temp_db.database_path,
            "format",
            "map",
            "Test Format",
            csv_col,
            db_field,
        ]
        if required:
            args.append("--required")
        
        result = cli_runner.invoke(cli, args)
        assert result.exit_code == 0
    
    # Step 5: Import CSV
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
    assert "Imported:" in result.output
    
    # Step 6: View transactions
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "view"]
    )
    assert result.exit_code == 0
    assert "transaction" in result.output.lower()
    
    # Step 7: Get summary
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )
    assert result.exit_code == 0
    assert "Category Summary" in result.output or "No transactions found" in result.output


def test_workflow_with_categorization(cli_runner, temp_db, sample_categories, sample_account, transaction_service):
    """Test workflow including transaction categorization."""
    from datetime import date
    from decimal import Decimal
    
    # Create a transaction
    txn_id = transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account["id"],
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Grocery Store",
    )
    
    # Categorize it
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
    
    # Add notes
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "notes",
            str(txn_id),
            "Weekly shopping trip",
        ],
    )
    assert result.exit_code == 0
    
    # View in verbose mode to see category and notes
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "view", "--verbose"]
    )
    assert result.exit_code == 0
    assert "Groceries" in result.output or "Food & Dining" in result.output
    assert "Weekly shopping trip" in result.output
    
    # Summary should show the categorized transaction
    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary"]
    )
    assert result.exit_code == 0
    assert "Groceries" in result.output or "Food & Dining" in result.output

