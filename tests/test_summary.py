"""Tests for summary command."""

import pytest
from datetime import timedelta
from click.testing import CliRunner
from trackit.cli.main import cli


def test_summary_empty(cli_runner, temp_db):
    """Test summary when no transactions exist."""
    result = cli_runner.invoke(cli, ["--db-path", temp_db.database_path, "summary"])

    assert result.exit_code == 0
    assert "No transactions found" in result.output


def test_summary_basic(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test basic summary groups by top-level category."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Add some transactions in subcategories
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
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    # Add a transaction in a different top-level category
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-30.00"),
        description="Gas",
        category_id=sample_categories["Transportation > Gas"],
    )

    result = cli_runner.invoke(cli, ["--db-path", temp_db.database_path, "summary"])

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Default behavior is now columnar format grouped by month
    # Should show top-level categories, not subcategories
    assert "Food & Dining" in result.output
    assert "Transportation" in result.output
    # Should NOT show subcategory names in default summary
    assert "Groceries" not in result.output
    assert "Coffee & Snacks" not in result.output
    # Should show combined totals for Food & Dining (-50.00 + -25.50 = -75.50)
    assert "-75.50" in result.output or "-75.5" in result.output
    # Should show Transportation total (-30.00)
    assert "-30.00" in result.output
    # Should show overall total (-75.50 + -30.00 = -105.50)
    assert "-105.50" in result.output or "-105.5" in result.output
    # Should show month column header (columnar format)
    from dateutil.relativedelta import relativedelta

    expected_months = [
        (today - relativedelta(months=offset)).strftime("%Y-%m") for offset in range(6)
    ]
    assert any(month in result.output for month in expected_months)


def test_summary_with_date_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary with date filters."""
    from datetime import date
    from decimal import Decimal

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-01-31",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output


def test_summary_with_category_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary with category filter groups by subcategories."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Add transactions in different subcategories of Food & Dining
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
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    # Filter by the parent category - should show subcategories
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Default is now columnar format, so check for month header instead of "Total"
    # Should show subcategory names, not full paths
    assert "Groceries" in result.output
    assert "Coffee & Snacks" in result.output or "Coffee" in result.output
    # Should show individual amounts for each subcategory
    assert "-50.00" in result.output
    assert "-25.50" in result.output or "-25.5" in result.output


def test_summary_with_subcategory_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary when filtering by a specific subcategory."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Filter by the subcategory itself
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Food & Dining > Groceries",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Default is now columnar format
    # Should show the subcategory name
    assert "Groceries" in result.output
    assert "-50.00" in result.output


def test_summary_excludes_transfers_by_default(
    cli_runner,
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    """Test that Transfer type category transactions are excluded by default."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Create Transfer type category and subcategory (type 2 = Transfer)
    category_service.create_category(name="Transfer", parent_path=None, category_type=2)
    transfer_sub_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )

    # Add a regular transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add a transfer transaction
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub_id,
    )

    result = cli_runner.invoke(cli, ["--db-path", temp_db.database_path, "summary"])

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Default is now columnar format
    # Should show Food & Dining
    assert "Food & Dining" in result.output
    assert "-50.00" in result.output
    # Should NOT show Transfer
    assert "Transfer" not in result.output
    assert "-100.00" not in result.output


def test_summary_includes_transfers_with_flag(
    cli_runner,
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    """Test that Transfer type category transactions are included with --include-transfers flag."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Create Transfer type category and subcategory (type 2 = Transfer)
    transfer_id = category_service.create_category(
        name="Transfer", parent_path=None, category_type=2
    )
    transfer_sub_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )

    # Add a regular transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add a transfer transaction
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub_id,
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--include-transfers"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Default is now columnar format
    # Should show Food & Dining
    assert "Food & Dining" in result.output
    assert "-50.00" in result.output
    # Should show Transfer
    assert "Transfer" in result.output
    assert "-100.00" in result.output


def test_summary_excludes_transfers_with_subcategories(
    cli_runner,
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    """Test that Transfer type category and all its subcategories are excluded by default."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Create Transfer type category with multiple subcategories (type 2 = Transfer)
    transfer_id = category_service.create_category(
        name="Transfer", parent_path=None, category_type=2
    )
    transfer_sub1_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )
    transfer_sub2_id = category_service.create_category(
        name="To Investment", parent_path="Transfer", category_type=2
    )

    # Add regular transactions
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add transfer transactions in different subcategories
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub1_id,
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-200.00"),
        description="Transfer to investment",
        category_id=transfer_sub2_id,
    )

    result = cli_runner.invoke(cli, ["--db-path", temp_db.database_path, "summary"])

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Default is now columnar format
    # Should show Food & Dining
    assert "Food & Dining" in result.output
    assert "-50.00" in result.output
    # Should NOT show Transfer or any of its subcategories
    assert "Transfer" not in result.output
    assert "Between Accounts" not in result.output
    assert "To Investment" not in result.output
    assert "-100.00" not in result.output
    assert "-200.00" not in result.output


