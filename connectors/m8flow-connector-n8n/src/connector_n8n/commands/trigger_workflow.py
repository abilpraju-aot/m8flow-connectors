"""Trigger an n8n workflow by calling its webhook URL."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import call_webhook
from connector_n8n.n8n_client import error_response


class TriggerWorkflow(ConnectorCommand):
    """Invoke an n8n workflow via its webhook URL, passing an optional JSON payload.

    Use this for any workflow exposed by a Webhook node, including AI/LLM and file/document
    processing workflows (supply the relevant data, e.g. base64 file content, in ``payload``).
    """

    def __init__(
        self,
        webhook_url: str,
        method: str = "POST",
        payload: dict | None = None,
        auth_type: str = "none",
        auth_header_name: str = "",
        auth_header_value: str = "",
        username: str = "",
        password: str = "",
    ):
        """
        :param webhook_url: Full n8n webhook URL (e.g. ``https://n8n.example.com/webhook/abc-123``).
        :param method: HTTP method the webhook expects: ``POST`` (default), ``GET``, ``PUT``, ``PATCH``, ``DELETE``.
        :param payload: JSON payload to send. Sent as a JSON body (non-GET) or query params (GET). Optional.
        :param auth_type: Webhook auth: ``none`` (default), ``header`` (custom header), or ``basic`` (HTTP basic).
        :param auth_header_name: Header name when ``auth_type`` is ``header`` (e.g. ``Authorization``).
        :param auth_header_value: Header value when ``auth_type`` is ``header``.
        :param username: Username when ``auth_type`` is ``basic``.
        :param password: Password when ``auth_type`` is ``basic``.
        """
        self.webhook_url = webhook_url
        self.method = method
        self.payload = payload
        self.auth_type = auth_type
        self.auth_header_name = auth_header_name
        self.auth_header_value = auth_header_value
        self.username = username
        self.password = password

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.webhook_url:
            return error_response(400, "N8nInvalidInput", "webhook_url is required.")
        response_json, status, error = call_webhook(
            self.webhook_url,
            self.method,
            payload=self.payload,
            auth_type=self.auth_type,
            auth_header_name=self.auth_header_name,
            auth_header_value=self.auth_header_value,
            username=self.username,
            password=self.password,
        )
        return build_result(response_json, status, error)
