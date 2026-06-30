"""Shared GitHub API client and error normalization. Token is never logged or included in error messages."""
import json
import logging
from typing import Any

import requests  # type: ignore

from connector_github.connector_interface import CommandErrorDict
from connector_github.connector_interface import CommandResponseDict
from connector_github.connector_interface import ConnectorProxyResponseDict

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
GITHUB_API_BASE = "https://api.github.com"

# GitHub error codes / messages that map to connector error codes
AUTH_MESSAGES = ("Bad credentials", "Requires authentication")
NOT_FOUND_MESSAGE = "Not Found"


def _build_headers(token: str) -> dict[str, str]:
    """Build standard GitHub API request headers."""
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _github_error_to_connector_error(response_json: dict[str, Any], status_code: int) -> tuple[int, CommandErrorDict]:
    """Map GitHub API error to connector error_code and message. Never includes token."""
    message = response_json.get("message", "Unknown GitHub error")

    if status_code in (401, 403) or any(m in message for m in AUTH_MESSAGES):
        return (
            status_code,
            {"error_code": "GitHubAuthError", "message": "GitHub authentication failed. Check your token."},
        )
    if status_code == 404 or NOT_FOUND_MESSAGE in message:
        return (
            404,
            {"error_code": "GitHubNotFoundError", "message": f"GitHub resource not found: {message}"},
        )
    return (
        status_code if status_code >= 400 else 400,
        {"error_code": "GitHubRequestFailed", "message": message},
    )


def get_json(
    url: str,
    token: str,
    params: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, int, CommandErrorDict | None]:
    """
    GET JSON from GitHub API. Returns (response_json, http_status, error_dict).
    error_dict is None on success. Token is only used in Authorization header.
    response_json may be a list or a dict depending on the endpoint.
    """
    headers = _build_headers(token)
    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
    except Exception as exc:
        logger.warning("GitHub API request failed: %s", exc)
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})
    return _parse_github_json_response(response)


def _parse_github_json_response(response: requests.Response) -> tuple[Any, int, CommandErrorDict | None]:
    """Parse a standard GitHub JSON API response."""
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        return (
            {},
            response.status_code,
            {"error_code": "GitHubRequestFailed", "message": "Unreadable (non JSON) response from GitHub"},
        )
    try:
        response_json = response.json()
    except (ValueError, TypeError):
        return (
            {},
            response.status_code,
            {"error_code": "GitHubRequestFailed", "message": "Unreadable (non JSON) response from GitHub"},
        )
    if response.status_code < 400:
        return (response_json, response.status_code, None)
    status_code, error = _github_error_to_connector_error(response_json, response.status_code)
    logger.warning("GitHub API error: %s", error.get("message"))
    return ({}, status_code, error)


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for an error (e.g. missing required field)."""
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status, "parsed_body": {}},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(
    response_json: Any, status: int, error: CommandErrorDict | None
) -> ConnectorProxyResponseDict:
    """Build connector response from GitHub response or error."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
        "parsed_body": response_json,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
