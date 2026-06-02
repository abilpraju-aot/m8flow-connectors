"""List n8n workflow executions (optionally filtered by workflow or status) via the public REST API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import API_PATH
from connector_n8n.n8n_client import DEFAULT_API_KEY_HEADER
from connector_n8n.n8n_client import DEFAULT_TIMEOUT
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.n8n_client import request_with_retry


class ListExecutions(ConnectorCommand):
    """List recent executions, optionally filtered by workflow id and status, to track run history."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workflow_id: str = "",
        status: str = "",
        limit: int = 100,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        :param base_url: n8n base URL (e.g. ``https://n8n.example.com``).
        :param api_key: n8n API key, sent as the ``X-N8N-API-KEY`` header (from m8flow secrets).
        :param workflow_id: Filter executions by workflow id. Default ``""`` (all).
        :param status: Filter by status: ``success`` / ``error`` / ``waiting`` / ``""`` (all). Default ``""``.
        :param limit: Maximum number of executions to return. Default 100.
        :param timeout: Request timeout in seconds. Default 30.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.status = status
        self.limit = limit
        self.timeout = timeout

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.base_url or not self.api_key:
            return error_response(400, "N8nConfigError", "base_url and api_key are required.")

        url = f"{self.base_url.rstrip('/')}{API_PATH}/executions"
        params: dict[str, Any] = {"limit": self.limit}
        if self.workflow_id:
            params["workflowId"] = self.workflow_id
        if self.status:
            params["status"] = self.status
        headers = {DEFAULT_API_KEY_HEADER: self.api_key}

        response_json, status, error = request_with_retry(
            "GET", url, headers=headers, params=params, timeout=self.timeout
        )
        return build_result(response_json, status, error)
