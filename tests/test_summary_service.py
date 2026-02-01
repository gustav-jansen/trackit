"""Tests for summary domain service helpers."""

from datetime import date
from decimal import Decimal

import pytest

from trackit.domain.summary import SummaryService
from trackit.domain.entities import SummaryGroupBy


def _find_node_by_name(nodes, name):
    for node in nodes:
        if node.get("name") == name:
            return node
        child_match = _find_node_by_name(node.get("children", []), name)
        if child_match is not None:
            return child_match
    return None


def _flatten_names(nodes):
    names = []
    for node in nodes:
        names.append(node.get("name"))
        names.extend(_flatten_names(node.get("children", [])))
    return names


def test_build_descendant_map_includes_children(temp_db, sample_categories):
    summary_service = SummaryService(temp_db)
    category_tree = summary_service.get_category_tree(None)
    descendant_map = summary_service.build_descendant_map(category_tree)

    parent_node = _find_node_by_name(category_tree, "Food & Dining")
    child_node = _find_node_by_name(category_tree, "Groceries")

    assert parent_node is not None
    assert child_node is not None
    parent_id = parent_node["id"]
    child_id = child_node["id"]

    assert parent_id in descendant_map
    assert parent_id in descendant_map[parent_id]
    assert child_id in descendant_map[parent_id]


def test_get_category_tree_with_filter(temp_db, sample_categories):
    summary_service = SummaryService(temp_db)

    category_tree = summary_service.get_category_tree("Food & Dining")
    assert len(category_tree) == 1
    assert category_tree[0].get("name") == "Food & Dining"

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

    assert report.transactions == ()
    assert report.category_tree == ()
    assert report.category_summaries == ()


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
