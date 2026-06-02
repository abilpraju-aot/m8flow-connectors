"""Trigger an n8n workflow by calling its webhook URL with a mapped payload."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import DEFAULT_API_KEY_HEADER
from connector_n8n.n8n_client import DEFAULT_MAX_RETRIES
from connector_n8n.n8n_client import DEFAULT_TIMEOUT
from connector_n8n.n8n_client import build_auth
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.n8n_client import parse_json_param
from connector_n8n.n8n_client import request_with_retry


class TriggerWorkflow(ConnectorCommand):
    """Invoke an n8n workflow via its webhook URL, sending a JSON payload and returning the response.

    This is the primary invocation command. It carries arbitrary JSON in ``payload`` and returns
    the workflow's JSON response in ``parsed_body``, so it supports any n8n workflow including
    AI/LLM workflows and file/document workflows (pass file content as base64 inside ``payload``).
    """

    def __init__(
        self,
        webhook_url: str = "",
        base_url: str = "",
        webhook_path: str = "",
        method: str = "POST",
        payload: str = "{}",
        query_params: str = "{}",
        auth_type: str = "none",
        api_key: str = "",
        auth_header_name: str = DEFAULT_API_KEY_HEADER,
        bearer_token: str = "",
        basic_username: str = "",
        basic_password: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        """
        :param webhook_url: Full n8n webhook URL. If empty, ``base_url`` + ``webhook_path`` are joined.
        :param base_url: n8n base URL (e.g. ``https://n8n.example.com``); used with ``webhook_path``.
        :param webhook_path: Webhook path (e.g. ``/webhook/abc123``); used with ``base_url``.
        :param method: HTTP method for the webhook. Default ``POST``.
        :param payload: Request body as a JSON object/string mapped from workflow variables. Default ``{}``.
        :param query_params: Optional query string as a JSON object/string. Default ``{}``.
        :param auth_type: Webhook auth: ``none`` (default), ``header`` (API key), ``bearer``, or ``basic``.
        :param api_key: API key value for ``header`` auth (from m8flow secrets).
        :param auth_header_name: Header name for ``header`` auth. Default ``X-N8N-API-KEY``.
        :param bearer_token: Token for ``bearer`` auth (from m8flow secrets).
        :param basic_username: Username for ``basic`` auth.
        :param basic_password: Password for ``basic`` auth (from m8flow secrets).
        :param timeout: Request timeout in seconds. Default 30.
        :param max_retries: Retries on timeout / 429 / 5xx. Default 0 (no retry).
        """
        self.webhook_url = webhook_url
        self.base_url = base_url
        self.webhook_path = webhook_path
        self.method = method
        self.payload = payload
        self.query_params = query_params
        self.auth_type = auth_type
        self.api_key = api_key
        self.auth_header_name = auth_header_name
        self.bearer_token = bearer_token
        self.basic_username = basic_username
        self.basic_password = basic_password
        self.timeout = timeout
        self.max_retries = max_retries

    def _resolve_url(self) -> str:
        if self.webhook_url:
            return self.webhook_url
        if self.base_url and self.webhook_path:
            return f"{self.base_url.rstrip('/')}/{self.webhook_path.lstrip('/')}"
        return ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        url = self._resolve_url()
        if not url:
            return error_response(400, "N8nConfigError", "Provide either webhook_url or both base_url and webhook_path.")

        body, body_error = parse_json_param(self.payload, "payload")
        if body_error:
            return error_response(400, body_error["error_code"], body_error["message"])
        params, params_error = parse_json_param(self.query_params, "query_params")
        if params_error:
            return error_response(400, params_error["error_code"], params_error["message"])

        headers, basic_auth, auth_error = build_auth(
            self.auth_type,
            api_key=self.api_key,
            auth_header_name=self.auth_header_name,
            bearer_token=self.bearer_token,
            basic_username=self.basic_username,
            basic_password=self.basic_password,
        )
        if auth_error:
            return error_response(400, auth_error["error_code"], auth_error["message"])

        response_json, status, error = request_with_retry(
            self.method,
            url,
            headers=headers,
            basic_auth=basic_auth,
            json_body=body,
            params=params or None,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        return build_result(response_json, status, error)
