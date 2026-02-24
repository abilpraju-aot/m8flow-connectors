"""Salesforce REST client, token refresh, and error normalization. Tokens never logged or in error messages."""
import json
from typing import Any

import requests  # type: ignore

from connector_salesforce.connector_interface import CommandErrorDict
from connector_salesforce.connector_interface import CommandResponseDict
from connector_salesforce.connector_interface import ConnectorProxyResponseDict

DEFAULT_TIMEOUT = 30
API_VERSION = "v58.0"
TOKEN_URL_PROD = "https://login.salesforce.com/services/oauth2/token"  # noqa: S105
TOKEN_URL_SANDBOX = "https://test.salesforce.com/services/oauth2/token"  # noqa: S105


def _is_sandbox(instance_url: str) -> bool:
    return "test.salesforce.com" in (instance_url or "").lower()


def _token_url(instance_url: str) -> str:
    return TOKEN_URL_SANDBOX if _is_sandbox(instance_url) else TOKEN_URL_PROD


def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
    instance_url: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[str | None, str | None, CommandErrorDict | None]:
    """
    Exchange refresh_token for new access_token. Returns (access_token, instance_url, error).
    error is None on success. Tokens are never included in error messages.
    """
    url = _token_url(instance_url)
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    try:
        response = requests.post(url, data=data, timeout=timeout)
    except Exception as exc:
        return (None, None, {"error_code": "SalesforceAuthError", "message": str(exc)})

    ct = response.headers.get("Content-Type", "") or ""
    if "application/json" not in ct:
        return (
            None,
            None,
            {"error_code": "SalesforceAuthError", "message": "Token endpoint returned non-JSON response."},
        )
    try:
        resp_json = response.json()
    except (ValueError, TypeError):
        return (
            None,
            None,
            {"error_code": "SalesforceAuthError", "message": "Token endpoint returned invalid JSON."},
        )

    if response.status_code != 200:
        err_msg = resp_json.get("error_description") or resp_json.get("error") or "Token refresh failed."
        return (None, None, {"error_code": "SalesforceAuthError", "message": str(err_msg)})

    new_token = resp_json.get("access_token")
    new_instance = resp_json.get("instance_url") or instance_url
    if not new_token:
        return (None, None, {"error_code": "SalesforceAuthError", "message": "Token response missing access_token."})
    return (new_token, new_instance, None)


def _parse_salesforce_errors(body: bytes | str, status_code: int) -> tuple[int, CommandErrorDict]:
    """Parse Salesforce error response (single object or array) into status and CommandErrorDict."""
    message_str = "Unknown Salesforce error"
    if isinstance(body, bytes):
        try:
            text = body.decode("utf-8")
        except Exception:
            text = ""
    else:
        text = str(body) or ""

    if text.strip():
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            message_str = text[:500] if len(text) > 500 else text
        else:
            errors = data if isinstance(data, list) else [data]
            parts = []
            for err in errors:
                if isinstance(err, dict):
                    msg = err.get("message") or err.get("error") or err.get("errorDescription") or ""
                    code = err.get("errorCode") or ""
                    if code:
                        parts.append(f"{code}: {msg}".strip() or code)
                    else:
                        parts.append(msg)
                else:
                    parts.append(str(err))
            message_str = ". ".join(parts) if parts else message_str

    if status_code == 401:
        return (401, {"error_code": "SalesforceAuthError", "message": "Authentication failed or token expired."})
    if status_code == 403:
        return (403, {"error_code": "SalesforcePermissionError", "message": message_str})
    if status_code == 400 or status_code == 422:
        return (status_code, {"error_code": "SalesforceValidationError", "message": message_str})
    return (status_code if status_code >= 400 else 400, {"error_code": "SalesforceApiError", "message": message_str})


def _request(
    method: str,
    url: str,
    access_token: str,
    body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """Perform HTTP request. Returns (response_json, status_code, error). error is None on success."""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=body or {}, timeout=timeout)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=body or {}, timeout=timeout)
        else:
            return ({}, 400, {"error_code": "SalesforceApiError", "message": f"Unsupported method: {method}"})
    except Exception as exc:
        return ({}, 500, {"error_code": exc.__class__.__name__, "message": str(exc)})

    raw = response.content
    ct = response.headers.get("Content-Type", "") or ""
    if response.ok:
        if not raw:
            return ({}, response.status_code, None)
        if "application/json" in ct:
            try:
                return (response.json(), response.status_code, None)
            except (ValueError, TypeError):
                pass
        return ({"raw": raw.decode("utf-8", errors="replace")}, response.status_code, None)

    status, error = _parse_salesforce_errors(raw, response.status_code)
    return ({}, status, error)