def test_summary_expand_flag(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that --expand flag shows full category tree with indentation."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Add transactions in subcategories
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
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-30.00"),
        description="Gas",
        category_id=sample_categories["Transportation > Gas"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--expand"]
    )

    assert result.exit_code == 0
    assert "Category Summary (Expanded)" in result.output
    # Default is now columnar format, so check for month header
    # Should show parent categories
    assert "Food & Dining" in result.output
    assert "Transportation" in result.output
    # Should show subcategories with indentation
    assert "Groceries" in result.output
    assert "Coffee & Snacks" in result.output or "Coffee" in result.output
    assert "Gas" in result.output
    # Check that subcategories appear after parent (with indentation)
    food_index = result.output.find("Food & Dining")
    groceries_index = result.output.find("Groceries")
    assert food_index < groceries_index
    # Parent should show total including children (-75.50)
    assert "-75.50" in result.output or "-75.5" in result.output
    # Overall total should be sum of all transactions
    assert "-105.50" in result.output or "-105.5" in result.output


def test_summary_expand_with_category_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that --expand with --category shows only that category's subtree."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Add transactions in different categories
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
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
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
            "summary",
            "--expand",
            "--category",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary (Expanded)" in result.output
    # Should show Food & Dining and its subcategories
    assert "Food & Dining" in result.output
    assert "Groceries" in result.output
    assert "Coffee & Snacks" in result.output or "Coffee" in result.output
    # Should NOT show Transportation
    assert "Transportation" not in result.output
    assert "Gas" not in result.output


def test_summary_expand_category_filter_orders_children(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test child ordering within a filtered category subtree."""
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
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--expand",
            "--category",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0

    lines = result.output.split("\n")
    coffee_index = None
    groceries_index = None
    for i, line in enumerate(lines):
        if "Coffee" in line and coffee_index is None:
            coffee_index = i
        if "Groceries" in line and groceries_index is None:
            groceries_index = i

    assert coffee_index is not None
    assert groceries_index is not None
    assert groceries_index < coffee_index


def test_summary_category_filter_nonexistent_path_shows_default_summary(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that a non-existent category path does not filter results."""
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

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Not A Category",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "Food & Dining" not in result.output
    assert "Groceries" not in result.output


def test_summary_expand_with_leaf_category_filter_shows_leaf_only(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that --expand with a leaf category shows only that leaf."""
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

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--expand",
            "--category",
            "Food & Dining > Groceries",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary (Expanded)" in result.output
    assert "Groceries" in result.output
    assert "Food & Dining" not in result.output
    assert "Coffee & Snacks" not in result.output


def test_summary_category_filter_trims_spaces(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that category path trimming matches categories."""
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

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "  Food & Dining  >   Groceries ",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "Groceries" in result.output


def test_summary_category_filter_case_sensitive(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that category path matching is case-sensitive."""
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

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "food & dining > groceries",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "Food & Dining" not in result.output
    assert "Groceries" not in result.output


def test_summary_category_filter_transfer_requires_include_transfers(
    cli_runner,
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    """Test that transfer filters require --include-transfers to show results."""
    from datetime import date
    from decimal import Decimal

    today = date.today()
    transfer_id = category_service.create_category(
        name="Transfer", parent_path=None, category_type=2
    )
    transfer_sub_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )

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
        amount=Decimal("-100.00"),
        description="Transfer to savings",
        category_id=transfer_sub_id,
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Transfer",
        ],
    )

    assert result.exit_code == 0
    assert "No transactions found" in result.output

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--category",
            "Transfer",
            "--include-transfers",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "Transfer" in result.output
    assert "Between Accounts" in result.output
    assert "-100.00" in result.output


def test_summary_expand_root_ordering_by_total(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test expanded ordering of top-level categories by total value."""
    from datetime import date
    from decimal import Decimal

    today = date.today()
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-100.00"),
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

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-10.00"),
        description="Electricity",
        category_id=sample_categories["Bills & Utilities > Electricity"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--expand"]
    )

    assert result.exit_code == 0
    assert "Category Summary (Expanded)" in result.output

    lines = result.output.split("\n")
    bills_index = None
    food_index = None
    transport_index = None
    for i, line in enumerate(lines):
        if "Bills & Utilities" in line and bills_index is None:
            bills_index = i
        if "Food & Dining" in line and food_index is None:
            food_index = i
        if "Transportation" in line and transport_index is None:
            transport_index = i

    assert food_index is not None
    assert transport_index is not None
    assert bills_index is not None
    assert food_index < transport_index
    assert transport_index < bills_index


def test_summary_expand_indentation(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test that expanded view properly indents child categories."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--expand"]
    )

    assert result.exit_code == 0
    # Check that Groceries line starts with indentation (4 spaces)
    lines = result.output.split("\n")
    groceries_line = None
    for line in lines:
        if "Groceries" in line:
            groceries_line = line
            break

    assert groceries_line is not None
    # Should start with 8 spaces for indentation (child category: indent level 2)
    assert groceries_line.startswith("        ")
    # Parent category should have 4 spaces of indentation (indent level 1, relative to headers)
    food_line = None
    for line in lines:
        if "Food & Dining" in line and "Groceries" not in line:
            food_line = line
            break
    assert food_line is not None
    assert food_line.startswith("    ")


def test_summary_groups_by_type_with_subtotals(
    cli_runner,
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    """Test that summary groups categories by type (Income first, then Expense) with subtotals."""
    from datetime import date
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Create an Income type category
    income_cat_id = category_service.create_category(
        name="Salary", parent_path=None, category_type=1
    )

    # Add income transaction
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("5000.00"),
        description="Monthly salary",
        category_id=income_cat_id,
    )

    # Add expense transaction
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(cli, ["--db-path", temp_db.database_path, "summary"])

    assert result.exit_code == 0
    assert "Category Summary" in result.output

    # Check that Income section comes first
    output_lines = result.output.split("\n")
    income_index = None
    expense_index = None
    income_subtotal_index = None
    expense_subtotal_index = None

    for i, line in enumerate(output_lines):
        if "Salary" in line:
            income_index = i
        if "Food & Dining" in line:
            expense_index = i
        if "Income Subtotal" in line:
            income_subtotal_index = i
        if "Expense Subtotal" in line:
            expense_subtotal_index = i

    # Income should come before Expense
    assert income_index is not None
    assert expense_index is not None
    assert income_index < expense_index

    # Subtotals should be present
    assert income_subtotal_index is not None
    assert expense_subtotal_index is not None

    # Income subtotal should come after Income categories but before Expense categories
    assert income_subtotal_index > income_index
    assert income_subtotal_index < expense_index

    # Expense subtotal should come after Expense categories
    assert expense_subtotal_index > expense_index

    # Check that totals are correct
    assert "5000.00" in result.output or "5,000.00" in result.output
    assert "-50.00" in result.output


def test_summary_this_month(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary with --this-month option."""
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
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Create transaction in previous month (should be excluded)
    last_month_date = (today - timedelta(days=32)).replace(day=1)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=last_month_date,
        amount=Decimal("-25.00"),
        description="Last month transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--this-month"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "-50.00" in result.output
    # Should not include last month's transaction
    assert "-25.00" not in result.output


def test_summary_this_year(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary with --this-year option."""
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
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Create transaction in previous year (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(today.year - 1, 12, 15),
        amount=Decimal("-25.00"),
        description="Last year transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--this-year"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "-50.00" in result.output
    # Should not include last year's transaction
    assert "-25.00" not in result.output


def test_summary_last_month(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary with --last-month option."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    today = date.today()
    last_month_start = (today - relativedelta(months=1)).replace(day=1)
    last_month_end = today.replace(day=1) - timedelta(days=1)

    # Create transaction in last month
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=last_month_start,
        amount=Decimal("-50.00"),
        description="Last month transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Create transaction in current month (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-25.00"),
        description="This month transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--last-month"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "-50.00" in result.output
    # Should not include this month's transaction
    assert "-25.00" not in result.output


def test_summary_last_year(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test summary with --last-year option."""
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
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Create transaction in current year (should be excluded)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-25.00"),
        description="This year transaction",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--last-year"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "-50.00" in result.output
    # Should not include this year's transaction
    assert "-25.00" not in result.output


def test_summary_period_options_validation_multiple(cli_runner, temp_db):
    """Test that multiple period options are rejected."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--this-month",
            "--last-month",
        ],
    )

    assert result.exit_code == 1
    assert "Only one period option" in result.output


def test_summary_period_options_validation_with_start_date(cli_runner, temp_db):
    """Test that period options cannot be combined with --start-date."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--this-month",
            "--start-date",
            "2024-01-01",
        ],
    )

    assert result.exit_code == 1
    assert "cannot be combined" in result.output


def test_summary_period_options_validation_with_end_date(cli_runner, temp_db):
    """Test that period options cannot be combined with --end-date."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--this-month",
            "--end-date",
            "2024-01-31",
        ],
    )

    assert result.exit_code == 1
    assert "cannot be combined" in result.output


def test_summary_period_options_with_category(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
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
            "summary",
            "--this-month",
            "--category",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "-50.00" in result.output
    # Should not show Transportation
    assert "Transportation" not in result.output


def test_summary_group_by_month_basic(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test basic month grouping."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Add transactions in different months
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Current month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    # Add transaction in previous month
    last_month = today - relativedelta(months=1)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=last_month,
        amount=Decimal("-30.00"),
        description="Last month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--group-by-month"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show month columns for current month and previous month
    current_month = today.strftime("%Y-%m")
    last_month_str = last_month.strftime("%Y-%m")
    assert current_month in result.output or last_month_str in result.output
    assert "-50.00" in result.output
    assert "-30.00" in result.output


def test_summary_group_by_year_basic(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test basic year grouping."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    # Use explicit date range that spans two years to ensure different year columns
    today = date.today()
    # Start from last year's December to current month to ensure we span years
    start_date = date(today.year - 1, 12, 1)
    end_date = today

    # Add transactions in different years
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(today.year - 1, 12, 15),  # Last December
        amount=Decimal("-50.00"),
        description="Last year groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-30.00"),
        description="This year groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--group-by-year",
            "--start-date",
            start_date.strftime("%Y-%m-%d"),
            "--end-date",
            end_date.strftime("%Y-%m-%d"),
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show year columns for both years
    current_year = str(today.year)
    last_year = str(today.year - 1)
    assert current_year in result.output
    assert last_year in result.output
    assert "-50.00" in result.output
    assert "-30.00" in result.output


def test_summary_group_by_month_with_date_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test month grouping with date range filter."""
    from datetime import date
    from decimal import Decimal

    # Add transactions in different months
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="January groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 2, 15),
        amount=Decimal("-30.00"),
        description="February groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 3, 15),
        amount=Decimal("-25.00"),
        description="March groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--group-by-month",
            "--start-date",
            "2024-01-01",
            "--end-date",
            "2024-02-28",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "2024-01" in result.output
    assert "2024-02" in result.output
    assert "2024-03" not in result.output  # Should be excluded
    assert "-50.00" in result.output
    assert "-30.00" in result.output
    assert "-25.00" not in result.output  # Should be excluded


def test_summary_group_by_year_with_date_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test year grouping with date range filter."""
    from datetime import date
    from decimal import Decimal

    # Add transactions in different years
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2022, 6, 15),
        amount=Decimal("-50.00"),
        description="2022 groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2023, 1, 15),
        amount=Decimal("-30.00"),
        description="2023 groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-25.00"),
        description="2024 groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--group-by-year",
            "--start-date",
            "2022-01-01",
            "--end-date",
            "2023-12-31",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    assert "2022" in result.output
    assert "2023" in result.output
    assert "2024" not in result.output  # Should be excluded
    assert "-50.00" in result.output
    assert "-30.00" in result.output
    assert "-25.00" not in result.output  # Should be excluded


def test_summary_group_by_month_expanded(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test month grouping with --expand flag."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    last_month = today - relativedelta(months=1)
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Current month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=last_month,
        amount=Decimal("-25.50"),
        description="Last month coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    result = cli_runner.invoke(
        cli,
        ["--db-path", temp_db.database_path, "summary", "--group-by-month", "--expand"],
    )

    assert result.exit_code == 0
    assert "Category Summary (Expanded)" in result.output
    # Should show month columns for current month and previous month
    current_month = today.strftime("%Y-%m")
    last_month_str = last_month.strftime("%Y-%m")
    assert current_month in result.output or last_month_str in result.output
    assert "Food & Dining" in result.output
    assert "Groceries" in result.output
    assert "Coffee" in result.output or "Coffee & Snacks" in result.output


def test_summary_group_by_year_expanded(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test year grouping with --expand flag."""
    from datetime import date
    from decimal import Decimal

    # Use explicit date range that spans two years to ensure different year columns
    today = date.today()
    # Start from last year's December to current month to ensure we span years
    start_date = date(today.year - 1, 12, 1)
    end_date = today

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(today.year - 1, 12, 15),  # Last December
        amount=Decimal("-50.00"),
        description="Last year groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-25.50"),
        description="This year coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--group-by-year",
            "--expand",
            "--start-date",
            start_date.strftime("%Y-%m-%d"),
            "--end-date",
            end_date.strftime("%Y-%m-%d"),
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary (Expanded)" in result.output
    # Should show year columns for both years
    current_year = str(today.year)
    last_year = str(today.year - 1)
    assert current_year in result.output
    assert last_year in result.output
    assert "Food & Dining" in result.output
    assert "Groceries" in result.output
    assert "Coffee" in result.output or "Coffee & Snacks" in result.output


def test_summary_group_by_month_year_mutually_exclusive(cli_runner, temp_db):
    """Test that --group-by-month and --group-by-year cannot be used together."""
    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--group-by-month",
            "--group-by-year",
        ],
    )

    assert result.exit_code == 1
    assert "cannot be specified at the same time" in result.output


def test_summary_group_by_month_all_transactions(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test month grouping with no date filter (uses default: last 6 months)."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    # Add transactions in different months
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Current month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    last_month = today - relativedelta(months=1)
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=last_month,
        amount=Decimal("-30.00"),
        description="Last month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--group-by-month"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show month columns for current month and previous month
    current_month = today.strftime("%Y-%m")
    last_month_str = last_month.strftime("%Y-%m")
    assert current_month in result.output or last_month_str in result.output


def test_summary_group_by_month_multiple_periods(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test month grouping with multiple months and different categories."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    last_month = today - relativedelta(months=1)
    # Add transactions in different months and categories
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Current month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-30.00"),
        description="Current month gas",
        category_id=sample_categories["Transportation > Gas"],
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=last_month,
        amount=Decimal("-25.00"),
        description="Last month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli, ["--db-path", temp_db.database_path, "summary", "--group-by-month"]
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show month columns for current month and previous month
    current_month = today.strftime("%Y-%m")
    last_month_str = last_month.strftime("%Y-%m")
    assert current_month in result.output or last_month_str in result.output
    assert "Food & Dining" in result.output
    assert "Transportation" in result.output
    # Check that totals are correct per period
    assert "-50.00" in result.output or "-50.0" in result.output
    assert "-30.00" in result.output or "-30.0" in result.output
    assert "-25.00" in result.output or "-25.0" in result.output


def test_summary_group_by_month_with_category_filter(
    cli_runner, temp_db, sample_account, sample_categories, transaction_service
):
    """Test month grouping with category filter."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from decimal import Decimal

    # Use recent dates within the default 6-month range
    today = date.today()
    last_month = today - relativedelta(months=1)
    # Add transactions in different months and categories
    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-50.00"),
        description="Current month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=today,
        amount=Decimal("-30.00"),
        description="Current month gas",
        category_id=sample_categories["Transportation > Gas"],
    )

    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=last_month,
        amount=Decimal("-25.00"),
        description="Last month groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    result = cli_runner.invoke(
        cli,
        [
            "--db-path",
            temp_db.database_path,
            "summary",
            "--group-by-month",
            "--category",
            "Food & Dining",
        ],
    )

    assert result.exit_code == 0
    assert "Category Summary" in result.output
    # Should show month columns for current month and previous month
    current_month = today.strftime("%Y-%m")
    last_month_str = last_month.strftime("%Y-%m")
    assert current_month in result.output or last_month_str in result.output
    assert "Food & Dining" in result.output or "Groceries" in result.output
    # Should not show Transportation
    assert "Transportation" not in result.output
    assert "-50.00" in result.output or "-50.0" in result.output
    assert "-25.00" in result.output or "-25.0" in result.output
