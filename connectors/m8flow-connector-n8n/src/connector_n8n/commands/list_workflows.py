"""List n8n workflows via the REST API."""
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


class ListWorkflows(ConnectorCommand):
    """List workflows from an n8n instance."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        active: str = "",
        name: str = "",
        limit: str = "50",
        cursor: str = "",
    ):
        """
        :param base_url: n8n API base URL, e.g. https://my-n8n.example.com/api/v1
        :param api_key: n8n API key (X-N8N-API-KEY header).
        :param active: Filter by active status: true, false, or empty for all.
        :param name: Partial workflow name filter.
        :param limit: Maximum workflows to return (default 50).
        :param cursor: Pagination cursor from a previous response.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.active = active
        self.name = name
        self.limit = limit
        self.cursor = cursor

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_base = normalize_api_base_url(self.base_url)
            key = require_non_empty(self.api_key, "api_key")
        except N8nValidationError as exc:
            return error_response(400, "N8nValidationError", exc.message)

        params: dict[str, Any] = {}
        if self.active.strip():
            params["active"] = self.active.strip().lower()
        if self.name.strip():
            params["name"] = self.name.strip()
        if self.limit.strip():
            params["limit"] = self.limit.strip()
        if self.cursor.strip():
            params["cursor"] = self.cursor.strip()

        url = build_api_url(api_base, "workflows")
        response_body, status, error = api_request("GET", url, key, params=params)
        if error is None and isinstance(response_body, dict):
            data = response_body.get("data", [])
            if isinstance(data, list):
                summary = [
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "active": item.get("active"),
                        "tags": item.get("tags", []),
                    }
                    for item in data
                    if isinstance(item, dict)
                ]
                response_body = {**response_body, "summary": summary}
        return build_result(response_body, status, error)
