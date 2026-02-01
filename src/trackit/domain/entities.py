"""Domain model entities for trackit.

These are pure data classes representing business concepts, independent of
database schema. This allows the business logic to remain stable when the
database schema changes (e.g., when switching to double-entry bookkeeping).
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Any


@dataclass(frozen=True)
class Account:
    """Bank account domain entity."""

    id: int
    name: str
    bank_name: str
    created_at: datetime


@dataclass(frozen=True)
class Category:
    """Category domain entity with hierarchical structure."""

    id: int
    name: str
    parent_id: Optional[int]
    created_at: datetime
    category_type: int = 0  # 0=Expense, 1=Income, 2=Transfer


@dataclass(frozen=True)
class CategoryTreeNode:
    """Category tree node domain entity.

    Represents the minimal category tree shape used for hierarchical displays
    while keeping the structure explicit and typed.
    """

    id: int
    name: str
    parent_id: Optional[int]
    category_type: int
    children: tuple["CategoryTreeNode", ...] = ()

    def get(self, key: str, default: Any = None) -> Any:
        """Dictionary-style access for compatibility with existing usage."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        """Allow bracket access for required keys."""
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc


@dataclass(frozen=True)
class Transaction:
    """Transaction domain entity."""

    id: int
    unique_id: str
    account_id: int
    date: date
    amount: Decimal
    description: Optional[str]
    reference_number: Optional[str]
    category_id: Optional[int]
    notes: Optional[str]
    imported_at: datetime


class SummaryGroupBy(str, Enum):
    """Grouping modes for summary reports."""

    CATEGORY = "category"
    CATEGORY_MONTH = "category_month"
    CATEGORY_YEAR = "category_year"


@dataclass(frozen=True)
class SummaryGroup:
    """Grouped transactions for summary views."""

    group_key: str
    category_id: Optional[int]
    category_name: Optional[str]
    category_type: Optional[int]
    period_key: Optional[str]
    transactions: tuple["Transaction", ...]
    children: tuple["SummaryGroup", ...] = ()


@dataclass(frozen=True)
class SummaryReport:
    """Summary grouping report returned by domain services."""

    group_by: SummaryGroupBy
    start_date: Optional[date]
    end_date: Optional[date]
    category_path: Optional[str]
    include_transfers: bool
    transactions: tuple["Transaction", ...]
    period_keys: tuple[str, ...]
    period_transactions_map: dict[str, tuple["Transaction", ...]]
    category_tree: tuple["CategoryTreeNode", ...]
    descendant_map: dict[int, set[int]]
    category_summaries: tuple[dict, ...]
    groups: tuple[SummaryGroup, ...] = ()


@dataclass(frozen=True)
class CSVFormat:
    """CSV format domain entity."""

    id: int
    name: str
    account_id: int
    created_at: datetime
    is_debit_credit_format: bool = False
    negate_debit: bool = False
    negate_credit: bool = False


@dataclass(frozen=True)
class CSVColumnMapping:
    """CSV column mapping domain entity."""

    id: int
    format_id: int
    csv_column_name: str
    db_field_name: str
    is_required: bool
