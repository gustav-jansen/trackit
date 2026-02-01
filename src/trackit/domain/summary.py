"""Summary grouping domain service."""

from datetime import date
from typing import Optional

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
        transactions = self.get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category_path=category_path,
            include_transfers=include_transfers,
        )
        return SummaryReport(
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            groups=(),
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
        transactions: list[Transaction],
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
        period_transactions: list[Transaction],
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
