"""Summary grouping domain service."""

from datetime import date
from typing import Optional

from trackit.database.base import Database
from trackit.domain.entities import SummaryGroupBy, SummaryReport


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
        raise NotImplementedError("Summary grouping not implemented yet")
