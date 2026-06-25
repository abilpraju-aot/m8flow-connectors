"""List n8n executions via the REST API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import build_api_url
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.validation import N8nValidationError
from connector_n8n.validation import normalize_api_base_url
from connector_n8n.validation import require_non_empty


class ListExecutions(ConnectorCommand):
    """List workflow executions with optional filters."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workflow_id: str = "",
        status: str = "",
        limit: str = "20",
        cursor: str = "",
    ):
        """
        :param base_url: n8n API base URL, e.g. https://my-n8n.example.com/api/v1
        :param api_key: n8n API key (X-N8N-API-KEY header).
        :param workflow_id: Optional workflow ID filter.
        :param status: Optional status filter (success, error, running, waiting, canceled, crashed).
        :param limit: Maximum executions to return (default 20).
        :param cursor: Pagination cursor from a previous response.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.status = status
        self.limit = limit
        self.cursor = cursor

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_base = normalize_api_base_url(self.base_url)
            key = require_non_empty(self.api_key, "api_key")
        except N8nValidationError as exc:
            return error_response(400, "N8nValidationError", exc.message)

        params: dict[str, Any] = {}
        if self.workflow_id.strip():
            params["workflowId"] = self.workflow_id.strip()
        if self.status.strip():
            params["status"] = self.status.strip()
        if self.limit.strip():
            params["limit"] = self.limit.strip()
        if self.cursor.strip():
            params["cursor"] = self.cursor.strip()

        url = build_api_url(api_base, "executions")
        response_body, status, error = api_request("GET", url, key, params=params)
        return build_result(response_body, status, error)
