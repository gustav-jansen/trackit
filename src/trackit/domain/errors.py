"""Shared domain error messages and error types."""


class DomainError(ValueError):
    """Base class for domain-level errors.

    Subclasses provide semantic categories while preserving ValueError
    compatibility for existing error handling.
    """


class ValidationError(DomainError):
    """Invalid input or failed validation in domain logic."""


class NotFoundError(DomainError):
    """Requested domain entity or path does not exist."""


class ConflictError(DomainError):
    """Domain conflict, such as uniqueness violations."""


class DependencyError(DomainError):
    """Operation blocked due to dependent domain data."""


def account_not_found(account_id: int) -> str:
    """Return message for missing account."""
    return f"Account {account_id} not found"


def category_not_found(category_id: int) -> str:
    """Return message for missing category by ID."""
    return f"Category {category_id} not found"


def category_path_not_found(path: str) -> str:
    """Return message for missing category by path."""
    return f"Category '{path}' not found"


def duplicate_transaction_unique_id(unique_id: str, account_id: int) -> str:
    """Return message for duplicate transaction unique ID."""
    return f"Transaction with unique_id '{unique_id}' already exists for account {account_id}"


def account_delete_blocked(
    account_id: int, transaction_count: int, format_count: int
) -> str:
    """Return message when account has dependent transactions or formats."""
    parts = []
    if transaction_count > 0:
        parts.append(
            f"{transaction_count} transaction{'s' if transaction_count != 1 else ''}"
        )
    if format_count > 0:
        parts.append(f"{format_count} CSV format{'s' if format_count != 1 else ''}")
    return (
        f"Cannot delete account {account_id}: it has {', '.join(parts)}. "
        "Please reassign or delete them first."
    )
