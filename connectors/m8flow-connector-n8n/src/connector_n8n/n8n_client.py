"""Shared n8n API/webhook client: auth, request, retry, and error normalization.

Credentials (API keys, bearer tokens, basic-auth passwords) are only used to build request
auth and are never logged or included in error messages.
"""
import json
import logging
from typing import Any

import requests  # type: ignore

from connector_n8n.connector_interface import CommandErrorDict
from connector_n8n.connector_interface import CommandResponseDict
from connector_n8n.connector_interface import ConnectorProxyResponseDict

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 0
API_PATH = "/api/v1"
DEFAULT_API_KEY_HEADER = "X-N8N-API-KEY"

# Auth modes supported for webhook invocation and REST API calls.
AUTH_NONE = "none"
AUTH_HEADER = "header"
AUTH_BEARER = "bearer"
AUTH_BASIC = "basic"
VALID_AUTH_TYPES = (AUTH_NONE, AUTH_HEADER, AUTH_BEARER, AUTH_BASIC)

# HTTP statuses worth retrying (transient): rate limit + server errors.
RETRYABLE_STATUSES = (429, 500, 502, 503, 504)


def build_auth(
    auth_type: str,
    *,
    api_key: str = "",
    auth_header_name: str = DEFAULT_API_KEY_HEADER,
    bearer_token: str = "",
    basic_username: str = "",
    basic_password: str = "",
) -> tuple[dict[str, str], tuple[str, str] | None, CommandErrorDict | None]:
    """Build request headers and optional basic-auth tuple for the given auth mode.

    Returns ``(headers, basic_auth, error)``. ``error`` is non-None only when the auth
    configuration is invalid (e.g. unknown ``auth_type`` or missing credential). Secrets are
    never logged.
    """
    headers: dict[str, str] = {}
    basic_auth: tuple[str, str] | None = None

    if auth_type == AUTH_NONE:
        return (headers, basic_auth, None)
    if auth_type == AUTH_HEADER:
        if not api_key:
            return ({}, None, {"error_code": "N8nConfigError", "message": "api_key is required for 'header' auth."})
        headers[auth_header_name or DEFAULT_API_KEY_HEADER] = api_key
        return (headers, basic_auth, None)
    if auth_type == AUTH_BEARER:
        if not bearer_token:
            return ({}, None, {"error_code": "N8nConfigError", "message": "bearer_token is required for 'bearer' auth."})
        headers["Authorization"] = f"Bearer {bearer_token}"
        return (headers, basic_auth, None)
    if auth_type == AUTH_BASIC:
        if not basic_username or not basic_password:
            return (
                {},
                None,
                {"error_code": "N8nConfigError", "message": "basic_username and basic_password are required for 'basic' auth."},
            )
        return (headers, (basic_username, basic_password), None)

    valid = ", ".join(VALID_AUTH_TYPES)
    return (
        {},
        None,
        {"error_code": "N8nConfigError", "message": f"Unsupported auth_type: {auth_type}. Use one of {valid}."},
    )


def _execution_id_from_body(body: Any) -> Any:
    """Best-effort extraction of an n8n executionId from a response body for logging/tracking."""
    if not isinstance(body, dict):
        return None
    execution_id = body.get("executionId") or body.get("id")
    if execution_id:
        return execution_id
    data = body.get("data")
    if isinstance(data, dict):
        return data.get("executionId") or data.get("id")
    return None


def _n8n_error_to_connector_error(body: Any, status_code: int) -> tuple[int, CommandErrorDict]:
    """Map an n8n error response to a connector error_code and message. Never includes credentials."""
    message = "Unknown n8n error"
    if isinstance(body, dict):
        message = body.get("message") or body.get("error") or body.get("hint") or message
    elif isinstance(body, str) and body.strip():
        message = body[:500]

    if status_code in (401, 403):
        auth_msg = "n8n authentication failed. Check your API key/token or webhook auth."
        return (status_code, {"error_code": "N8nAuthError", "message": auth_msg})
    if status_code == 404:
        return (404, {"error_code": "N8nNotFoundError", "message": f"n8n resource not found: {message}"})
    if status_code >= 500:
        return (status_code, {"error_code": "N8nExecutionFailed", "message": f"n8n workflow/webhook execution failed: {message}"})
    return (status_code if status_code >= 400 else 400, {"error_code": "N8nRequestFailed", "message": str(message)})


