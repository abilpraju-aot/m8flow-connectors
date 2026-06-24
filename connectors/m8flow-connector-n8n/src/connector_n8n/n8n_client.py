"""Shared n8n API/webhook client and error normalization.

API keys and webhook credentials are never logged or included in error messages.
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

# Webhook auth modes supported by n8n Webhook nodes.
AUTH_NONE = "none"
AUTH_HEADER = "header"
AUTH_BASIC = "basic"


def normalize_base_url(base_url: str) -> str:
    """Strip a trailing slash so paths can be appended cleanly."""
    return base_url.rstrip("/")


def api_url(base_url: str, path: str) -> str:
    """Build a full n8n Public API URL (``{base}/api/v1/{path}``)."""
    return f"{normalize_base_url(base_url)}/api/v1/{path.lstrip('/')}"


def _build_api_headers(api_key: str) -> dict[str, str]:
    """Build standard n8n Public API request headers."""
    return {
        "X-N8N-API-KEY": api_key,
        "Accept": "application/json",
    }


def _n8n_error_to_connector_error(message: str, status_code: int) -> tuple[int, CommandErrorDict]:
    """Map an n8n API error to a connector error_code and message. Never includes credentials."""
    if status_code in (401, 403):
        return (
            status_code,
            {"error_code": "N8nAuthError", "message": "n8n authentication failed. Check your API key."},
        )
    if status_code == 404:
        return (
            404,
            {"error_code": "N8nNotFoundError", "message": f"n8n resource not found: {message}"},
        )
    return (
        status_code if status_code >= 400 else 400,
        {"error_code": "N8nRequestFailed", "message": message},
    )


def _extract_error_message(response_json: Any) -> str:
    """Pull a human-readable message out of an n8n error body (dict) if possible."""
    if isinstance(response_json, dict):
        message = response_json.get("message") or response_json.get("error")
        if isinstance(message, str):
            return message
    return "Unknown n8n error"


def _parse_json_response(response: "requests.Response") -> tuple[Any, int, CommandErrorDict | None]:
    """Parse a standard n8n Public API JSON response."""
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return (
            {},
            response.status_code,
            {"error_code": "N8nRequestFailed", "message": "Unreadable (non JSON) response from n8n"},
        )
    try:
        response_json = response.json()
    except (ValueError, TypeError):
        return (
            {},
            response.status_code,
            {"error_code": "N8nRequestFailed", "message": "Unreadable (non JSON) response from n8n"},
        )
    if response.status_code < 400:
        return (response_json, response.status_code, None)
    status_code, error = _n8n_error_to_connector_error(_extract_error_message(response_json), response.status_code)
    logger.warning("n8n API error: %s", error.get("message"))
    return ({}, status_code, error)


def api_request(
    method: str,
    url: str,
    api_key: str,
    params: dict[str, Any] | None = None,
    json_body: Any = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, int, CommandErrorDict | None]:
    """
    Call the n8n Public API. Returns (response_json, http_status, error_dict).
    error_dict is None on success. The API key is only used in the X-N8N-API-KEY header.
    """
    headers = _build_api_headers(api_key)
    try:
        response = requests.request(
            method.upper(), url, headers=headers, params=params, json=json_body, timeout=timeout
        )
    except Exception as exc:
        logger.warning("n8n API request failed: %s", exc)
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})
    return _parse_json_response(response)


def _parse_webhook_response(response: "requests.Response") -> tuple[Any, int, CommandErrorDict | None]:
    """Parse a webhook response, tolerating non-JSON bodies (text/binary 'Respond to Webhook')."""
    if response.status_code >= 400:
        message = response.text or f"n8n webhook returned HTTP {response.status_code}"
        status_code, error = _n8n_error_to_connector_error(message, response.status_code)
        logger.warning("n8n webhook error: %s", error.get("error_code"))
        return ({}, status_code, error)
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            return (response.json(), response.status_code, None)
        except (ValueError, TypeError):
            pass
    # Non-JSON (or unparseable) success body: return the raw text payload.
    return (response.text, response.status_code, None)


def call_webhook(
    webhook_url: str,
    method: str,
    payload: Any = None,
    auth_type: str = AUTH_NONE,
    auth_header_name: str = "",
    auth_header_value: str = "",
    username: str = "",
    password: str = "",
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, int, CommandErrorDict | None]:
    """
    Invoke an n8n workflow via its webhook URL. Returns (response_json_or_text, http_status, error_dict).

    Auth modes mirror the n8n Webhook node: ``none`` (no auth), ``header`` (custom header
    name/value), or ``basic`` (HTTP basic auth). For GET the payload is sent as query params;
    otherwise it is sent as a JSON body. Credentials are never logged.
    """
    method_upper = method.upper()
    headers: dict[str, str] = {}
    auth: tuple[str, str] | None = None
    if auth_type == AUTH_HEADER and auth_header_name:
        headers[auth_header_name] = auth_header_value
    elif auth_type == AUTH_BASIC:
        auth = (username, password)

    params = payload if method_upper == "GET" else None
    json_body = None if method_upper == "GET" else payload
    try:
        response = requests.request(
            method_upper, webhook_url, headers=headers, params=params, json=json_body, auth=auth, timeout=timeout
        )
    except Exception as exc:
        logger.warning("n8n webhook request failed: %s", exc)
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})
    return _parse_webhook_response(response)


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for an error (e.g. missing required field)."""
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status, "parsed_body": {}},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(response_json: Any, status: int, error: CommandErrorDict | None) -> ConnectorProxyResponseDict:
    """Build connector response from an n8n response or error."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
        "parsed_body": response_json,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
