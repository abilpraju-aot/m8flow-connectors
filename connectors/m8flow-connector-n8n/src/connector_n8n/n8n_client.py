"""Shared n8n API and webhook client with error normalization. Credentials are never logged."""
import json
import logging
from typing import Any
from urllib.parse import urljoin

import requests  # type: ignore

from connector_n8n.connector_interface import CommandErrorDict
from connector_n8n.connector_interface import CommandResponseDict
from connector_n8n.connector_interface import ConnectorProxyResponseDict

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
WEBHOOK_DEFAULT_TIMEOUT = 120

WEBHOOK_NOT_REGISTERED_HINTS = ("not registered", "webhook not found")


def _build_api_headers(api_key: str) -> dict[str, str]:
    return {
        "X-N8N-API-KEY": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _n8n_api_error_to_connector_error(
    response_json: dict[str, Any] | list[Any],
    status_code: int,
    *,
    is_webhook: bool = False,
) -> tuple[int, CommandErrorDict]:
    """Map n8n API or webhook error to connector error_code and message."""
    message = "Unknown n8n error"
    if isinstance(response_json, dict):
        message = str(response_json.get("message") or response_json.get("error") or message)

    if status_code in (401, 403):
        return (
            status_code,
            {"error_code": "N8nAuthError", "message": "n8n authentication failed. Check your API key or webhook credentials."},
        )
    if status_code == 404:
        if is_webhook and any(hint in message.lower() for hint in WEBHOOK_NOT_REGISTERED_HINTS):
            return (
                404,
                {
                    "error_code": "N8nWebhookNotFound",
                    "message": "n8n webhook not registered. Ensure the workflow is active and the production URL is used.",
                },
            )
        return (
            404,
            {"error_code": "N8nNotFoundError", "message": f"n8n resource not found: {message}"},
        )
    if is_webhook:
        return (
            status_code if status_code >= 400 else 400,
            {"error_code": "N8nWebhookFailed", "message": message},
        )
    return (
        status_code if status_code >= 400 else 400,
        {"error_code": "N8nApiError", "message": message},
    )


def _response_to_body(response_json: Any, raw_text: str, content_type: str) -> tuple[Any, str, str]:
    """Return parsed body, serialized body string, and mimetype."""
    if response_json is not None:
        return response_json, json.dumps(response_json), "application/json"
    if "application/json" in content_type:
        return {}, "{}", "application/json"
    return raw_text, raw_text, content_type or "text/plain"


def _parse_http_response(
    response: requests.Response,
    *,
    is_webhook: bool = False,
) -> tuple[Any, int, CommandErrorDict | None, str]:
    """Parse HTTP response. Returns (body, http_status, error_dict, raw_text)."""
    content_type = response.headers.get("Content-Type", "")
    raw_text = response.text or ""
    response_json: Any = None

    if "application/json" in content_type and raw_text:
        try:
            response_json = response.json()
        except (ValueError, TypeError):
            if response.status_code < 400:
                return raw_text, response.status_code, None, raw_text

    if response.status_code >= 400:
        if isinstance(response_json, dict | list):
            error_source: dict[str, Any] | list[Any] = response_json
        else:
            error_source = {"message": raw_text}
        status_code, error = _n8n_api_error_to_connector_error(error_source, response.status_code, is_webhook=is_webhook)
        logger.warning("n8n request failed: %s", error.get("message"))
        return {}, status_code, error, raw_text

    if response_json is None and raw_text and "application/json" in content_type:
        return {}, response.status_code, {"error_code": "N8nApiError", "message": "Invalid JSON response from n8n"}, raw_text

    body = response_json if response_json is not None else raw_text
    return body, response.status_code, None, raw_text


def api_request(
    method: str,
    url: str,
    api_key: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, int, CommandErrorDict | None]:
    """Authenticated request to n8n REST API. Returns (response_body, http_status, error_dict)."""
    headers = _build_api_headers(api_key)
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=body,
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        logger.warning("n8n API request timed out")
        return ({}, 504, {"error_code": "N8nTimeout", "message": "n8n API request timed out"})
    except requests.exceptions.RequestException as exc:
        logger.warning("n8n API request failed: %s", exc.__class__.__name__)
        return ({}, 500, {"error_code": "N8nConnectionError", "message": str(exc)})

    parsed_body, status, error, _ = _parse_http_response(response, is_webhook=False)
    return parsed_body, status, error


def invoke_webhook(
    method: str,
    webhook_url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    basic_auth_user: str = "",
    basic_auth_password: str = "",
    timeout: int = WEBHOOK_DEFAULT_TIMEOUT,
) -> tuple[Any, int, CommandErrorDict | None]:
    """Invoke an n8n webhook URL. Returns (response_body, http_status, error_dict)."""
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update({str(k): str(v) for k, v in headers.items()})

    auth: tuple[str, str] | None = None
    if basic_auth_user:
        auth = (basic_auth_user, basic_auth_password)

    json_body = payload if method in {"POST", "PUT", "PATCH"} else None
    try:
        response = requests.request(
            method,
            webhook_url,
            headers=request_headers,
            params=query_params,
            json=json_body,
            auth=auth,
            timeout=timeout,
        )
    except requests.exceptions.Timeout:
        logger.warning("n8n webhook request timed out")
        return ({}, 504, {"error_code": "N8nTimeout", "message": "n8n webhook request timed out"})
    except requests.exceptions.RequestException as exc:
        logger.warning("n8n webhook request failed: %s", exc.__class__.__name__)
        return ({}, 500, {"error_code": "N8nConnectionError", "message": str(exc)})

    parsed_body, status, error, _ = _parse_http_response(response, is_webhook=True)
    return parsed_body, status, error


def build_api_url(base_url: str, path: str) -> str:
    """Join API base URL with a relative path."""
    normalized_base = base_url.rstrip("/") + "/"
    return urljoin(normalized_base, path.lstrip("/"))


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for a validation or local error."""
    return {
        "command_response": {
            "body": "{}",
            "mimetype": "application/json",
            "http_status": http_status,
            "parsed_body": {},
        },
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(response_body: Any, status: int, error: CommandErrorDict | None) -> ConnectorProxyResponseDict:
    """Build connector response from n8n response or error."""
    if isinstance(response_body, dict | list):
        body_str = json.dumps(response_body)
        parsed = response_body
        mimetype = "application/json"
    elif response_body is None:
        body_str = "{}"
        parsed = {}
        mimetype = "application/json"
    else:
        body_str = str(response_body)
        parsed = response_body
        mimetype = "text/plain"

    return_response: CommandResponseDict = {
        "body": body_str,
        "mimetype": mimetype,
        "http_status": status,
        "parsed_body": parsed,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
