"""Domain model entities for trackit.

These are pure data classes representing business concepts, independent of
database schema. This allows the business logic to remain stable when the
database schema changes (e.g., when switching to double-entry bookkeeping).
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


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
