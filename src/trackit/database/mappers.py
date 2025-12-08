"""Mapper functions to convert between domain models and SQLAlchemy models.

This layer isolates the conversion logic, making it easy to change when
the database schema changes (e.g., when switching to double-entry bookkeeping).
"""

from trackit.domain import entities as domain
from trackit.database.models import (
    Account as ORMAccount,
    Category as ORMCategory,
    Transaction as ORMTransaction,
    CSVFormat as ORMCSVFormat,
    CSVColumnMapping as ORMCSVColumnMapping,
)


def account_to_domain(orm_account: ORMAccount) -> domain.Account:
    """Convert SQLAlchemy Account model to domain Account entity."""
    return domain.Account(
        id=orm_account.id,
        name=orm_account.name,
        bank_name=orm_account.bank_name,
        created_at=orm_account.created_at,
    )


def category_to_domain(orm_category: ORMCategory) -> domain.Category:
    """Convert SQLAlchemy Category model to domain Category entity."""
    return domain.Category(
        id=orm_category.id,
        name=orm_category.name,
        parent_id=orm_category.parent_id,
        created_at=orm_category.created_at,
        category_type=orm_category.category_type,
    )


def transaction_to_domain(orm_transaction: ORMTransaction) -> domain.Transaction:
    """Convert SQLAlchemy Transaction model to domain Transaction entity."""
    return domain.Transaction(
        id=orm_transaction.id,
        unique_id=orm_transaction.unique_id,
        account_id=orm_transaction.account_id,
        date=orm_transaction.date,
        amount=orm_transaction.amount,
        description=orm_transaction.description,
        reference_number=orm_transaction.reference_number,
        category_id=orm_transaction.category_id,
        notes=orm_transaction.notes,
        imported_at=orm_transaction.imported_at,
    )


def csv_format_to_domain(orm_format: ORMCSVFormat) -> domain.CSVFormat:
    """Convert SQLAlchemy CSVFormat model to domain CSVFormat entity."""
    return domain.CSVFormat(
        id=orm_format.id,
        name=orm_format.name,
        account_id=orm_format.account_id,
        created_at=orm_format.created_at,
        is_debit_credit_format=orm_format.is_debit_credit_format,
        negate_debit=orm_format.negate_debit,
        negate_credit=orm_format.negate_credit,
    )


def csv_column_mapping_to_domain(orm_mapping: ORMCSVColumnMapping) -> domain.CSVColumnMapping:
    """Convert SQLAlchemy CSVColumnMapping model to domain CSVColumnMapping entity."""
    return domain.CSVColumnMapping(
        id=orm_mapping.id,
        format_id=orm_mapping.format_id,
        csv_column_name=orm_mapping.csv_column_name,
        db_field_name=orm_mapping.db_field_name,
        is_required=orm_mapping.is_required,
    )
