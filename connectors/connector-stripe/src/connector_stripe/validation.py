"""Input validation helpers for Stripe connector."""
import json
import re
from typing import Any

CURRENCY_PATTERN = re.compile(r"^[a-zA-Z]{3}$")


class StripeValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def validate_amount(amount: str) -> int:
    """Validate and parse amount string to integer (smallest currency unit).

    Raises StripeValidationError if invalid.
    """
    if not amount or not amount.strip():
        raise StripeValidationError("Amount is required")

    try:
        amount_int = int(amount.strip())
    except ValueError as exc:
        raise StripeValidationError(f"Amount must be a valid integer, got: {amount}") from exc

    if amount_int <= 0:
        raise StripeValidationError(f"Amount must be positive, got: {amount_int}")

    return amount_int


def validate_currency(currency: str) -> str:
    """Validate currency is a 3-letter ISO code.

    Raises StripeValidationError if invalid.
    """
    if not currency or not currency.strip():
        raise StripeValidationError("Currency is required")

    currency = currency.strip().lower()
    if not CURRENCY_PATTERN.match(currency):
        raise StripeValidationError(f"Currency must be a 3-letter ISO code, got: {currency}")

    return currency


def validate_required(value: str, field_name: str) -> str:
    """Validate a required string field is not empty.

    Raises StripeValidationError if empty.
    """
    if not value or not value.strip():
        raise StripeValidationError(f"{field_name} is required")
    return value.strip()


def validate_optional_json(json_str: str, field_name: str) -> dict[str, Any] | None:
    """Validate and parse optional JSON string.

    Returns None if empty, parsed dict if valid.
    Raises StripeValidationError if invalid JSON.
    """
    if not json_str or not json_str.strip():
        return None

    try:
        parsed = json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as exc:
        raise StripeValidationError(f"Invalid JSON for {field_name}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise StripeValidationError(f"{field_name} must be a JSON object, got: {type(parsed).__name__}")

    return parsed


def validate_boolean_string(value: str, default: bool = False) -> bool:
    """Parse a boolean string value.

    Accepts: 'true', 'false', '1', '0', 'yes', 'no' (case-insensitive).
    Returns default if empty.
    """
    if not value or not value.strip():
        return default

    value = value.strip().lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False

    return default


def validate_stripe_id(value: str, prefix: str, field_name: str) -> str:
    """Validate a Stripe ID has the expected prefix.

    Raises StripeValidationError if invalid.
    """
    if not value or not value.strip():
        raise StripeValidationError(f"{field_name} is required")

    value = value.strip()
    if not value.startswith(prefix):
        raise StripeValidationError(f"{field_name} must start with '{prefix}', got: {value[:20]}...")

    return value


def validate_optional_stripe_id(value: str, prefix: str, field_name: str) -> str | None:
    """Validate an optional Stripe ID has the expected prefix if provided.

    Returns None if empty.
    Raises StripeValidationError if provided but invalid.
    """
    if not value or not value.strip():
        return None

    value = value.strip()
    if not value.startswith(prefix):
        raise StripeValidationError(f"{field_name} must start with '{prefix}', got: {value[:20]}...")

    return value
