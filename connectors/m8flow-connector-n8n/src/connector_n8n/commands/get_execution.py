"""Retrieve a single n8n execution (status/result) by id via the Public API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import api_url
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response


class GetExecution(ConnectorCommand):
    """Fetch a single execution's status and (optionally) its full result data by id."""

    def __init__(self, base_url: str, api_key: str, execution_id: str, include_data: bool = False):
        """
        :param base_url: n8n instance base URL (e.g. ``https://n8n.example.com``).
        :param api_key: n8n Public API key (Settings > n8n API), sent as the ``X-N8N-API-KEY`` header.
        :param execution_id: Id of the execution to retrieve.
        :param include_data: When ``True``, include the full execution result data. Default is ``False``.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.execution_id = execution_id
        self.include_data = include_data

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.base_url or not self.api_key or not self.execution_id:
            return error_response(400, "N8nInvalidInput", "base_url, api_key and execution_id are required.")
        params: dict[str, Any] = {}
        if self.include_data:
            params["includeData"] = "true"
        url = api_url(self.base_url, f"executions/{self.execution_id}")
        response_json, status, error = api_request("GET", url, self.api_key, params=params)
        return build_result(response_json, status, error)
