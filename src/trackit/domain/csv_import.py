"""CSV import domain service."""

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence, TextIO

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

    def _get_format(self, format_name: str):
        fmt = self.format_service.get_format_by_name(format_name)
        if fmt is None:
            raise NotFoundError(f"CSV format '{format_name}' not found")

        is_valid, missing = self.format_service.validate_format(fmt.id)
        if not is_valid:
            raise ValidationError(
                f"CSV format '{format_name}' is missing required mappings: {', '.join(missing)}"
            )

        return fmt

    def _get_column_map(self, format_id: int) -> dict[str, str]:
        mappings = self.format_service.get_mappings(format_id)
        return {m.csv_column_name: m.db_field_name for m in mappings}

    def _open_csv_reader(self, csv_path: Path) -> tuple[csv.DictReader, TextIO]:
        f = open(csv_path, "r", encoding="utf-8-sig")
        sample = f.read(1024)
        f.seek(0)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter
        return csv.DictReader(f, delimiter=delimiter), f

    def _validate_required_columns(
        self, fmt, column_map: dict[str, str], csv_columns: Sequence[str] | None
    ) -> None:
        if csv_columns is None:
            raise ValidationError("CSV file has no columns")

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

    def _extract_values(
        self, row: dict[str, str], column_map: dict[str, str]
    ) -> dict[str, str | None]:
        values: dict[str, str | None] = {}
        for csv_col, db_field in column_map.items():
            if csv_col in row:
                values[db_field] = row[csv_col].strip() if row[csv_col] else None
            else:
                values[db_field] = None
        return values

    def _parse_row(
        self,
        row_num: int,
        values: dict[str, str | None],
        fmt,
        has_unique_id_mapping: bool,
        result: ImportResult,
    ) -> dict[str, Any] | None:
        unique_id = values.get("unique_id")
        if not unique_id and has_unique_id_mapping:
            result.errors.append(f"Row {row_num}: Missing unique_id")
            return None

        date_str = values.get("date")
        if not date_str:
            result.errors.append(f"Row {row_num}: Missing date")
            return None

        try:
            txn_date = parse_date(date_str)
        except ValueError as e:
            result.errors.append(f"Row {row_num}: {e}")
            return None

        amount: Decimal
        if fmt.is_debit_credit_format:
            debit_str = values.get("debit")
            credit_str = values.get("credit")
            debit_value = debit_str if isinstance(debit_str, str) else None
            credit_value = credit_str if isinstance(credit_str, str) else None

            has_debit = debit_value is not None and debit_value.strip() != ""
            has_credit = credit_value is not None and credit_value.strip() != ""

            if not has_debit and not has_credit:
                result.errors.append(
                    f"Row {row_num}: Missing both debit and credit values (exactly one required)"
                )
                return None

            if has_debit and has_credit:
                result.errors.append(
                    f"Row {row_num}: Both debit and credit have values (exactly one required)"
                )
                return None

            if has_debit and debit_value is not None:
                try:
                    debit_amount = parse_amount(debit_value)
                    amount = -debit_amount if fmt.negate_debit else debit_amount
                except ValueError as e:
                    result.errors.append(f"Row {row_num}: Invalid debit value: {e}")
                    return None
            else:
                if credit_value is None:
                    result.errors.append(f"Row {row_num}: Missing credit value")
                    return None
                try:
                    credit_amount = parse_amount(credit_value)
                    amount = -credit_amount if fmt.negate_credit else credit_amount
                except ValueError as e:
                    result.errors.append(f"Row {row_num}: Invalid credit value: {e}")
                    return None
        else:
            amount_str = values.get("amount")
            if not isinstance(amount_str, str) or amount_str == "":
                result.errors.append(f"Row {row_num}: Missing amount")
                return None

            try:
                amount = parse_amount(amount_str)
            except ValueError as e:
                result.errors.append(f"Row {row_num}: {e}")
                return None

        if not unique_id:
            description = values.get("description")
            if not description:
                result.errors.append(
                    f"Row {row_num}: Missing description (required when unique_id is not provided)"
                )
                return None
            unique_id = self._generate_unique_id(txn_date, description, amount)

        return {
            "unique_id": unique_id,
            "date": txn_date,
            "amount": amount,
            "description": values.get("description"),
            "reference_number": values.get("reference_number"),
        }

    def _check_account_exists(
        self, account_id: int, row_num: int, result: ImportResult
    ) -> bool:
        account = self.account_service.get_account(account_id)
        if account is None:
            result.errors.append(
                f"Row {row_num}: Format's account {account_id} no longer exists"
            )
            return False
        return True

    def _record_duplicate(
        self,
        account_id: int,
        unique_id: str,
        row_num: int,
        txn_date: date,
        values: dict[str, str | None],
        amount: Decimal,
        result: ImportResult,
    ) -> bool:
        if self.db.transaction_exists(account_id, unique_id):
            result.skipped += 1
            result.skipped_details.append(
                SkippedTransaction(
                    row_num=row_num,
                    reason="Duplicate transaction",
                    details={
                        "date": str(txn_date),
                        "description": values.get("description", "") or "",
                        "amount": str(amount),
                    },
                )
            )
            return True
        return False

    def _persist_transaction(self, account_id: int, parsed: dict[str, Any]) -> None:
        self.transaction_service.create_transaction(
            unique_id=parsed["unique_id"],
            account_id=account_id,
            date=parsed["date"],
            amount=parsed["amount"],
            description=parsed.get("description"),
            reference_number=parsed.get("reference_number"),
            category_id=None,
            notes=None,
        )

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
        fmt = self._get_format(format_name)
        column_map = self._get_column_map(fmt.id)

        # Read CSV file
        csv_path = Path(csv_file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

        result = ImportResult()

        # Check if unique_id is mapped
        has_unique_id_mapping = "unique_id" in column_map.values()

        reader, file_handle = self._open_csv_reader(csv_path)
        try:
            self._validate_required_columns(fmt, column_map, reader.fieldnames)

            for row_num, row in enumerate(reader, start=2):
                try:
                    values = self._extract_values(row, column_map)
                    parsed = self._parse_row(
                        row_num=row_num,
                        values=values,
                        fmt=fmt,
                        has_unique_id_mapping=has_unique_id_mapping,
                        result=result,
                    )
                    if parsed is None:
                        continue

                    account_id = fmt.account_id
                    if not self._check_account_exists(account_id, row_num, result):
                        continue

                    if self._record_duplicate(
                        account_id=account_id,
                        unique_id=parsed["unique_id"],
                        row_num=row_num,
                        txn_date=parsed["date"],
                        values=values,
                        amount=parsed["amount"],
                        result=result,
                    ):
                        continue

                    self._persist_transaction(account_id, parsed)
                    result.imported += 1

                except DomainError as e:
                    result.errors.append(f"Row {row_num}: {str(e)}")
                except Exception as e:
                    result.errors.append(f"Row {row_num}: {str(e)}")
        finally:
            file_handle.close()

        return result.to_dict()
