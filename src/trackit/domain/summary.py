"""Summary grouping domain service."""

from datetime import date
from typing import Optional, Sequence, Any

from trackit.database.base import Database
from trackit.domain.entities import SummaryGroupBy, SummaryReport, Transaction


class SummaryService:
    """Service for building summary grouping models."""

    def __init__(self, db: Database):
        """Initialize summary service.

        Args:
            db: Database instance
        """
        self.db = db

    def group_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        include_transfers: bool = False,
        group_by: SummaryGroupBy = SummaryGroupBy.CATEGORY,
    ) -> SummaryReport:
        """Group transactions for summary views.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            category_path: Optional category path filter
            include_transfers: If True, include transfers in results
            group_by: Grouping mode for the report

        Returns:
            SummaryReport describing grouped transactions
        """
        return self.build_summary_report(
            start_date=start_date,
            end_date=end_date,
            category_path=category_path,
            include_transfers=include_transfers,
            group_by=group_by,
        )

    def build_summary_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        include_transfers: bool = False,
        group_by: SummaryGroupBy = SummaryGroupBy.CATEGORY,
    ) -> SummaryReport:
        """Build a summary report for formatting."""
        transactions = self.get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category_path=category_path,
            include_transfers=include_transfers,
        )

        category_tree = self.get_category_tree(category_path)
        descendant_map = self.build_descendant_map(category_tree)
        category_summaries = self.get_category_summaries(
            start_date=start_date,
            end_date=end_date,
            category_path=category_path,
            include_transfers=include_transfers,
        )

        period_transactions_map: dict[str, tuple[Transaction, ...]] = {}
        period_keys: tuple[str, ...] = ()
        if group_by in (SummaryGroupBy.CATEGORY_MONTH, SummaryGroupBy.CATEGORY_YEAR):
            group_by_month = group_by == SummaryGroupBy.CATEGORY_MONTH
            grouped = self.group_transactions_by_period(transactions, group_by_month)
            period_transactions_map = {
                key: tuple(value) for key, value in grouped.items()
            }
            period_keys = tuple(sorted(period_transactions_map.keys()))

        return SummaryReport(
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            category_path=category_path,
            include_transfers=include_transfers,
            transactions=tuple(transactions),
            period_keys=period_keys,
            period_transactions_map=period_transactions_map,
            category_tree=tuple(category_tree),
            descendant_map=descendant_map,
            category_summaries=tuple(category_summaries),
        )

    def build_category_summary(
        self,
        transactions: Sequence[Transaction],
        category_tree: list[dict],
        category_id: Optional[int],
    ) -> list[dict[str, Any]]:
        """Build category summary from transactions and category tree."""
        category_index, parent_map, children_map = self.build_category_index(
            category_tree
        )
        immediate_children_ids = None
        if category_id is not None:
            immediate_children_ids = set(children_map.get(category_id, set()))

        summary_dict = self.aggregate_transactions_by_group(
            transactions,
            category_id=category_id,
            category_index=category_index,
            parent_map=parent_map,
            immediate_children_ids=immediate_children_ids,
        )
        return self.convert_summary_to_results(
            summary_dict=summary_dict,
            category_id=category_id,
            category_index=category_index,
        )

    def get_filtered_transactions(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        include_transfers: bool = False,
    ) -> list[Transaction]:
        """Get transactions matching summary criteria."""
        category_id = None
        if category_path is not None:
            category = self.db.get_category_by_path(category_path)
            if category is not None:
                category_id = category.id

        return self.db.get_summary_transactions(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            include_transfers=include_transfers,
        )

    def get_category_summaries(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        include_transfers: bool = False,
    ) -> list[dict]:
        """Get category summaries for standard view."""
        category_id = None
        resolved_path = None
        if category_path is not None:
            category = self.db.get_category_by_path(category_path)
            if category is not None:
                category_id = category.id
                resolved_path = category_path

        transactions = self.get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category_path=resolved_path,
            include_transfers=include_transfers,
        )
        category_tree = self.get_category_tree(resolved_path)
        return self.build_category_summary(transactions, category_tree, category_id)

    def get_category_tree(self, category_path: Optional[str]) -> list[dict]:
        """Get category tree, filtered by category path if provided."""
        if not category_path:
            return self.db.get_category_tree()

        category = self.db.get_category_by_path(category_path)
        if category is None:
            return []

        full_tree = self.db.get_category_tree()

        def find_subtree(nodes: list[dict], category_id: int) -> Optional[dict]:
            for node in nodes:
                if node.get("id") == category_id:
                    return node
                child_match = find_subtree(node.get("children", []), category_id)
                if child_match is not None:
                    return child_match
            return None

        subtree = find_subtree(full_tree, category.id)
        return [subtree] if subtree is not None else []

    def build_category_index(
        self, category_tree: list[dict]
    ) -> tuple[
        dict[int, dict[str, Any]], dict[int, Optional[int]], dict[int, set[int]]
    ]:
        """Build lookup maps from a category tree."""
        category_index: dict[int, dict[str, Any]] = {}
        parent_map: dict[int, Optional[int]] = {}
        children_map: dict[int, set[int]] = {}

        def visit(node: dict) -> None:
            category_id = node.get("id")
            if category_id is None:
                return
            category_index[category_id] = {
                "name": node.get("name"),
                "category_type": node.get("category_type"),
            }
            parent_map[category_id] = node.get("parent_id")
            for child in node.get("children", []):
                child_id = child.get("id")
                if child_id is not None:
                    children_map.setdefault(category_id, set()).add(child_id)
                visit(child)

        for root in category_tree or []:
            visit(root)

        return category_index, parent_map, children_map

    def build_descendant_map(self, category_tree: list[dict]) -> dict[int, set[int]]:
        """Build map of category IDs to descendant ID sets."""
        descendant_map: dict[int, set[int]] = {}

        def collect_descendants(node: dict) -> set[int]:
            descendants = {node["id"]}
            for child in node.get("children", []):
                descendants.update(collect_descendants(child))
            descendant_map[node["id"]] = descendants
            return descendants

        for root in category_tree or []:
            collect_descendants(root)

        return descendant_map

    def get_top_level_category_id(
        self,
        category_id: int,
        category_index: dict[int, dict[str, Any]],
        parent_map: dict[int, Optional[int]],
    ) -> Optional[int]:
        """Get top-level category ID for a category in a tree."""
        if category_id not in category_index:
            return None

        current_id = category_id
        while True:
            parent_id = parent_map.get(current_id)
            if parent_id is None:
                return current_id
            current_id = parent_id

    def get_group_id_for_transaction(
        self,
        txn: Transaction,
        category_id: Optional[int],
        category_index: dict[int, dict[str, Any]],
        parent_map: dict[int, Optional[int]],
        immediate_children_ids: Optional[set[int]],
    ) -> Optional[int]:
        """Determine summary group ID for a transaction."""
        if txn.category_id is None:
            return None

        if category_id is None:
            return self.get_top_level_category_id(
                txn.category_id, category_index, parent_map
            )

        if txn.category_id == category_id:
            return category_id

        if immediate_children_ids and txn.category_id in immediate_children_ids:
            return txn.category_id

        current_id = txn.category_id
        while current_id is not None and current_id != category_id:
            parent_id = parent_map.get(current_id)
            if parent_id == category_id:
                return current_id
            if current_id not in category_index:
                break
            current_id = parent_id

        return category_id

    def aggregate_transactions_by_group(
        self,
        transactions: Sequence[Transaction],
        category_id: Optional[int],
        category_index: dict[int, dict[str, Any]],
        parent_map: dict[int, Optional[int]],
        immediate_children_ids: Optional[set[int]],
    ) -> dict[Optional[int], dict[str, Any]]:
        """Aggregate transactions into summary groups."""
        from collections import defaultdict

        summary_dict: dict[Optional[int], dict[str, Any]] = defaultdict(
            lambda: {"expenses": 0.0, "income": 0.0, "count": 0}
        )

        for txn in transactions:
            group_id = self.get_group_id_for_transaction(
                txn,
                category_id=category_id,
                category_index=category_index,
                parent_map=parent_map,
                immediate_children_ids=immediate_children_ids,
            )
            summary_dict[group_id]["expenses"] += float(min(txn.amount, 0))
            summary_dict[group_id]["income"] += float(max(txn.amount, 0))
            summary_dict[group_id]["count"] += 1

        return summary_dict

    def convert_summary_to_results(
        self,
        summary_dict: dict[Optional[int], dict[str, Any]],
        category_id: Optional[int],
        category_index: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert summary groups into result dictionaries."""
        parent_name = None
        if category_id is not None:
            parent_name = category_index.get(category_id, {}).get("name")

        results: list[dict[str, Any]] = []
        for group_id, data in summary_dict.items():
            if group_id is None:
                category_name = "Uncategorized"
            elif category_id is not None and group_id == category_id:
                category_name = parent_name or "Unknown"
            else:
                category_name = category_index.get(group_id, {}).get("name")
                if category_name is None:
                    category_name = (
                        "Uncategorized" if category_id is None else "Unknown"
                    )

            category_type = None
            if group_id is not None:
                category_type = category_index.get(group_id, {}).get("category_type")

            results.append(
                {
                    "category_id": group_id,
                    "category_name": category_name,
                    "category_type": category_type,
                    "expenses": data["expenses"],
                    "income": data["income"],
                    "count": data["count"],
                }
            )

        return results

    def get_category_type(self, category_id: Optional[int]) -> Optional[int]:
        """Get category type for a category ID."""
        if category_id is None:
            return None
        cat = self.db.get_category(category_id)
        return cat.category_type if cat else None

    def group_transactions_by_period(
        self, transactions: list[Transaction], group_by_month: bool
    ) -> dict[str, list[Transaction]]:
        """Group transactions by month or year."""
        from collections import defaultdict

        period_transactions: dict[str, list[Transaction]] = defaultdict(list)

        for txn in transactions:
            if group_by_month:
                period_key = txn.date.strftime("%Y-%m")
            else:
                period_key = txn.date.strftime("%Y")
            period_transactions[period_key].append(txn)

        return dict(period_transactions)

    def calculate_category_total(
        self,
        descendant_map: dict[int, set[int]],
        category_id: Optional[int],
        transactions: Sequence[Transaction],
    ) -> float:
        """Calculate total for a category including all its descendants."""
        if category_id is None:
            return sum(
                float(txn.amount) for txn in transactions if txn.category_id is None
            )

        descendant_ids = descendant_map.get(category_id, {category_id})
        return sum(
            float(txn.amount)
            for txn in transactions
            if txn.category_id in descendant_ids
        )

    def calculate_category_total_for_period(
        self,
        descendant_map: dict[int, set[int]],
        category_id: Optional[int],
        period_transactions: Sequence[Transaction],
    ) -> float:
        """Calculate total for a category in a specific period."""
        if category_id is None:
            return sum(
                float(txn.amount)
                for txn in period_transactions
                if txn.category_id is None
            )

        descendant_ids = descendant_map.get(category_id, {category_id})
        return sum(
            float(txn.amount)
            for txn in period_transactions
            if txn.category_id in descendant_ids
        )