def _parse_json_response(response: requests.Response) -> tuple[Any, int, CommandErrorDict | None]:
    """Parse an n8n JSON response into (body, status, error). Handles empty and non-JSON bodies."""
    status_code = response.status_code
    raw = response.content

    if status_code < 400:
        if not raw:
            # Some webhooks (e.g. "Respond immediately") return an empty 200 body.
            return ({}, status_code, None)
        content_type = response.headers.get("Content-Type", "") or ""
        if "application/json" not in content_type:
            return (
                {},
                status_code,
                {"error_code": "N8nInvalidResponse", "message": "Unreadable (non JSON) response from n8n."},
            )
        try:
            return (response.json(), status_code, None)
        except (ValueError, TypeError):
            return (
                {},
                status_code,
                {"error_code": "N8nInvalidResponse", "message": "Invalid JSON in response from n8n."},
            )

    parsed: Any = {}
    content_type = response.headers.get("Content-Type", "") or ""
    if "application/json" in content_type:
        try:
            parsed = response.json()
        except (ValueError, TypeError):
            parsed = {}
    elif raw:
        parsed = raw.decode("utf-8", errors="replace")
    status, error = _n8n_error_to_connector_error(parsed, status_code)
    logger.warning("n8n API error (status %s): %s", status, error.get("message"))
    return ({}, status, error)


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    basic_auth: tuple[str, str] | None = None,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, int, CommandErrorDict | None]:
    """Perform a single HTTP request to n8n. Returns (body, status, error).

    Network timeouts map to ``N8nTimeoutError``; other transport errors map to a generic
    failure using the exception class name. Auth values are passed to ``requests`` only and
    are never logged.
    """
    logger.info("n8n request: %s %s", method.upper(), url)
    try:
        response = requests.request(
            method.upper(),
            url,
            headers=headers or {},
            auth=basic_auth,
            json=json_body if json_body is not None else None,
            params=params,
            timeout=timeout,
        )
    except requests.Timeout:
        logger.warning("n8n request timed out after %ss: %s %s", timeout, method.upper(), url)
        return ({}, 504, {"error_code": "N8nTimeoutError", "message": f"n8n request timed out after {timeout}s."})
    except Exception as exc:
        logger.warning("n8n request failed: %s", exc)
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})

    body, status, error = _parse_json_response(response)
    execution_id = _execution_id_from_body(body)
    if execution_id:
        logger.info("n8n response: status %s, executionId %s", status, execution_id)
    else:
        logger.info("n8n response: status %s", status)
    return (body, status, error)


def request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    basic_auth: tuple[str, str] | None = None,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> tuple[Any, int, CommandErrorDict | None]:
    """Perform a request, retrying on timeout / 429 / 5xx up to ``max_retries`` times.

    Each retry is logged at WARNING with the attempt number (no secrets). Returns the result
    of the final attempt.
    """
    attempts = max(0, max_retries) + 1
    body: Any = {}
    status = 500
    error: CommandErrorDict | None = None
    for attempt in range(1, attempts + 1):
        body, status, error = request_json(
            method,
            url,
            headers=headers,
            basic_auth=basic_auth,
            json_body=json_body,
            params=params,
            timeout=timeout,
        )
        retryable = error is not None and (error.get("error_code") == "N8nTimeoutError" or status in RETRYABLE_STATUSES)
        if not retryable or attempt >= attempts:
            return (body, status, error)
        logger.warning("n8n request retry %s/%s (status %s): %s %s", attempt, attempts - 1, status, method.upper(), url)
    return (body, status, error)


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for an error (e.g. invalid config / missing required field)."""
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status, "parsed_body": {}},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(response_json: Any, status: int, error: CommandErrorDict | None) -> ConnectorProxyResponseDict:
    """Build connector response from an n8n response or error. Parsed body is available for output mapping."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
        "parsed_body": response_json,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}


def parse_json_param(value: Any, field_name: str) -> tuple[Any, CommandErrorDict | None]:
    """Parse a JSON-string parameter (payload / query_params) coming from a workflow variable.

    Accepts an already-parsed dict/list (passed through) or a JSON string. Returns (parsed, error);
    error is non-None with code ``N8nConfigError`` when the string is not valid JSON.
    """
    if value is None or value == "":
        return ({}, None)
    if isinstance(value, dict | list):
        return (value, None)
    if isinstance(value, str):
        try:
            return (json.loads(value), None)
        except (ValueError, TypeError):
            return (None, {"error_code": "N8nConfigError", "message": f"{field_name} is not valid JSON."})
    return (None, {"error_code": "N8nConfigError", "message": f"{field_name} must be a JSON object/array or JSON string."})
