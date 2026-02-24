"""Shared Slack API client and error normalization. Token is never logged or included in error messages."""
import json
from typing import Any

import requests  # type: ignore

from connector_slack.connector_interface import CommandErrorDict, CommandResponseDict, ConnectorProxyResponseDict

DEFAULT_TIMEOUT = 30

# Slack error codes that map to connector error codes
AUTH_ERRORS = ("invalid_auth", "token_revoked", "account_inactive", "not_authed")
SCOPE_ERRORS = ("missing_scope", "invalid_scopes")


def _slack_error_to_connector_error(response_json: dict[str, Any], status_code: int) -> tuple[int, CommandErrorDict]:
    """Map Slack API error to connector error_code and message. Never includes token."""
    slack_error = response_json.get("error", "unknown")
    messages = response_json.get("response_metadata", {}).get("messages", [])
    message_str = ". ".join(messages) if messages else str(slack_error)

    if slack_error in AUTH_ERRORS:
        return (
            status_code if status_code != 200 else 401,
            {"error_code": "SlackAuthError", "message": "Slack authentication failed or token was revoked."},
        )
    if slack_error in SCOPE_ERRORS:
        return (
            status_code if status_code != 200 else 403,
            {"error_code": "SlackPermissionError", "message": f"Slack permission error: {message_str}"},
        )
    return (
        status_code if status_code != 200 else 400,
        {"error_code": "SlackMessageFailed", "message": message_str or str(slack_error)},
    )


def post_json(url: str, token: str, body: dict[str, Any], timeout: int = DEFAULT_TIMEOUT) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """
    POST JSON to Slack API. Returns (response_json, http_status, error_dict).
    error_dict is None on success. Token is only used in Authorization header.
    """
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=body, timeout=timeout)
    except Exception as exc:
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})

    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return (
            {},
            response.status_code,
            {"error_code": "SlackMessageFailed", "message": "Unreadable (non JSON) response from Slack"},
        )

    try:
        response_json = response.json()
    except (ValueError, TypeError):
        return (
            {},
            response.status_code,
            {"error_code": "SlackMessageFailed", "message": "Unreadable (non JSON) response from Slack"},
        )

    if response_json.get("ok") is True:
        return (response_json, response.status_code, None)

    status_code, error = _slack_error_to_connector_error(response_json, response.status_code)
    return ({}, status_code, error)


def post_multipart(
    url: str, token: str, files: dict[str, tuple[str, bytes]], data: dict[str, str] | None = None, timeout: int = DEFAULT_TIMEOUT
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """
    POST multipart/form-data to Slack API (e.g. files.upload). Returns (response_json, http_status, error_dict).
    error_dict is None on success. Token is only used in Authorization header.
    """
    headers = {"Authorization": f"Bearer {token}"}
    if data is None:
        data = {}
    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=timeout)
    except Exception as exc:
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})

    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return (
            {},
            response.status_code,
            {"error_code": "SlackMessageFailed", "message": "Unreadable (non JSON) response from Slack"},
        )

    try:
        response_json = response.json()
    except (ValueError, TypeError):
        return (
            {},
            response.status_code,
            {"error_code": "SlackMessageFailed", "message": "Unreadable (non JSON) response from Slack"},
        )

    if response_json.get("ok") is True:
        return (response_json, response.status_code, None)

    status_code, error = _slack_error_to_connector_error(response_json, response.status_code)
    return ({}, status_code, error)


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for an error (e.g. invalid blocks JSON)."""
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(
    response_json: dict, status: int, error: CommandErrorDict | None
) -> ConnectorProxyResponseDict:
    """Build connector response from Slack response or error."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
