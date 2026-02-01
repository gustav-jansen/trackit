"""Summary grouping domain service."""

from datetime import date
from typing import Optional, Sequence, Any

from trackit.database.base import Database
from trackit.domain.entities import (
    SummaryGroupBy,
    SummaryReport,
    Transaction,
    CategoryTreeNode,
    SummaryCategoryFilter,
    SummaryRow,
    SummarySection,
)


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
        category_filter = self.resolve_category_filter(category_path)
        if category_filter.is_missing:
            return SummaryReport(
                group_by=group_by,
                start_date=start_date,
                end_date=end_date,
                category_path=category_path,
                include_transfers=include_transfers,
                category_filter=category_filter,
                transactions=(),
                period_keys=(),
                period_transactions_map={},
                category_tree=(),
                descendant_map={},
                category_summaries=(),
                sections=(),
                period_sections=(),
                expanded_sections=(),
                period_expanded_sections=(),
                overall_total=0.0,
                period_overall_totals={},
            )

        transactions = self.get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category_path=category_filter.resolved_path,
            include_transfers=include_transfers,
        )

        category_tree = self.get_category_tree(category_filter.resolved_path)
        descendant_map = self.build_descendant_map(category_tree)
        category_summaries = self.get_category_summaries(
            start_date=start_date,
            end_date=end_date,
            category_path=category_filter.resolved_path,
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

        overall_total = sum(float(txn.amount) for txn in transactions)
        period_overall_totals = self.calculate_period_overall_totals(
            period_keys, period_transactions_map
        )
        sections = self.build_summary_sections(category_summaries, include_transfers)
        period_sections = ()
        period_expanded_sections = ()
        if period_keys:
            period_sections = self.build_period_summary_sections(
                category_summaries=category_summaries,
                period_keys=period_keys,
                period_transactions_map=period_transactions_map,
                descendant_map=descendant_map,
                include_transfers=include_transfers,
            )
            period_expanded_sections = self.build_period_expanded_sections(
                category_tree=category_tree,
                transactions=transactions,
                period_keys=period_keys,
                period_transactions_map=period_transactions_map,
                descendant_map=descendant_map,
                include_transfers=include_transfers,
            )
        expanded_sections = self.build_expanded_sections(
            category_tree=category_tree,
            transactions=transactions,
            descendant_map=descendant_map,
            include_transfers=include_transfers,
        )

        return SummaryReport(
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            category_path=category_path,
            include_transfers=include_transfers,
            category_filter=category_filter,
            transactions=tuple(transactions),
            period_keys=period_keys,
            period_transactions_map=period_transactions_map,
            category_tree=tuple(category_tree),
            descendant_map=descendant_map,
            category_summaries=tuple(category_summaries),
            sections=sections,
            period_sections=period_sections,
            expanded_sections=expanded_sections,
            period_expanded_sections=period_expanded_sections,
            overall_total=overall_total,
            period_overall_totals=period_overall_totals,
        )

    def resolve_category_filter(
        self, category_path: Optional[str]
    ) -> SummaryCategoryFilter:
        """Resolve category filters for summary reports."""
        if category_path is None:
            return SummaryCategoryFilter(
                requested_path=None,
                resolved_path=None,
                category_id=None,
                is_missing=False,
            )

        category = self.db.get_category_by_path(category_path)
        if category is None:
            return SummaryCategoryFilter(
                requested_path=category_path,
                resolved_path=None,
                category_id=None,
                is_missing=True,
            )

        return SummaryCategoryFilter(
            requested_path=category_path,
            resolved_path=category_path,
            category_id=category.id,
            is_missing=False,
        )

    def build_category_summary(
        self,
        transactions: Sequence[Transaction],
        category_tree: list[CategoryTreeNode],
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
        category_filter = self.resolve_category_filter(category_path)
        if category_filter.is_missing:
            return []

        transactions = self.db.list_transactions(
            start_date=start_date,
            end_date=end_date,
        )

        if not transactions:
            return []

        category_tree = self.db.get_category_tree()
        descendant_map = self.build_descendant_map(category_tree)

        if category_filter.category_id is not None:
            descendant_ids = descendant_map.get(
                category_filter.category_id, {category_filter.category_id}
            )
            transactions = [
                txn for txn in transactions if txn.category_id in descendant_ids
            ]

        if not include_transfers:
            transfer_ids = self.get_transfer_category_ids(category_tree, descendant_map)
            if transfer_ids:
                transactions = [
                    txn
                    for txn in transactions
                    if txn.category_id is None or txn.category_id not in transfer_ids
                ]

        return transactions

    def get_category_summaries(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_path: Optional[str] = None,
        include_transfers: bool = False,
    ) -> list[dict]:
        """Get category summaries for standard view."""
        category_filter = self.resolve_category_filter(category_path)
        if category_filter.is_missing:
            return []

        transactions = self.get_filtered_transactions(
            start_date=start_date,
            end_date=end_date,
            category_path=category_filter.resolved_path,
            include_transfers=include_transfers,
        )
        category_tree = self.get_category_tree(category_filter.resolved_path)
        return self.build_category_summary(
            transactions, category_tree, category_filter.category_id
        )

    def get_category_tree(self, category_path: Optional[str]) -> list[CategoryTreeNode]:
        """Get category tree, filtered by category path if provided."""
        if not category_path:
            return self.db.get_category_tree()

        category = self.db.get_category_by_path(category_path)
        if category is None:
            return []

        full_tree = self.db.get_category_tree()

        def find_subtree(
            nodes: list[CategoryTreeNode], category_id: int
        ) -> Optional[CategoryTreeNode]:
            for node in nodes:
                if node.id == category_id:
                    return node
                child_match = find_subtree(list(node.children), category_id)
                if child_match is not None:
                    return child_match
            return None

        subtree = find_subtree(full_tree, category.id)
        return [subtree] if subtree is not None else []

    def get_transfer_category_ids(
        self,
        category_tree: list[CategoryTreeNode],
        descendant_map: dict[int, set[int]],
    ) -> set[int]:
        """Collect transfer category IDs including descendants."""
        transfer_ids: set[int] = set()

        def visit(node: CategoryTreeNode) -> None:
            if node.category_type == 2:
                transfer_ids.update(descendant_map.get(node.id, {node.id}))
                return
            for child in node.children:
                visit(child)

        for root in category_tree or []:
            visit(root)

        return transfer_ids

    def build_category_index(
        self, category_tree: list[CategoryTreeNode]
    ) -> tuple[
        dict[int, dict[str, Any]], dict[int, Optional[int]], dict[int, set[int]]
    ]:
        """Build lookup maps from a category tree."""
        category_index: dict[int, dict[str, Any]] = {}
        parent_map: dict[int, Optional[int]] = {}
        children_map: dict[int, set[int]] = {}

        def visit(node: CategoryTreeNode) -> None:
            category_index[node.id] = {
                "name": node.name,
                "category_type": node.category_type,
            }
            parent_map[node.id] = node.parent_id
            for child in node.children:
                children_map.setdefault(node.id, set()).add(child.id)
                visit(child)

        for root in category_tree or []:
            visit(root)

        return category_index, parent_map, children_map

    def build_descendant_map(
        self, category_tree: list[CategoryTreeNode]
    ) -> dict[int, set[int]]:
        """Build map of category IDs to descendant ID sets."""
        descendant_map: dict[int, set[int]] = {}

        def collect_descendants(node: CategoryTreeNode) -> set[int]:
            descendants = {node.id}
            for child in node.children:
                descendants.update(collect_descendants(child))
            descendant_map[node.id] = descendants
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

    def calculate_period_overall_totals(
        self,
        period_keys: Sequence[str],
        period_transactions_map: dict[str, tuple[Transaction, ...]],
    ) -> dict[str, float]:
        """Calculate overall totals per period key."""
        return {
            period_key: sum(
                float(txn.amount) for txn in period_transactions_map.get(period_key, ())
            )
            for period_key in period_keys
        }

    def build_summary_sections(
        self, category_summaries: Sequence[dict], include_transfers: bool
    ) -> tuple[SummarySection, ...]:
        """Build ordered summary sections for standard views."""
        buckets: dict[str, list[SummaryRow]] = {
            "income": [],
            "transfer": [],
            "expense": [],
        }

        for summary in category_summaries:
            total = summary.get("expenses", 0.0) + summary.get("income", 0.0)
            if total == 0:
                continue

            category_name = summary.get("category_name") or "Uncategorized"
            category_type = summary.get("category_type")
            row = SummaryRow(
                category_id=summary.get("category_id"),
                category_name=category_name,
                category_type=category_type,
                total=total,
                income=summary.get("income", 0.0),
                expenses=summary.get("expenses", 0.0),
                count=summary.get("count", 0),
            )
            bucket = self.resolve_section_bucket(category_type, include_transfers)
            buckets[bucket].append(row)

        return self.finalize_sections(buckets)

    def build_period_summary_sections(
        self,
        category_summaries: Sequence[dict],
        period_keys: Sequence[str],
        period_transactions_map: dict[str, tuple[Transaction, ...]],
        descendant_map: dict[int, set[int]],
        include_transfers: bool,
    ) -> tuple[SummarySection, ...]:
        """Build ordered summary sections for period grouping."""
        buckets: dict[str, list[SummaryRow]] = {
            "income": [],
            "transfer": [],
            "expense": [],
        }

        for summary in category_summaries:
            category_id = summary.get("category_id")
            period_totals = {
                period_key: self.calculate_category_total_for_period(
                    descendant_map,
                    category_id,
                    period_transactions_map.get(period_key, ()),
                )
                for period_key in period_keys
            }
            total = sum(period_totals.values())
            if total == 0:
                continue

            category_name = summary.get("category_name") or "Uncategorized"
            category_type = summary.get("category_type")
            row = SummaryRow(
                category_id=category_id,
                category_name=category_name,
                category_type=category_type,
                total=total,
                income=summary.get("income", 0.0),
                expenses=summary.get("expenses", 0.0),
                count=summary.get("count", 0),
                period_totals=period_totals,
            )
            bucket = self.resolve_section_bucket(category_type, include_transfers)
            buckets[bucket].append(row)

        return self.finalize_sections(buckets, period_keys=period_keys)

    def build_expanded_sections(
        self,
        category_tree: Sequence[CategoryTreeNode],
        transactions: Sequence[Transaction],
        descendant_map: dict[int, set[int]],
        include_transfers: bool,
    ) -> tuple[SummarySection, ...]:
        """Build ordered summary sections for expanded views."""
        buckets: dict[str, list[SummaryRow]] = {
            "income": [],
            "transfer": [],
            "expense": [],
        }

        for node in category_tree or []:
            resolved_type = self.resolve_category_type(node)
            row = self.build_expanded_tree_row(
                node=node,
                transactions=transactions,
                descendant_map=descendant_map,
            )
            if row is None:
                continue
            bucket = self.resolve_section_bucket(resolved_type, include_transfers)
            buckets[bucket].append(row)

        for bucket_rows in buckets.values():
            bucket_rows.sort(key=lambda row: (-abs(row.total), row.category_name))

        uncategorized_row = self.build_uncategorized_row(
            transactions=transactions,
            descendant_map=descendant_map,
        )
        return self.finalize_sections(
            buckets, uncategorized_row=uncategorized_row, include_tree_order=True
        )

    def build_period_expanded_sections(
        self,
        category_tree: Sequence[CategoryTreeNode],
        transactions: Sequence[Transaction],
        period_keys: Sequence[str],
        period_transactions_map: dict[str, tuple[Transaction, ...]],
        descendant_map: dict[int, set[int]],
        include_transfers: bool,
    ) -> tuple[SummarySection, ...]:
        """Build ordered summary sections for expanded period views."""
        buckets: dict[str, list[SummaryRow]] = {
            "income": [],
            "transfer": [],
            "expense": [],
        }

        for node in category_tree or []:
            resolved_type = self.resolve_category_type(node)
            row = self.build_period_expanded_tree_row(
                node=node,
                transactions=transactions,
                period_keys=period_keys,
                period_transactions_map=period_transactions_map,
                descendant_map=descendant_map,
            )
            if row is None:
                continue
            bucket = self.resolve_section_bucket(resolved_type, include_transfers)
            buckets[bucket].append(row)

        for bucket_rows in buckets.values():
            bucket_rows.sort(key=lambda row: (-abs(row.total), row.category_name))

        uncategorized_row = self.build_period_uncategorized_row(
            transactions=transactions,
            period_keys=period_keys,
            period_transactions_map=period_transactions_map,
            descendant_map=descendant_map,
        )
        return self.finalize_sections(
            buckets,
            period_keys=period_keys,
            uncategorized_row=uncategorized_row,
            include_tree_order=True,
            include_children_in_period_subtotals=True,
        )

    def resolve_section_bucket(
        self, category_type: Optional[int], include_transfers: bool
    ) -> str:
        """Resolve section bucket for a category type."""
        if category_type == 1:
            return "income"
        if category_type == 2 and include_transfers:
            return "transfer"
        return "expense"

    def resolve_category_type(self, node: CategoryTreeNode) -> Optional[int]:
        """Resolve category type for a tree node."""
        if node.category_type is not None:
            return node.category_type
        if self.db is None:
            return None
        return self.get_category_type(node.id)

    def calculate_category_stats(
        self,
        descendant_map: dict[int, set[int]],
        category_id: Optional[int],
        transactions: Sequence[Transaction],
    ) -> tuple[float, float, int, float]:
        """Calculate income, expenses, count, and total for a category."""
        if category_id is None:
            matching = [txn for txn in transactions if txn.category_id is None]
        else:
            descendant_ids = descendant_map.get(category_id, {category_id})
            matching = [
                txn for txn in transactions if txn.category_id in descendant_ids
            ]

        income = sum(float(txn.amount) for txn in matching if txn.amount > 0)
        expenses = sum(float(txn.amount) for txn in matching if txn.amount < 0)
        count = len(matching)
        total = income + expenses
        return income, expenses, count, total

    def build_expanded_tree_row(
        self,
        node: CategoryTreeNode,
        transactions: Sequence[Transaction],
        descendant_map: dict[int, set[int]],
    ) -> Optional[SummaryRow]:
        """Build a summary row for expanded trees."""
        income, expenses, count, total = self.calculate_category_stats(
            descendant_map, node.id, transactions
        )
        if total == 0:
            return None

        children = self.build_expanded_tree_rows(
            nodes=node.children,
            transactions=transactions,
            descendant_map=descendant_map,
        )
        category_type = self.resolve_category_type(node)
        return SummaryRow(
            category_id=node.id,
            category_name=node.name,
            category_type=category_type,
            total=total,
            income=income,
            expenses=expenses,
            count=count,
            children=children,
        )

    def build_expanded_tree_rows(
        self,
        nodes: Sequence[CategoryTreeNode],
        transactions: Sequence[Transaction],
        descendant_map: dict[int, set[int]],
    ) -> tuple[SummaryRow, ...]:
        """Build ordered tree rows for expanded views."""
        rows: list[SummaryRow] = []
        for node in nodes or []:
            row = self.build_expanded_tree_row(
                node=node,
                transactions=transactions,
                descendant_map=descendant_map,
            )
            if row is not None:
                rows.append(row)

        rows.sort(key=lambda row: (-abs(row.total), row.category_name))
        return tuple(rows)

    def build_period_expanded_tree_row(
        self,
        node: CategoryTreeNode,
        transactions: Sequence[Transaction],
        period_keys: Sequence[str],
        period_transactions_map: dict[str, tuple[Transaction, ...]],
        descendant_map: dict[int, set[int]],
    ) -> Optional[SummaryRow]:
        """Build a summary row for expanded period trees."""
        period_totals = {
            period_key: self.calculate_category_total_for_period(
                descendant_map,
                node.id,
                period_transactions_map.get(period_key, ()),
            )
            for period_key in period_keys
        }
        total = sum(period_totals.values())
        if total == 0:
            return None

        income, expenses, count, _ = self.calculate_category_stats(
            descendant_map, node.id, transactions
        )
        children = self.build_period_expanded_tree_rows(
            nodes=node.children,
            transactions=transactions,
            period_keys=period_keys,
            period_transactions_map=period_transactions_map,
            descendant_map=descendant_map,
        )
        category_type = self.resolve_category_type(node)
        return SummaryRow(
            category_id=node.id,
            category_name=node.name,
            category_type=category_type,
            total=total,
            income=income,
            expenses=expenses,
            count=count,
            period_totals=period_totals,
            children=children,
        )

    def build_period_expanded_tree_rows(
        self,
        nodes: Sequence[CategoryTreeNode],
        transactions: Sequence[Transaction],
        period_keys: Sequence[str],
        period_transactions_map: dict[str, tuple[Transaction, ...]],
        descendant_map: dict[int, set[int]],
    ) -> tuple[SummaryRow, ...]:
        """Build ordered tree rows for expanded period views."""
        rows: list[SummaryRow] = []
        for node in nodes or []:
            row = self.build_period_expanded_tree_row(
                node=node,
                transactions=transactions,
                period_keys=period_keys,
                period_transactions_map=period_transactions_map,
                descendant_map=descendant_map,
            )
            if row is not None:
                rows.append(row)

        rows.sort(key=lambda row: (-abs(row.total), row.category_name))
        return tuple(rows)

    def build_uncategorized_row(
        self,
        transactions: Sequence[Transaction],
        descendant_map: dict[int, set[int]],
    ) -> Optional[SummaryRow]:
        """Build uncategorized row for expanded summary views."""
        income, expenses, count, total = self.calculate_category_stats(
            descendant_map, None, transactions
        )
        if total == 0:
            return None

        return SummaryRow(
            category_id=None,
            category_name="Uncategorized",
            category_type=None,
            total=total,
            income=income,
            expenses=expenses,
            count=count,
        )

    def build_period_uncategorized_row(
        self,
        transactions: Sequence[Transaction],
        period_keys: Sequence[str],
        period_transactions_map: dict[str, tuple[Transaction, ...]],
        descendant_map: dict[int, set[int]],
    ) -> Optional[SummaryRow]:
        """Build uncategorized row for expanded period summary views."""
        period_totals = {
            period_key: self.calculate_category_total_for_period(
                descendant_map,
                None,
                period_transactions_map.get(period_key, ()),
            )
            for period_key in period_keys
        }
        total = sum(period_totals.values())
        if total == 0:
            return None

        income, expenses, count, _ = self.calculate_category_stats(
            descendant_map, None, transactions
        )
        return SummaryRow(
            category_id=None,
            category_name="Uncategorized",
            category_type=None,
            total=total,
            income=income,
            expenses=expenses,
            count=count,
            period_totals=period_totals,
        )

    def finalize_sections(
        self,
        buckets: dict[str, list[SummaryRow]],
        period_keys: Optional[Sequence[str]] = None,
        uncategorized_row: Optional[SummaryRow] = None,
        include_tree_order: bool = False,
        include_children_in_period_subtotals: bool = False,
    ) -> tuple[SummarySection, ...]:
        """Finalize section ordering and subtotals."""
        period_keys = tuple(period_keys or ())
        section_definitions = (
            ("Income", "income", 1),
            ("Transfer", "transfer", 2),
            ("Expense", "expense", 0),
        )

        sections: list[SummarySection] = []
        for name, bucket, category_type in section_definitions:
            rows = list(buckets.get(bucket, []))
            if not include_tree_order:
                rows.sort(key=lambda row: (-abs(row.total), row.category_name))

            if bucket == "expense" and uncategorized_row is not None:
                rows.append(uncategorized_row)

            if not rows:
                continue

            period_subtotals: dict[str, float] = {}
            if period_keys:
                if include_children_in_period_subtotals:
                    period_subtotals = self.sum_period_totals_from_rows(
                        rows, period_keys
                    )
                else:
                    period_subtotals = {
                        period_key: sum(
                            row.period_totals.get(period_key, 0.0) for row in rows
                        )
                        for period_key in period_keys
                    }

            subtotal = sum(row.total for row in rows)
            sections.append(
                SummarySection(
                    name=name,
                    category_type=category_type,
                    rows=tuple(rows),
                    subtotal=subtotal,
                    period_subtotals=period_subtotals,
                )
            )

        return tuple(sections)

    def sum_period_totals_from_rows(
        self, rows: Sequence[SummaryRow], period_keys: Sequence[str]
    ) -> dict[str, float]:
        """Sum period totals for rows, including nested children."""
        totals: dict[str, float] = {period_key: 0.0 for period_key in period_keys}

        for row in rows:
            for period_key in period_keys:
                totals[period_key] += row.period_totals.get(period_key, 0.0)
            if row.children:
                child_totals = self.sum_period_totals_from_rows(
                    row.children, period_keys
                )
                for period_key in period_keys:
                    totals[period_key] += child_totals.get(period_key, 0.0)

        return totals
