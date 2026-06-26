"""Retrieve a single n8n workflow by id via the Public API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import api_url
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response


class GetWorkflow(ConnectorCommand):
    """Fetch a single workflow's details (nodes, settings, active state) by id."""

    def __init__(self, base_url: str, api_key: str, workflow_id: str):
        """
        :param base_url: n8n instance base URL (e.g. ``https://n8n.example.com``).
        :param api_key: n8n Public API key (Settings > n8n API), sent as the ``X-N8N-API-KEY`` header.
        :param workflow_id: Id of the workflow to retrieve.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.workflow_id = workflow_id

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.base_url or not self.api_key or not self.workflow_id:
            return error_response(400, "N8nInvalidInput", "base_url, api_key and workflow_id are required.")
        url = api_url(self.base_url, f"workflows/{self.workflow_id}")
        response_json, status, error = api_request("GET", url, self.api_key)
        return build_result(response_json, status, error)
