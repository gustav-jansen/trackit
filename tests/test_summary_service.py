"""Tests for summary domain service helpers."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from trackit.domain.summary import SummaryService
from trackit.domain.entities import SummaryGroupBy, Transaction, CategoryTreeNode


def _find_node_by_name(nodes, name):
    for node in nodes:
        if node.name == name:
            return node
        child_match = _find_node_by_name(node.children, name)
        if child_match is not None:
            return child_match
    return None


def _flatten_names(nodes):
    names = []
    for node in nodes:
        names.append(node.name)
        names.extend(_flatten_names(node.children))
    return names


def _find_summary_by_name(summaries, name):
    for summary in summaries:
        if summary.get("category_name") == name:
            return summary
    return None


def _find_section_by_name(sections, name):
    for section in sections:
        if section.name == name:
            return section
    return None


def test_build_descendant_map_includes_children(temp_db, sample_categories):
    summary_service = SummaryService(temp_db)
    category_tree = summary_service.get_category_tree(None)
    descendant_map = summary_service.build_descendant_map(category_tree)

    parent_node = _find_node_by_name(category_tree, "Food & Dining")
    child_node = _find_node_by_name(category_tree, "Groceries")

    assert parent_node is not None
    assert child_node is not None
    parent_id = parent_node.id
    child_id = child_node.id

    assert parent_id in descendant_map
    assert parent_id in descendant_map[parent_id]
    assert child_id in descendant_map[parent_id]


def test_build_category_index_with_tree_nodes(temp_db):
    summary_service = SummaryService(temp_db)
    tree = [
        CategoryTreeNode(
            id=1,
            name="Food & Dining",
            parent_id=None,
            category_type=0,
            children=(
                CategoryTreeNode(
                    id=2,
                    name="Groceries",
                    parent_id=1,
                    category_type=0,
                ),
            ),
        )
    ]

    category_index, parent_map, children_map = summary_service.build_category_index(
        tree
    )

    assert category_index[1]["name"] == "Food & Dining"
    assert category_index[2]["name"] == "Groceries"
    assert parent_map[1] is None
    assert parent_map[2] == 1
    assert children_map[1] == {2}


def test_build_descendant_map_with_tree_nodes(temp_db):
    summary_service = SummaryService(temp_db)
    tree = [
        CategoryTreeNode(
            id=10,
            name="Income",
            parent_id=None,
            category_type=1,
            children=(
                CategoryTreeNode(
                    id=11,
                    name="Salary",
                    parent_id=10,
                    category_type=1,
                ),
            ),
        )
    ]

    descendant_map = summary_service.build_descendant_map(tree)

    assert descendant_map[10] == {10, 11}
    assert descendant_map[11] == {11}


def test_get_category_tree_with_filter(temp_db, sample_categories):
    summary_service = SummaryService(temp_db)

    category_tree = summary_service.get_category_tree("Food & Dining")
    assert len(category_tree) == 1
    assert category_tree[0].name == "Food & Dining"

    names = _flatten_names(category_tree)
    assert "Transportation" not in names


def test_group_transactions_by_period_month(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-10.00"),
        description="January",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 2, 20),
        amount=Decimal("-15.00"),
        description="February",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transactions = summary_service.get_filtered_transactions()
    grouped = summary_service.group_transactions_by_period(
        transactions, group_by_month=True
    )

    assert "2024-01" in grouped
    assert "2024-02" in grouped


def test_calculate_category_total_includes_descendants(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 20),
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )

    category_tree = summary_service.get_category_tree(None)
    descendant_map = summary_service.build_descendant_map(category_tree)
    transactions = summary_service.get_filtered_transactions()

    parent_id = sample_categories["Food & Dining"]
    total = summary_service.calculate_category_total(
        descendant_map, parent_id, transactions
    )

    assert total == pytest.approx(-75.5)


def test_get_filtered_transactions_excludes_transfers_by_default(
    temp_db, sample_account, sample_categories, transaction_service, category_service
):
    summary_service = SummaryService(temp_db)

    category_service.create_category(name="Transfer", parent_path=None, category_type=2)
    transfer_sub_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-100.00"),
        description="Transfer",
        category_id=transfer_sub_id,
    )

    transactions = summary_service.get_filtered_transactions(include_transfers=False)
    assert all(txn.category_id != transfer_sub_id for txn in transactions)

    transactions_with_transfers = summary_service.get_filtered_transactions(
        include_transfers=True
    )
    assert any(
        txn.category_id == transfer_sub_id for txn in transactions_with_transfers
    )


def test_build_summary_report_period_fields_month(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 10),
        amount=Decimal("-10.00"),
        description="January",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 2, 5),
        amount=Decimal("-20.00"),
        description="February",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    report = summary_service.build_summary_report(
        group_by=SummaryGroupBy.CATEGORY_MONTH
    )

    assert "2024-01" in report.period_keys
    assert "2024-02" in report.period_keys
    assert report.period_transactions_map["2024-01"]
    assert report.period_transactions_map["2024-02"]
    assert report.category_tree
    assert report.category_summaries


def test_build_summary_report_no_period_grouping_has_empty_periods(temp_db):
    summary_service = SummaryService(temp_db)

    report = summary_service.build_summary_report(group_by=SummaryGroupBy.CATEGORY)

    assert report.period_keys == ()
    assert report.period_transactions_map == {}


def test_build_summary_report_nonexistent_category_path(temp_db):
    summary_service = SummaryService(temp_db)

    report = summary_service.build_summary_report(category_path="Not A Category")

    assert report.category_filter.is_missing is True
    assert report.category_filter.requested_path == "Not A Category"
    assert report.category_filter.resolved_path is None
    assert report.transactions == ()
    assert report.category_tree == ()
    assert report.category_summaries == ()


def test_build_summary_report_resolves_category_filter(temp_db, sample_categories):
    summary_service = SummaryService(temp_db)

    report = summary_service.build_summary_report(category_path="Food & Dining")

    assert report.category_filter.is_missing is False
    assert report.category_filter.requested_path == "Food & Dining"
    assert report.category_filter.resolved_path == "Food & Dining"
    assert report.category_filter.category_id == sample_categories["Food & Dining"]


def test_build_summary_report_transfer_filter_respects_include_transfers(
    temp_db, sample_account, transaction_service, category_service
):
    summary_service = SummaryService(temp_db)

    transfer_id = category_service.create_category(
        name="Transfer", parent_path=None, category_type=2
    )
    transfer_sub_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Transfer",
        category_id=transfer_sub_id,
    )

    report_excluded = summary_service.build_summary_report(
        category_path="Transfer", include_transfers=False
    )
    assert report_excluded.transactions == ()
    assert report_excluded.category_summaries == ()

    report_included = summary_service.build_summary_report(
        category_path="Transfer", include_transfers=True
    )
    assert report_included.transactions
    assert report_included.category_summaries


def test_build_summary_report_period_keys_only_present_periods(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 10),
        amount=Decimal("-10.00"),
        description="January",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 3, 5),
        amount=Decimal("-20.00"),
        description="March",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    report = summary_service.build_summary_report(
        group_by=SummaryGroupBy.CATEGORY_MONTH
    )

    assert report.period_keys == ("2024-01", "2024-03")


def test_build_category_summary_groups_by_top_level(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-25.50"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 17),
        amount=Decimal("-30.00"),
        description="Gas",
        category_id=sample_categories["Transportation > Gas"],
    )
    transaction_service.create_transaction(
        unique_id="TXN004",
        account_id=sample_account.id,
        date=date(2024, 1, 18),
        amount=Decimal("20.00"),
        description="Adjustment",
        category_id=None,
    )

    transactions = summary_service.get_filtered_transactions()
    category_tree = summary_service.get_category_tree(None)
    summaries = summary_service.build_category_summary(
        transactions, category_tree, category_id=None
    )

    food_summary = _find_summary_by_name(summaries, "Food & Dining")
    transport_summary = _find_summary_by_name(summaries, "Transportation")
    uncategorized_summary = _find_summary_by_name(summaries, "Uncategorized")

    assert food_summary is not None
    assert transport_summary is not None
    assert uncategorized_summary is not None

    assert food_summary["expenses"] == pytest.approx(-75.5)
    assert food_summary["income"] == pytest.approx(0.0)
    assert food_summary["count"] == 2

    assert transport_summary["expenses"] == pytest.approx(-30.0)
    assert transport_summary["income"] == pytest.approx(0.0)
    assert transport_summary["count"] == 1

    assert uncategorized_summary["expenses"] == pytest.approx(0.0)
    assert uncategorized_summary["income"] == pytest.approx(20.0)
    assert uncategorized_summary["count"] == 1

    assert _find_summary_by_name(summaries, "Groceries") is None
    assert _find_summary_by_name(summaries, "Coffee & Snacks") is None


def test_build_category_summary_groups_by_immediate_children(
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    summary_service = SummaryService(temp_db)

    produce_id = category_service.create_category(
        name="Produce", parent_path="Food & Dining > Groceries"
    )

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-40.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-10.00"),
        description="Produce",
        category_id=produce_id,
    )
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 17),
        amount=Decimal("-5.00"),
        description="Coffee",
        category_id=sample_categories["Food & Dining > Coffee & Snacks"],
    )
    transaction_service.create_transaction(
        unique_id="TXN004",
        account_id=sample_account.id,
        date=date(2024, 1, 18),
        amount=Decimal("-15.00"),
        description="Parent",
        category_id=sample_categories["Food & Dining"],
    )

    transactions = summary_service.get_filtered_transactions(
        category_path="Food & Dining"
    )
    category_tree = summary_service.get_category_tree("Food & Dining")
    summaries = summary_service.build_category_summary(
        transactions,
        category_tree,
        category_id=sample_categories["Food & Dining"],
    )

    groceries_summary = _find_summary_by_name(summaries, "Groceries")
    coffee_summary = _find_summary_by_name(summaries, "Coffee & Snacks")
    parent_summary = _find_summary_by_name(summaries, "Food & Dining")

    assert groceries_summary is not None
    assert coffee_summary is not None
    assert parent_summary is not None

    assert groceries_summary["expenses"] == pytest.approx(-50.0)
    assert groceries_summary["income"] == pytest.approx(0.0)
    assert groceries_summary["count"] == 2

    assert coffee_summary["expenses"] == pytest.approx(-5.0)
    assert coffee_summary["income"] == pytest.approx(0.0)
    assert coffee_summary["count"] == 1

    assert parent_summary["expenses"] == pytest.approx(-15.0)
    assert parent_summary["income"] == pytest.approx(0.0)
    assert parent_summary["count"] == 1

    assert _find_summary_by_name(summaries, "Transportation") is None


def test_build_category_summary_unknown_category_name_when_missing_tree():
    summary_service = SummaryService(None)

    transactions = [
        Transaction(
            id=1,
            unique_id="TXN001",
            account_id=1,
            date=date(2024, 1, 1),
            amount=Decimal("-10.00"),
            description="Missing",
            reference_number=None,
            category_id=999,
            notes=None,
            imported_at=datetime(2024, 1, 1),
        )
    ]

    summaries = summary_service.build_category_summary(
        transactions, category_tree=[], category_id=999
    )

    assert summaries[0]["category_name"] == "Unknown"
    assert summaries[0]["category_type"] is None
    assert summaries[0]["expenses"] == pytest.approx(-10.0)
    assert summaries[0]["income"] == pytest.approx(0.0)
    assert summaries[0]["count"] == 1


def test_get_filtered_transactions_category_filter_does_not_include_transfers(
    temp_db, sample_account, sample_categories, transaction_service, category_service
):
    summary_service = SummaryService(temp_db)

    transfer_id = category_service.create_category(
        name="Transfer", parent_path=None, category_type=2
    )
    transfer_sub_id = category_service.create_category(
        name="Between Accounts", parent_path="Transfer", category_type=2
    )

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-20.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-100.00"),
        description="Transfer",
        category_id=transfer_sub_id,
    )

    transactions = summary_service.get_filtered_transactions(
        category_path="Food & Dining", include_transfers=False
    )
    assert all(txn.category_id != transfer_sub_id for txn in transactions)

    transactions_with_transfers = summary_service.get_filtered_transactions(
        category_path="Food & Dining", include_transfers=True
    )
    assert all(
        txn.category_id != transfer_sub_id for txn in transactions_with_transfers
    )


def test_get_filtered_transactions_includes_descendants(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-40.00"),
        description="Parent",
        category_id=sample_categories["Food & Dining"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("-15.00"),
        description="Child",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 17),
        amount=Decimal("-10.00"),
        description="Other",
        category_id=sample_categories["Transportation > Gas"],
    )

    transactions = summary_service.get_filtered_transactions(
        category_path="Food & Dining"
    )
    category_ids = {txn.category_id for txn in transactions}

    assert sample_categories["Food & Dining"] in category_ids
    assert sample_categories["Food & Dining > Groceries"] in category_ids
    assert sample_categories["Transportation > Gas"] not in category_ids


def test_build_category_summary_splits_income_and_expenses(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 16),
        amount=Decimal("25.00"),
        description="Refund",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    transactions = summary_service.get_filtered_transactions()
    category_tree = summary_service.get_category_tree(None)
    summaries = summary_service.build_category_summary(
        transactions, category_tree, category_id=None
    )

    food_summary = _find_summary_by_name(summaries, "Food & Dining")
    assert food_summary is not None
    assert food_summary["expenses"] == pytest.approx(-50.0)
    assert food_summary["income"] == pytest.approx(25.0)
    assert food_summary["count"] == 2


def test_build_summary_report_sections_order_and_subtotals(
    temp_db,
    sample_account,
    sample_categories,
    transaction_service,
    category_service,
):
    summary_service = SummaryService(temp_db)

    income_id = category_service.create_category(
        name="Income", parent_path=None, category_type=1
    )

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 10),
        amount=Decimal("100.00"),
        description="Paycheck",
        category_id=income_id,
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 11),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining"],
    )
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 12),
        amount=Decimal("20.00"),
        description="Adjustment",
        category_id=None,
    )

    report = summary_service.build_summary_report(group_by=SummaryGroupBy.CATEGORY)

    income_section = _find_section_by_name(report.sections, "Income")
    expense_section = _find_section_by_name(report.sections, "Expense")

    assert income_section is not None
    assert expense_section is not None
    assert [row.category_name for row in expense_section.rows] == [
        "Food & Dining",
        "Uncategorized",
    ]
    assert income_section.subtotal == pytest.approx(100.0)
    assert expense_section.subtotal == pytest.approx(-30.0)
    assert report.overall_total == pytest.approx(70.0)


def test_build_summary_report_period_sections_include_period_totals(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 10),
        amount=Decimal("-10.00"),
        description="January",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 3, 5),
        amount=Decimal("-20.00"),
        description="March",
        category_id=sample_categories["Food & Dining > Groceries"],
    )

    report = summary_service.build_summary_report(
        group_by=SummaryGroupBy.CATEGORY_MONTH
    )

    expense_section = _find_section_by_name(report.period_sections, "Expense")

    assert expense_section is not None
    assert len(expense_section.rows) == 1
    row = expense_section.rows[0]
    assert row.category_name == "Food & Dining"
    assert row.period_totals["2024-01"] == pytest.approx(-10.0)
    assert row.period_totals["2024-03"] == pytest.approx(-20.0)
    assert report.period_overall_totals["2024-01"] == pytest.approx(-10.0)


def test_build_summary_report_expanded_sections_order_and_uncategorized(
    temp_db, sample_account, sample_categories, transaction_service
):
    summary_service = SummaryService(temp_db)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 10),
        amount=Decimal("-50.00"),
        description="Groceries",
        category_id=sample_categories["Food & Dining > Groceries"],
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 1, 12),
        amount=Decimal("-20.00"),
        description="Gas",
        category_id=sample_categories["Transportation > Gas"],
    )
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 13),
        amount=Decimal("10.00"),
        description="Adjustment",
        category_id=None,
    )

    report = summary_service.build_summary_report(group_by=SummaryGroupBy.CATEGORY)

    expense_section = _find_section_by_name(report.expanded_sections, "Expense")

    assert expense_section is not None
    row_names = [row.category_name for row in expense_section.rows]
    assert row_names[0] == "Food & Dining"
    assert row_names[1] == "Transportation"
    assert row_names[-1] == "Uncategorized"


def test_build_summary_report_period_expanded_sections_uncategorized_last(
    temp_db, sample_account, transaction_service, category_service
):
    summary_service = SummaryService(temp_db)

    misc_id = category_service.create_category(name="Misc", parent_path=None)

    transaction_service.create_transaction(
        unique_id="TXN001",
        account_id=sample_account.id,
        date=date(2024, 1, 10),
        amount=Decimal("-10.00"),
        description="Misc January",
        category_id=misc_id,
    )
    transaction_service.create_transaction(
        unique_id="TXN002",
        account_id=sample_account.id,
        date=date(2024, 2, 10),
        amount=Decimal("-20.00"),
        description="Misc February",
        category_id=misc_id,
    )
    transaction_service.create_transaction(
        unique_id="TXN003",
        account_id=sample_account.id,
        date=date(2024, 1, 12),
        amount=Decimal("5.00"),
        description="Uncategorized",
        category_id=None,
    )

    report = summary_service.build_summary_report(
        group_by=SummaryGroupBy.CATEGORY_MONTH
    )

    expense_section = _find_section_by_name(report.period_expanded_sections, "Expense")
    assert expense_section is not None
    assert expense_section.rows[-1].category_name == "Uncategorized"

    misc_row = next(row for row in expense_section.rows if row.category_name == "Misc")
    assert misc_row.period_totals["2024-01"] == pytest.approx(-10.0)
    assert misc_row.period_totals["2024-02"] == pytest.approx(-20.0)
    assert expense_section.period_subtotals["2024-01"] == pytest.approx(-5.0)
