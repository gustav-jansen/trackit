"""CSV import domain service."""

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from trackit.database.base import Database
from trackit.domain.transaction import TransactionService
from trackit.domain.account import AccountService
from trackit.domain.csv_format import CSVFormatService
from trackit.domain.errors import DomainError, NotFoundError, ValidationError
from trackit.utils.date_parser import parse_date
from trackit.utils.amount_parser import parse_amount


@dataclass
class SkippedTransaction:
    """Details for a skipped CSV transaction."""

    row_num: int
    reason: str
    details: dict[str, str]


@dataclass
class ImportResult:
    """Structured result for CSV import."""

    imported: int = 0
    skipped: int = 0
    skipped_details: list[SkippedTransaction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a dict representation for CLI compatibility."""
        return {
            "imported": self.imported,
            "skipped": self.skipped,
            "skipped_details": [
                {
                    "row_num": skipped.row_num,
                    "reason": skipped.reason,
                    "details": skipped.details,
                }
                for skipped in self.skipped_details
            ],
            "errors": self.errors,
        }


class CSVImportService:
    """Service for importing CSV files."""

    def __init__(self, db: Database):
        """Initialize CSV import service.

        Args:
            db: Database instance
        """
        self.db = db
        self.transaction_service = TransactionService(db)
        self.account_service = AccountService(db)
        self.format_service = CSVFormatService(db)

    def _generate_unique_id(self, date: date, description: str, amount: Decimal) -> str:
        """Generate a unique transaction ID from date, description, and amount.

        Args:
            date: Transaction date
            description: Transaction description
            amount: Transaction amount

        Returns:
            Deterministic hash-based unique ID
        """
        # Create a deterministic string from the transaction fields
        # Use | as separator to avoid collisions
        id_string = f"{date.isoformat()}|{description}|{amount}"
        # Generate SHA256 hash and use first 32 characters (64 hex chars = 32 bytes)
        return hashlib.sha256(id_string.encode()).hexdigest()

    def import_csv(self, csv_file_path: str, format_name: str) -> dict[str, Any]:
        """Import transactions from a CSV file.

        Args:
            csv_file_path: Path to CSV file
            format_name: Name of CSV format to use

        Returns:
            Dict with import statistics:
            - imported: number of transactions imported
            - skipped: number of transactions skipped (duplicates)
            - skipped_details: list of dicts with skipped transaction details
            - errors: list of error messages

        Raises:
            ValueError: If format doesn't exist or is invalid
            FileNotFoundError: If CSV file doesn't exist
        """
        # Get format
        fmt = self.format_service.get_format_by_name(format_name)
        if fmt is None:
            raise NotFoundError(f"CSV format '{format_name}' not found")

        # Validate format
        is_valid, missing = self.format_service.validate_format(fmt.id)
        if not is_valid:
            raise ValidationError(
                f"CSV format '{format_name}' is missing required mappings: {', '.join(missing)}"
            )

        # Get mappings
        mappings = self.format_service.get_mappings(fmt.id)
        column_map = {m.csv_column_name: m.db_field_name for m in mappings}

        # Read CSV file
        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        result = ImportResult()

        # Check if unique_id is mapped
        has_unique_id_mapping = "unique_id" in column_map.values()

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(f, delimiter=delimiter)

            # Validate required columns exist
            csv_columns = reader.fieldnames
            if csv_columns is None:
                raise ValidationError("CSV file has no columns")

            # Determine required columns based on format type
            if fmt.is_debit_credit_format:
                required_fields = {"date", "debit", "credit"}
            else:
                required_fields = {"date", "amount"}

            required_csv_columns = {
                col for col, field in column_map.items() if field in required_fields
            }
            missing_columns = required_csv_columns - set(csv_columns)
            if missing_columns:
                raise ValidationError(
                    f"CSV file missing required columns: {', '.join(missing_columns)}"
                )

            # Process each row
            for row_num, row in enumerate(
                reader, start=2
            ):  # Start at 2 (header is row 1)
                try:
                    # Extract values using mappings
                    values = {}
                    for csv_col, db_field in column_map.items():
                        if csv_col in row:
                            values[db_field] = (
                                row[csv_col].strip() if row[csv_col] else None
                            )
                        else:
                            values[db_field] = None

                    # Get unique_id if mapped, otherwise generate it
                    unique_id = values.get("unique_id")
                    if not unique_id and has_unique_id_mapping:
                        result.errors.append(f"Row {row_num}: Missing unique_id")
                        continue

                    date_str = values.get("date")
                    if not date_str:
                        result.errors.append(f"Row {row_num}: Missing date")
                        continue

                    # Parse date
                    try:
                        txn_date = parse_date(date_str)
                    except ValueError as e:
                        result.errors.append(f"Row {row_num}: {e}")
                        continue

                    # Handle amount based on format type
                    if fmt.is_debit_credit_format:
                        # Debit/credit format: read from both columns
                        debit_str = values.get("debit")
                        credit_str = values.get("credit")
                        debit_value = debit_str if isinstance(debit_str, str) else None
                        credit_value = (
                            credit_str if isinstance(credit_str, str) else None
                        )

                        # Check that exactly one has a value
                        has_debit = (
                            debit_value is not None and debit_value.strip() != ""
                        )
                        has_credit = (
                            credit_value is not None and credit_value.strip() != ""
                        )

                        if not has_debit and not has_credit:
                            result.errors.append(
                                f"Row {row_num}: Missing both debit and credit values (exactly one required)"
                            )
                            continue

                        if has_debit and has_credit:
                            result.errors.append(
                                f"Row {row_num}: Both debit and credit have values (exactly one required)"
                            )
                            continue

                        # Parse the value that exists
                        if has_debit and debit_value is not None:
                            try:
                                debit_amount = parse_amount(debit_value)
                                # Apply negation if configured
                                amount = (
                                    -debit_amount if fmt.negate_debit else debit_amount
                                )
                            except ValueError as e:
                                result.errors.append(
                                    f"Row {row_num}: Invalid debit value: {e}"
                                )
                                continue
                        else:  # has_credit
                            try:
                                if credit_value is None:
                                    result.errors.append(
                                        f"Row {row_num}: Missing credit value"
                                    )
                                    continue
                                credit_amount = parse_amount(credit_value)
                                # Apply negation if configured
                                amount = (
                                    -credit_amount
                                    if fmt.negate_credit
                                    else credit_amount
                                )
                            except ValueError as e:
                                result.errors.append(
                                    f"Row {row_num}: Invalid credit value: {e}"
                                )
                                continue
                    else:
                        # Regular format: read from amount column
                        amount_str = values.get("amount")
                        if not isinstance(amount_str, str) or amount_str == "":
                            result.errors.append(f"Row {row_num}: Missing amount")
                            continue

                        try:
                            amount = parse_amount(amount_str)
                        except ValueError as e:
                            result.errors.append(f"Row {row_num}: {e}")
                            continue

                    # If unique_id is not provided, generate it from date, description, and amount
                    if not unique_id:
                        description = values.get("description")
                        if not description:
                            result.errors.append(
                                f"Row {row_num}: Missing description (required when unique_id is not provided)"
                            )
                            continue
                        unique_id = self._generate_unique_id(
                            txn_date, description, amount
                        )

                    # Use the account from the format (account_name is not read from CSV)
                    account_id = fmt.account_id

                    # Verify account still exists
                    account = self.account_service.get_account(account_id)
                    if account is None:
                        result.errors.append(
                            f"Row {row_num}: Format's account {account_id} no longer exists"
                        )
                        continue

                    # Check for duplicate
                    if self.db.transaction_exists(account_id, unique_id):
                        result.skipped += 1
                        result.skipped_details.append(
                            SkippedTransaction(
                                row_num=row_num,
                                reason="Duplicate transaction",
                                details={
                                    "date": str(txn_date),
                                    "description": values.get("description", ""),
                                    "amount": str(amount),
                                },
                            )
                        )
                        continue

                    # Create transaction
                    self.transaction_service.create_transaction(
                        unique_id=unique_id,
                        account_id=account_id,
                        date=txn_date,
                        amount=amount,
                        description=values.get("description"),
                        reference_number=values.get("reference_number"),
                        category_id=None,  # Categories assigned later
                        notes=None,
                    )
                    result.imported += 1

                except DomainError as e:
                    result.errors.append(f"Row {row_num}: {str(e)}")
                    continue
                except Exception as e:
                    result.errors.append(f"Row {row_num}: {str(e)}")
                    continue

        return result.to_dict()
