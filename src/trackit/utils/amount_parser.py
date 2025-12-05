"""Amount parsing utilities."""

from decimal import Decimal
import re


def parse_amount(amount_str: str) -> Decimal:
    """Parse an amount string into a Decimal.

    Handles various formats:
    - "123.45"
    - "$123.45"
    - "-123.45"
    - "-$123.45"
    - "1,234.56"
    - "(123.45)" (negative in parentheses)

    Args:
        amount_str: Amount string

    Returns:
        Decimal amount

    Raises:
        ValueError: If amount string cannot be parsed
    """
    if not amount_str or not amount_str.strip():
        raise ValueError("Empty amount string")

    # Remove whitespace
    amount_str = amount_str.strip()

    # Handle parentheses notation (negative)
    is_negative = False
    if amount_str.startswith("(") and amount_str.endswith(")"):
        is_negative = True
        amount_str = amount_str[1:-1]

    # Remove currency symbols
    amount_str = re.sub(r"[$€£¥]", "", amount_str)

    # Remove commas
    amount_str = amount_str.replace(",", "")

    # Remove whitespace again
    amount_str = amount_str.strip()

    try:
        amount = Decimal(amount_str)
        if is_negative:
            amount = -amount
        return amount
    except Exception as e:
        raise ValueError(f"Could not parse amount '{amount_str}': {e}")

