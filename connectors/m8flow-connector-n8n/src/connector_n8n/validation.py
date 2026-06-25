"""Input validation helpers for the n8n connector."""
import json
from typing import Any

ALLOWED_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"})


class N8nValidationError(Exception):
    """Raised when command input validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def parse_json_field(name: str, value: str) -> Any:
    """Parse a JSON string field; raise N8nValidationError on invalid JSON."""
    if not value or not value.strip():
        return {}
    try:
        return json.loads(value)
    except (ValueError, TypeError) as exc:
        raise N8nValidationError(f"Invalid JSON for {name}: {exc}") from exc


def normalize_api_base_url(url: str) -> str:
    """Normalize n8n API base URL to end with /api/v1 without trailing slash."""
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        raise N8nValidationError("base_url is required")
    if cleaned.endswith("/api/v1"):
        return cleaned
    if cleaned.endswith("/api"):
        return f"{cleaned}/v1"
    return f"{cleaned}/api/v1"


def normalize_instance_host(url: str) -> str:
    """Normalize n8n instance host URL without trailing slash."""
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        raise N8nValidationError("instance_host is required")
    if cleaned.endswith("/api/v1"):
        cleaned = cleaned[: -len("/api/v1")]
    elif cleaned.endswith("/api"):
        cleaned = cleaned[: -len("/api")]
    return cleaned.rstrip("/")


def validate_http_method(method: str) -> str:
    """Validate and normalize HTTP method."""
    normalized = method.strip().upper()
    if normalized not in ALLOWED_HTTP_METHODS:
        raise N8nValidationError(f"Unsupported HTTP method: {method}")
    return normalized


def parse_timeout(value: str, default: int = 120) -> int:
    """Parse timeout seconds with bounds checking."""
    if not value or not value.strip():
        return default
    try:
        timeout = int(value.strip())
    except ValueError as exc:
        raise N8nValidationError(f"timeout must be an integer, got: {value}") from exc
    if timeout < 1 or timeout > 600:
        raise N8nValidationError("timeout must be between 1 and 600 seconds")
    return timeout


def require_non_empty(value: str, field_name: str) -> str:
    """Ensure a required string field is non-empty."""
    cleaned = value.strip()
    if not cleaned:
        raise N8nValidationError(f"{field_name} is required")
    return cleaned
