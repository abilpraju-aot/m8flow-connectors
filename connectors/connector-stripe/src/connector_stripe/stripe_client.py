"""Shared Stripe API client and error normalization.

API keys are never logged or included in error messages.
"""
import hashlib
import json
import uuid
from typing import Any

import requests  # type: ignore

from connector_stripe.connector_interface import CommandErrorDict
from connector_stripe.connector_interface import CommandResponseDict
from connector_stripe.connector_interface import ConnectorProxyResponseDict

DEFAULT_TIMEOUT = 30
STRIPE_API_BASE_URL = "https://api.stripe.com/v1"


def _extract_task_fingerprint(task_data: Any) -> str:
    """Build deterministic fingerprint from task metadata when available."""
    if not isinstance(task_data, dict):
        return ""
    keys = [
        "task_instance_id",
        "task_id",
        "execution_id",
        "workflow_instance_id",
        "process_instance_id",
        "correlation_id",
    ]
    parts: list[str] = []
    for key in keys:
        value = task_data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(f"{key}:{text}")
    return "|".join(parts)


def resolve_idempotency_key(
    provided_key: str | None,
    operation: str,
    payload: dict[str, Any],
    task_data: Any,
) -> str:
    """Return provided key or generate deterministic key from operation/payload/task context."""
    cleaned = str(provided_key).strip() if provided_key is not None else ""
    if cleaned:
        return cleaned

    fingerprint = _extract_task_fingerprint(task_data)
    payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if fingerprint:
        base = f"{operation}|{fingerprint}|{payload_str}"
        digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
        return f"m8stripe_{operation}_{digest[:40]}"

    return f"m8stripe_{operation}_{uuid.uuid4().hex}"


def _build_error_message(error_obj: dict[str, Any]) -> str:
    """Compose a readable Stripe error message from error object."""
    message = str(error_obj.get("message") or "Unknown Stripe error")
    code = str(error_obj.get("code") or "").strip()
    error_type = str(error_obj.get("type") or "").strip()
    decline_code = str(error_obj.get("decline_code") or "").strip()

    parts = [message]
    if code:
        parts.append(f"code={code}")
    if error_type:
        parts.append(f"type={error_type}")
    if decline_code:
        parts.append(f"decline_code={decline_code}")
    return " | ".join(parts)


def _parse_stripe_error(body: bytes | str, status_code: int) -> tuple[int, CommandErrorDict]:
    """Map Stripe API error payload/status to connector error code and message."""
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)
    message = text[:500] if text else "Unknown Stripe error"
    error_obj: dict[str, Any] = {}

    if text.strip():
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            nested = parsed.get("error")
            if isinstance(nested, dict):
                error_obj = nested
                message = _build_error_message(error_obj)
            else:
                message = str(parsed)

    error_type = str(error_obj.get("type") or "").strip()

    if status_code == 401:
        return (401, {"error_code": "StripeAuthError", "message": message or "Stripe authentication failed."})
    if status_code == 429:
        return (429, {"error_code": "StripeRateLimitError", "message": message or "Stripe rate limit exceeded."})
    if status_code == 402 or error_type == "card_error":
        return (status_code if status_code >= 400 else 402, {"error_code": "StripeCardError", "message": message})
    if status_code in (400, 404, 422) or error_type == "invalid_request_error":
        return (
            status_code if status_code >= 400 else 400,
            {"error_code": "StripeValidationError", "message": message},
        )
    return (status_code if status_code >= 400 else 500, {"error_code": "StripeApiError", "message": message})


def request_form(
    method: str,
    path: str,
    api_key: str,
    form_data: dict[str, str] | None = None,
    idempotency_key: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """Send a Stripe API request and return (json, status, error)."""
    token = str(api_key).strip() if api_key is not None else ""
    headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    url = f"{STRIPE_API_BASE_URL}/{path.lstrip('/')}"
    try:
        response = requests.request(method.upper(), url, headers=headers, data=form_data or {}, timeout=timeout)
    except Exception as exc:
        return ({}, 500, {"error_code": "StripeApiError", "message": f"{exc.__class__.__name__}: {exc}"})

    if response.ok:
        if not response.content:
            return ({}, response.status_code, None)
        try:
            payload = response.json()
        except (TypeError, ValueError):
            text = response.text or ""
            return ({"raw": text}, response.status_code, None)
        if isinstance(payload, dict):
            return (payload, response.status_code, None)
        return ({"raw": str(payload)}, response.status_code, None)

    status, error = _parse_stripe_error(response.content, response.status_code)
    return ({}, status, error)


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for an error."""
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(response_json: dict[str, Any], status: int, error: CommandErrorDict | None) -> ConnectorProxyResponseDict:
    """Build connector response from Stripe response or error."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