def sobject_base_url(instance_url: str) -> str:
    """Build sobjects base URL (no trailing slash)."""
    base = (instance_url or "").rstrip("/")
    return f"{base}/services/data/{API_VERSION}/sobjects"


def get(
    instance_url: str,
    access_token: str,
    path: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """GET request to instance_url + path. Path should be e.g. 'Lead/00Q...'. Returns (data, status, error)."""
    base = sobject_base_url(instance_url)
    url = f"{base}/{path}" if not path.startswith("/") else f"{base}{path}"
    return _request("GET", url, access_token, timeout=timeout)


def post(
    instance_url: str,
    access_token: str,
    path: str,
    body: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """POST request (e.g. Create). Path e.g. 'Lead'. Returns (data, status, error)."""
    base = sobject_base_url(instance_url)
    url = f"{base}/{path}" if not path.startswith("/") else f"{base}{path}"
    return _request("POST", url, access_token, body=body, timeout=timeout)


def patch(
    instance_url: str,
    access_token: str,
    path: str,
    body: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """PATCH request (e.g. Update). Path e.g. 'Lead/00Q...'. Returns (data, status, error)."""
    base = sobject_base_url(instance_url)
    url = f"{base}/{path}" if not path.startswith("/") else f"{base}{path}"
    return _request("PATCH", url, access_token, body=body, timeout=timeout)


def delete(
    instance_url: str,
    access_token: str,
    path: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    """DELETE request. Path e.g. 'Lead/00Q...'. Returns (data, status, error)."""
    base = sobject_base_url(instance_url)
    url = f"{base}/{path}" if not path.startswith("/") else f"{base}{path}"
    return _request("DELETE", url, access_token, timeout=timeout)


def request_with_retry(
    instance_url: str,
    access_token: str,
    refresh_token: str | None,
    client_id: str | None,
    client_secret: str | None,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[dict[str, Any], int, CommandErrorDict | None, str, str]:
    """
    Perform request; on 401 and if refresh_token/client_id/client_secret present, refresh and retry once.
    Returns (data, status, error, final_access_token, final_instance_url).
    """
    token, inst = access_token, instance_url
    data, status, err = _do_one(method, inst, token, path, body, timeout)
    if status != 401 or err is None:
        return (data, status, err, token, inst)
    if not all([refresh_token, client_id, client_secret]):
        return (data, status, err, token, inst)
    new_token, new_inst, refresh_err = refresh_access_token(
        refresh_token, client_id, client_secret, inst, timeout
    )
    if refresh_err or not new_token:
        return (data, status, err, token, inst)
    token, inst = new_token, new_inst or inst
    data, status, err = _do_one(method, inst, token, path, body, timeout)
    return (data, status, err, token, inst)


def _do_one(
    method: str,
    instance_url: str,
    access_token: str,
    path: str,
    body: dict[str, Any] | None,
    timeout: int,
) -> tuple[dict[str, Any], int, CommandErrorDict | None]:
    if method == "GET":
        return get(instance_url, access_token, path, timeout)
    if method == "DELETE":
        return delete(instance_url, access_token, path, timeout)
    if method == "POST":
        return post(instance_url, access_token, path, body or {}, timeout)
    if method == "PATCH":
        return patch(instance_url, access_token, path, body or {}, timeout)
    return ({}, 400, {"error_code": "SalesforceApiError", "message": f"Unsupported method: {method}"})


def error_response(http_status: int, error_code: str, message: str) -> ConnectorProxyResponseDict:
    """Build connector response for an error (e.g. validation failure)."""
    return {
        "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status},
        "error": {"error_code": error_code, "message": message},
        "command_response_version": 2,
    }


def build_result(
    response_json: dict[str, Any], status: int, error: CommandErrorDict | None
) -> ConnectorProxyResponseDict:
    """Build connector response from Salesforce response or error."""
    return_response: CommandResponseDict = {
        "body": json.dumps(response_json),
        "mimetype": "application/json",
        "http_status": status,
    }
    return {"command_response": return_response, "error": error, "command_response_version": 2}
