"""CSV format domain service."""

from typing import Optional
from trackit.database.base import Database
from trackit.domain.entities import (
    CSVFormat as CSVFormatEntity,
    CSVColumnMapping as CSVColumnMappingEntity,
)


class CSVFormatService:
    """Service for managing CSV formats."""

    def __init__(self, db: Database):
        """Initialize CSV format service.

        Args:
            db: Database instance
        """
        self.db = db

    def create_format(self, name: str, account_id: int) -> int:
        """Create a new CSV format.

        Args:
            name: Format name
            account_id: Associated account ID

        Returns:
            Format ID

        Raises:
            ValueError: If format name already exists or account doesn't exist
        """
        # Verify account exists
        account = self.db.get_account(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")

        # Check if format with same name exists
        existing = self.db.get_csv_format_by_name(name)
        if existing is not None:
            raise ValueError(f"CSV format with name '{name}' already exists")

        return self.db.create_csv_format(name=name, account_id=account_id)

    def get_format(self, format_id: int) -> Optional[CSVFormatEntity]:
        """Get CSV format by ID.

        Args:
            format_id: Format ID

        Returns:
            Format entity or None if not found
        """
        return self.db.get_csv_format(format_id)

    def get_format_by_name(self, name: str) -> Optional[CSVFormatEntity]:
        """Get CSV format by name.

        Args:
            name: Format name

        Returns:
            Format entity or None if not found
        """
        return self.db.get_csv_format_by_name(name)

    def list_formats(self, account_id: Optional[int] = None) -> list[CSVFormatEntity]:
        """List CSV formats.

        Args:
            account_id: Optional account ID to filter by

        Returns:
            List of format entities
        """
        return self.db.list_csv_formats(account_id=account_id)

    def add_mapping(
        self, format_id: int, csv_column_name: str, db_field_name: str, is_required: bool = False
    ) -> int:
        """Add a column mapping to a format.

        Args:
            format_id: Format ID
            csv_column_name: Column name in CSV file
            db_field_name: Database field name (unique_id, date, amount, etc.)
            is_required: Whether this mapping is required

        Returns:
            Mapping ID

        Raises:
            ValueError: If format doesn't exist or invalid db_field_name
        """
        # Verify format exists
        fmt = self.db.get_csv_format(format_id)
        if fmt is None:
            raise ValueError(f"CSV format {format_id} not found")

        # Validate db_field_name
        valid_fields = {
            "unique_id",
            "date",
            "amount",
            "description",
            "reference_number",
            "account_name",
        }
        if db_field_name not in valid_fields:
            raise ValueError(
                f"Invalid db_field_name '{db_field_name}'. "
                f"Must be one of: {', '.join(sorted(valid_fields))}"
            )

        return self.db.add_column_mapping(
            format_id=format_id,
            csv_column_name=csv_column_name,
            db_field_name=db_field_name,
            is_required=is_required,
        )

    def get_mappings(self, format_id: int) -> list[CSVColumnMappingEntity]:
        """Get all column mappings for a format.

        Args:
            format_id: Format ID

        Returns:
            List of mapping entities
        """
        return self.db.get_column_mappings(format_id)

    def validate_format(self, format_id: int) -> tuple[bool, list[str]]:
        """Validate that a format has all required mappings.

        Args:
            format_id: Format ID

        Returns:
            Tuple of (is_valid, list of missing required fields)

        Note:
            account_name is not required as it comes from the format's account_id,
            not from the CSV file.
            unique_id is optional - if not provided, it will be generated from
            date, description, and amount.
        """
        mappings = self.get_mappings(format_id)
        mapped_fields = {m.db_field_name for m in mappings}

        required_fields = {"date", "amount"}
        missing = required_fields - mapped_fields

        return (len(missing) == 0, list(missing))

    def update_format(
        self, format_id: int, name: Optional[str] = None, account_id: Optional[int] = None
    ) -> None:
        """Update CSV format fields.

        Args:
            format_id: Format ID to update
            name: Optional new format name
            account_id: Optional new account ID

        Raises:
            ValueError: If format not found, name already exists, or account doesn't exist
        """
        # Verify format exists
        fmt = self.db.get_csv_format(format_id)
        if fmt is None:
            raise ValueError(f"CSV format {format_id} not found")

        # Check for duplicate name if updating name
        if name is not None:
            existing = self.db.get_csv_format_by_name(name)
            if existing is not None and existing.id != format_id:
                raise ValueError(f"CSV format with name '{name}' already exists")

        # Verify account if provided
        if account_id is not None:
            account = self.db.get_account(account_id)
            if account is None:
                raise ValueError(f"Account {account_id} not found")

        self.db.update_csv_format(format_id=format_id, name=name, account_id=account_id)

    def delete_format(self, format_id: int) -> None:
        """Delete a CSV format.

        Args:
            format_id: Format ID to delete

        Raises:
            ValueError: If format doesn't exist
        """
        # Verify format exists
        fmt = self.db.get_csv_format(format_id)
        if fmt is None:
            raise ValueError(f"CSV format {format_id} not found")

        self.db.delete_csv_format(format_id)

