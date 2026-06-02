"""Retrieve the status/result of a single n8n workflow execution via the public REST API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import API_PATH
from connector_n8n.n8n_client import DEFAULT_API_KEY_HEADER
from connector_n8n.n8n_client import DEFAULT_TIMEOUT
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.n8n_client import request_with_retry


class GetExecution(ConnectorCommand):
    """Fetch an n8n execution by id to track its status and (optionally) its result data."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        execution_id: str,
        include_data: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        :param base_url: n8n base URL (e.g. ``https://n8n.example.com``).
        :param api_key: n8n API key, sent as the ``X-N8N-API-KEY`` header (from m8flow secrets).
        :param execution_id: Id of the execution to retrieve.
        :param include_data: Include full execution result data. Default True.
        :param timeout: Request timeout in seconds. Default 30.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.execution_id = execution_id
        self.include_data = include_data
        self.timeout = timeout

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.base_url or not self.api_key:
            return error_response(400, "N8nConfigError", "base_url and api_key are required.")
        if not self.execution_id:
            return error_response(400, "N8nConfigError", "execution_id is required.")

        url = f"{self.base_url.rstrip('/')}{API_PATH}/executions/{self.execution_id}"
        params: dict[str, Any] = {"includeData": "true" if self.include_data else "false"}
        headers = {DEFAULT_API_KEY_HEADER: self.api_key}

        response_json, status, error = request_with_retry(
            "GET", url, headers=headers, params=params, timeout=self.timeout
        )
        return build_result(response_json, status, error)
