"""List available workflows from an n8n instance via the public REST API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import API_PATH
from connector_n8n.n8n_client import DEFAULT_API_KEY_HEADER
from connector_n8n.n8n_client import DEFAULT_TIMEOUT
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.n8n_client import request_with_retry


class ListWorkflows(ConnectorCommand):
    """List workflows from an n8n instance so they can be selected in m8flow connector config."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        active: str = "",
        limit: int = 100,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        :param base_url: n8n base URL (e.g. ``https://n8n.example.com``).
        :param api_key: n8n API key, sent as the ``X-N8N-API-KEY`` header (from m8flow secrets).
        :param active: Filter by active state: ``true`` / ``false`` / ``""`` (all). Default ``""``.
        :param limit: Maximum number of workflows to return. Default 100.
        :param timeout: Request timeout in seconds. Default 30.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.active = active
        self.limit = limit
        self.timeout = timeout

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.base_url or not self.api_key:
            return error_response(400, "N8nConfigError", "base_url and api_key are required.")

        url = f"{self.base_url.rstrip('/')}{API_PATH}/workflows"
        params: dict[str, Any] = {"limit": self.limit}
        if self.active != "":
            params["active"] = self.active
        headers = {DEFAULT_API_KEY_HEADER: self.api_key}

        response_json, status, error = request_with_retry(
            "GET", url, headers=headers, params=params, timeout=self.timeout
        )
        return build_result(response_json, status, error)
