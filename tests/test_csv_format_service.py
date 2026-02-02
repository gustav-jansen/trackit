"""Domain tests for CSV format service."""

import pytest


def test_debit_credit_format_rejects_amount_mapping(csv_format_service, sample_account):
    """Debit/credit formats cannot map the amount field."""
    format_id = csv_format_service.create_format(
        name="Debit Credit Domain",
        account_id=sample_account.id,
        is_debit_credit_format=True,
    )

    with pytest.raises(ValueError) as excinfo:
        csv_format_service.add_mapping(format_id, "Amount", "amount", is_required=True)

    assert "Cannot map 'amount' field for debit/credit format" in str(excinfo.value)
