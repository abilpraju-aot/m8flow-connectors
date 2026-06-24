"""List workflows from an n8n instance via the Public API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import api_url
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response


class ListWorkflows(ConnectorCommand):
    """List workflows on an n8n instance, with optional active filter and pagination."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        active: str = "",
        limit: int = 100,
        cursor: str = "",
    ):
        """
        :param base_url: n8n instance base URL (e.g. ``https://n8n.example.com``).
        :param api_key: n8n Public API key (Settings > n8n API), sent as the ``X-N8N-API-KEY`` header.
        :param active: Filter by active state: ``true``, ``false``, or ``""`` for all (default).
        :param limit: Maximum number of workflows to return (1–250). Default is 100.
        :param cursor: Pagination cursor from a previous response's ``nextCursor``. Optional.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.active = active
        self.limit = limit
        self.cursor = cursor

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.base_url or not self.api_key:
            return error_response(400, "N8nInvalidInput", "base_url and api_key are required.")
        params: dict[str, Any] = {"limit": self.limit}
        if self.active in ("true", "false"):
            params["active"] = self.active
        if self.cursor:
            params["cursor"] = self.cursor
        url = api_url(self.base_url, "workflows")
        response_json, status, error = api_request("GET", url, self.api_key, params=params)
        return build_result(response_json, status, error)
