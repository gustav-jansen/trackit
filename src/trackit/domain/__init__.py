"""Domain layer for trackit application."""

# Import entities directly (no dependencies)
from trackit.domain import entities


# Lazy imports for services to avoid circular dependencies
def __getattr__(name):
    if name == "TransactionService":
        from trackit.domain.transaction import TransactionService

        return TransactionService
    elif name == "CategoryService":
        from trackit.domain.category import CategoryService

        return CategoryService
    elif name == "CSVImportService":
        from trackit.domain.csv_import import CSVImportService

        return CSVImportService
    elif name == "AccountService":
        from trackit.domain.account import AccountService

        return AccountService
    elif name == "CSVFormatService":
        from trackit.domain.csv_format import CSVFormatService

        return CSVFormatService
    elif name == "SummaryService":
        from trackit.domain.summary import SummaryService

        return SummaryService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "entities",
    "TransactionService",
    "CategoryService",
    "CSVImportService",
    "AccountService",
    "CSVFormatService",
    "SummaryService",
]
