"""Shared Stripe API client with idempotency support and error normalization. API key is never logged."""
import json
import logging
import uuid
from typing import Any
from urllib.parse import urlencode

import requests  # type: ignore

logger = logging.getLogger(__name__)

from connector_stripe.connector_interface import CommandErrorDict
from connector_stripe.connector_interface import CommandResponseDict
from connector_stripe.connector_interface import ConnectorProxyResponseDict

STRIPE_API_BASE = "https://api.stripe.com/v1"
DEFAULT_TIMEOUT = 30

AUTH_ERROR_TYPES = ("authentication_error",)
CARD_ERROR_TYPES = ("card_error",)
VALIDATION_ERROR_TYPES = ("invalid_request_error",)
RATE_LIMIT_ERROR_TYPES = ("rate_limit_error",)


def generate_idempotency_key() -> str:
    """Generate a unique idempotency key using UUID4."""
    return str(uuid.uuid4())


def _flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = "[") -> dict[str, Any]:
    """Flatten nested dict for Stripe's form encoding (e.g., metadata[key]=value)."""
    items: list[tuple[str, Any]] = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}]" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep="[").items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(_flatten_dict(item, f"{new_key}[{i}]", sep="[").items())
                else:
                    items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, v))
    return dict(items)


def _stripe_error_to_connector_error(response_json: dict[str, Any], status_code: int) -> tuple[int, CommandErrorDict]:
    """Map Stripe API error to connector error_code and message. Never includes API key."""
    error = response_json.get("error", {})
    error_type = error.get("type", "api_error")
    message = error.get("message", "Unknown Stripe error")
    code = error.get("code", "")
    decline_code = error.get("decline_code", "")

    if error_type in AUTH_ERROR_TYPES:
        return (
            401,
            {"error_code": "StripeAuthError", "message": "Stripe authentication failed. Check your API key."},
        )
    if error_type in CARD_ERROR_TYPES:
        decline_info = f" (decline_code: {decline_code})" if decline_code else ""
        return (
            402,
            {"error_code": "StripeCardError", "message": f"{message}{decline_info}"},
        )
    if error_type in VALIDATION_ERROR_TYPES:
        code_info = f" (code: {code})" if code else ""
        return (
            400,
            {"error_code": "StripeValidationError", "message": f"{message}{code_info}"},
        )
    if error_type in RATE_LIMIT_ERROR_TYPES:
        return (
            429,
            {"error_code": "StripeRateLimitError", "message": "Stripe rate limit exceeded. Please retry later."},
        )
    return (
        status_code if status_code >= 400 else 500,
        {"error_code": "StripeAPIError", "message": message},
    )


def _parse_stripe_response(response: requests.Response) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """Parse Stripe JSON response. Returns (response_json, http_status, error_dict)."""
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return (
            {},
            response.status_code,
            {"error_code": "StripeAPIError", "message": "Non-JSON response from Stripe API"},
        )
    try:
        response_json = response.json()
    except (ValueError, TypeError):
        return (
            {},
            response.status_code,
            {"error_code": "StripeAPIError", "message": "Invalid JSON response from Stripe API"},
        )

    if response.status_code >= 400:
        status_code, error = _stripe_error_to_connector_error(response_json, response.status_code)
        return ({}, status_code, error)

    return (response_json, response.status_code, None)


def post(
    endpoint: str,
    api_key: str,
    data: dict[str, Any],
    idempotency_key: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """
    POST form-encoded data to Stripe API. Returns (response_json, http_status, error_dict).
    error_dict is None on success. API key is only used in Authorization header.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    flat_data = _flatten_dict(data)
    filtered_data = {k: v for k, v in flat_data.items() if v is not None and v != ""}

    try:
        response = requests.post(
            f"{STRIPE_API_BASE}/{endpoint}",
            headers=headers,
            data=urlencode(filtered_data),
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return ({}, 504, {"error_code": "StripeTimeout", "message": "Request to Stripe API timed out"})
    except requests.exceptions.ConnectionError:
        return ({}, 503, {"error_code": "StripeConnectionError", "message": "Failed to connect to Stripe API"})
    except Exception as exc:
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})

    return _parse_stripe_response(response)


def delete(
    endpoint: str,
    api_key: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """
    DELETE request to Stripe API. Returns (response_json, http_status, error_dict).
    error_dict is None on success.
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.delete(
            f"{STRIPE_API_BASE}/{endpoint}",
            headers=headers,
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        return ({}, 504, {"error_code": "StripeTimeout", "message": "Request to Stripe API timed out"})
    except requests.exceptions.ConnectionError:
        return ({}, 503, {"error_code": "StripeConnectionError", "message": "Failed to connect to Stripe API"})
    except Exception as exc:
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})

    return _parse_stripe_response(response)


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for a validation or pre-request error."""
    logger.warning("Validation error [%s]: %s", error_code, message)
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(
    response_json: dict[str, Any], status: int, error: CommandErrorDict | None
) -> ConnectorProxyResponseDict:
    """Build connector response from Stripe response or error."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
