"""Validation helpers for Stripe command inputs."""
import json
from typing import Any


class ValidationError(Exception):
    """Raised for command input validation failures."""


def require_non_empty(name: str, value: str) -> str:
    """Ensure value is a non-empty string."""
    out = str(value).strip() if value is not None else ""
    if not out:
        raise ValidationError(f"{name} is required.")
    return out


def parse_positive_int(name: str, value: str) -> int:
    """Parse a positive integer from string/number."""
    raw = str(value).strip() if value is not None else ""
    if not raw:
        raise ValidationError(f"{name} is required.")
    try:
        parsed = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer.") from exc
    if parsed <= 0:
        raise ValidationError(f"{name} must be greater than 0.")
    return parsed


def parse_optional_positive_int(name: str, value: str) -> int | None:
    """Parse optional positive int; empty string means None."""
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return None
    return parse_positive_int(name, raw)


def validate_currency(currency: str) -> str:
    """Validate and normalize ISO currency code."""
    out = require_non_empty("currency", currency).lower()
    if len(out) != 3 or not out.isalpha():
        raise ValidationError("currency must be a 3-letter ISO code (e.g. usd).")
    return out


def parse_bool(value: str, default: bool = False) -> bool:
    """Parse a bool from common string values."""
    raw = str(value).strip().lower() if value is not None else ""
    if not raw:
        return default
    if raw in ("true", "1", "yes", "y"):
        return True
    if raw in ("false", "0", "no", "n"):
        return False
    return default


def parse_metadata_json(metadata: str) -> dict[str, str]:
    """Parse metadata JSON as string dict with Stripe limits enforced.

    Stripe limits:
    - Max 50 key-value pairs
    - Keys max 40 characters
    - Values max 500 characters
    """
    raw = str(metadata).strip() if metadata is not None else ""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Invalid metadata JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValidationError("metadata must be a JSON object.")
    if len(parsed) > 50:
        raise ValidationError("metadata cannot have more than 50 key-value pairs.")
    out: dict[str, str] = {}
    for key, value in parsed.items():
        str_key = str(key)
        str_value = str(value)
        if len(str_key) > 40:
            raise ValidationError(f"metadata key '{str_key[:20]}...' exceeds 40 characters.")
        if len(str_value) > 500:
            raise ValidationError(f"metadata value for '{str_key}' exceeds 500 characters.")
        out[str_key] = str_value
    return out


VALID_REFUND_REASONS = frozenset({"duplicate", "fraudulent", "requested_by_customer"})


def validate_refund_reason(reason: str) -> str | None:
    """Validate Stripe refund reason. Returns None if empty, validated reason otherwise."""
    cleaned = str(reason).strip() if reason else ""
    if not cleaned:
        return None
    if cleaned not in VALID_REFUND_REASONS:
        raise ValidationError(
            f"Invalid refund reason '{cleaned}'. "
            f"Must be one of: {', '.join(sorted(VALID_REFUND_REASONS))}"
        )
    return cleaned


def parse_refund_reference(charge_id: str, payment_intent_id: str) -> tuple[str | None, str | None]:
    """Require exactly one of charge_id or payment_intent_id."""
    charge = str(charge_id).strip() if charge_id is not None else ""
    payment_intent = str(payment_intent_id).strip() if payment_intent_id is not None else ""
    if bool(charge) == bool(payment_intent):
        raise ValidationError("Provide exactly one of charge_id or payment_intent_id.")
    return (charge or None, payment_intent or None)


def ensure_idempotency_key_length(idempotency_key: str) -> str:
    """Validate max Stripe idempotency key length."""
    key = str(idempotency_key).strip() if idempotency_key is not None else ""
    if key and len(key) > 255:
        raise ValidationError("idempotency_key must be 255 characters or fewer.")
    return key


def to_form_payload(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten a nested dict/list payload into Stripe form-encoded key/value pairs."""
    out: dict[str, str] = {}
    for key, value in data.items():
        if value is None:
            continue
        full_key = f"{prefix}[{key}]" if prefix else str(key)
        if isinstance(value, dict):
            out.update(to_form_payload(value, full_key))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                list_key = f"{full_key}[{idx}]"
                if isinstance(item, dict):
                    out.update(to_form_payload(item, list_key))
                else:
                    out[list_key] = str(item)
        elif isinstance(value, bool):
            out[full_key] = "true" if value else "false"
        else:
            out[full_key] = str(value)
    return out
