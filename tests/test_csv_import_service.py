"""Domain tests for CSV import service."""

import pytest

from trackit.domain.csv_import import CSVImportService
from trackit.domain.errors import ValidationError


def test_import_service_result_contract(temp_db, sample_csv_format, fixtures_dir):
    """Import returns a structured result contract."""
    service = CSVImportService(temp_db)
    csv_file = fixtures_dir / "sample_transactions.csv"

    result = service.import_csv(str(csv_file), "Test Format")

    assert result["imported"] > 0
    assert result["skipped"] == 0
    assert isinstance(result["skipped_details"], list)
    assert isinstance(result["errors"], list)
    assert result["errors"] == []


def test_import_service_missing_columns_raises(
    temp_db, sample_csv_format, fixtures_dir
):
    """Missing required columns raises a validation error."""
    service = CSVImportService(temp_db)
    csv_file = fixtures_dir / "sample_transactions_missing_cols.csv"

    with pytest.raises(ValidationError) as excinfo:
        service.import_csv(str(csv_file), "Test Format")

    assert "missing required columns" in str(excinfo.value).lower()


def test_import_service_row_error_collected(temp_db, sample_csv_format, tmp_path):
    """Row-level parsing errors are collected in result errors."""
    service = CSVImportService(temp_db)
    csv_path = tmp_path / "missing_amount.csv"
    csv_path.write_text(
        "Transaction ID,Date,Amount,Description,Reference\n"
        "TXN1,2024-01-15,,Test,REF1\n",
        encoding="utf-8",
    )

    result = service.import_csv(str(csv_path), "Test Format")

    assert result["imported"] == 0
    assert any("Missing amount" in error for error in result["errors"])


def test_import_service_duplicate_detection_generated_id(
    temp_db,
    sample_account,
    sample_csv_format_no_id,
    fixtures_dir,
    transaction_service,
):
    """Duplicate detection uses generated unique IDs when mapping omitted."""
    from datetime import date
    from decimal import Decimal

    service = CSVImportService(temp_db)
    generated_id = service._generate_unique_id(
        date(2024, 1, 15),
        "Grocery Store",
        Decimal("-50.00"),
    )

    transaction_service.create_transaction(
        unique_id=generated_id,
        account_id=sample_account.id,
        date=date(2024, 1, 15),
        amount=Decimal("-50.00"),
        description="Grocery Store",
    )

    csv_file = fixtures_dir / "sample_transactions_no_id.csv"
    result = service.import_csv(str(csv_file), "Test Format No ID")

    assert result["skipped"] >= 1
    assert any(
        skipped["row_num"] == 2 and skipped["details"]["description"] == "Grocery Store"
        for skipped in result["skipped_details"]
    )


def test_import_service_headers_only(temp_db, sample_csv_format, tmp_path):
    """Header-only CSV returns empty results without errors."""
    service = CSVImportService(temp_db)
    csv_path = tmp_path / "headers_only.csv"
    csv_path.write_text(
        "Transaction ID,Date,Amount,Description,Reference\n",
        encoding="utf-8",
    )

    result = service.import_csv(str(csv_path), "Test Format")

    assert result["imported"] == 0
    assert result["skipped"] == 0
    assert result["errors"] == []


def test_import_service_error_ordering(temp_db, sample_csv_format, tmp_path):
    """Row-level errors are reported in input order."""
    service = CSVImportService(temp_db)
    csv_path = tmp_path / "error_ordering.csv"
    csv_path.write_text(
        "Transaction ID,Date,Amount,Description,Reference\n"
        "TXN1,2024-01-15,,Test One,REF1\n"
        "TXN2,,10.00,Test Two,REF2\n",
        encoding="utf-8",
    )

    result = service.import_csv(str(csv_path), "Test Format")

    assert result["errors"][0].startswith("Row 2: Missing amount")
    assert result["errors"][1].startswith("Row 3: Missing date")


def test_import_service_missing_unique_id_row_error(
    temp_db, sample_csv_format, tmp_path
):
    """Missing unique_id is reported as row error when mapped."""
    service = CSVImportService(temp_db)
    csv_path = tmp_path / "missing_unique_id.csv"
    csv_path.write_text(
        "Transaction ID,Date,Amount,Description,Reference\n"
        ",2024-01-15,-5.00,Test,REF1\n",
        encoding="utf-8",
    )

    result = service.import_csv(str(csv_path), "Test Format")

    assert result["imported"] == 0
    assert result["errors"] == ["Row 2: Missing unique_id"]


def test_import_service_semicolon_delimiter(temp_db, sample_csv_format, tmp_path):
    """Semicolon-delimited CSV is parsed successfully."""
    service = CSVImportService(temp_db)
    csv_path = tmp_path / "semicolon.csv"
    csv_path.write_text(
        "Transaction ID;Date;Amount;Description;Reference\n"
        "TXN1;2024-01-15;-1.00;Test;REF1\n",
        encoding="utf-8",
    )

    result = service.import_csv(str(csv_path), "Test Format")

    assert result["imported"] == 1
    assert result["errors"] == []


def test_import_service_debit_credit_missing_both_row_error(
    temp_db, sample_debit_credit_format, tmp_path
):
    """Debit/credit rows with both values missing are reported as errors."""
    service = CSVImportService(temp_db)
    csv_path = tmp_path / "missing_debit_credit.csv"
    csv_path.write_text(
        "Date,Debit,Credit,Description,Member Name\n2025-11-26,,,Test,REF\n",
        encoding="utf-8",
    )

    result = service.import_csv(str(csv_path), "Test Debit Credit Format")

    assert result["imported"] == 0
    assert any(
        "Missing both debit and credit values" in error for error in result["errors"]
    )
