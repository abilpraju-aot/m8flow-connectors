"""Invoke an n8n workflow via its webhook URL."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.n8n_client import invoke_webhook
from connector_n8n.validation import N8nValidationError
from connector_n8n.validation import parse_json_field
from connector_n8n.validation import parse_timeout
from connector_n8n.validation import require_non_empty
from connector_n8n.validation import validate_http_method


class InvokeWebhook(ConnectorCommand):
    """Invoke an n8n workflow using its webhook URL."""

    def __init__(
        self,
        webhook_url: str,
        method: str = "POST",
        payload: str = "{}",
        headers: str = "{}",
        query_params: str = "{}",
        basic_auth_user: str = "",
        basic_auth_password: str = "",
        timeout: str = "120",
    ):
        """
        :param webhook_url: Full n8n webhook URL (production or test).
        :param method: HTTP method (GET, POST, PUT, PATCH, DELETE). Default POST.
        :param payload: JSON string request body.
        :param headers: JSON string of additional HTTP headers.
        :param query_params: JSON string of query parameters.
        :param basic_auth_user: Optional basic auth username for protected webhooks.
        :param basic_auth_password: Optional basic auth password.
        :param timeout: Request timeout in seconds (1-600). Default 120.
        """
        self.webhook_url = webhook_url
        self.method = method
        self.payload = payload
        self.headers = headers
        self.query_params = query_params
        self.basic_auth_user = basic_auth_user
        self.basic_auth_password = basic_auth_password
        self.timeout = timeout

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            url = require_non_empty(self.webhook_url, "webhook_url")
            http_method = validate_http_method(self.method)
            body = parse_json_field("payload", self.payload)
            header_map = parse_json_field("headers", self.headers)
            params = parse_json_field("query_params", self.query_params)
            request_timeout = parse_timeout(self.timeout, default=120)
            if not isinstance(body, dict):
                raise N8nValidationError("payload must be a JSON object")
            if not isinstance(header_map, dict):
                raise N8nValidationError("headers must be a JSON object")
            if not isinstance(params, dict):
                raise N8nValidationError("query_params must be a JSON object")
        except N8nValidationError as exc:
            return error_response(400, "N8nValidationError", exc.message)

        response_body, status, error = invoke_webhook(
            http_method,
            url,
            payload=body,
            headers=header_map,
            query_params=params,
            basic_auth_user=self.basic_auth_user,
            basic_auth_password=self.basic_auth_password,
            timeout=request_timeout,
        )
        return build_result(response_body, status, error)
