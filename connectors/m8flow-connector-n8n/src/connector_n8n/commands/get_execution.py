"""Get n8n execution status and results via the REST API."""
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


class GetExecution(ConnectorCommand):
    """Retrieve execution status and optional execution data."""

    def __init__(self, base_url: str, api_key: str, execution_id: str, include_data: str = "false"):
        """
        :param base_url: n8n API base URL, e.g. https://my-n8n.example.com/api/v1
        :param api_key: n8n API key (X-N8N-API-KEY header).
        :param execution_id: Execution ID to retrieve.
        :param include_data: Include full node I/O when true (default false).
        """
        self.base_url = base_url
        self.api_key = api_key
        self.execution_id = execution_id
        self.include_data = include_data

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_base = normalize_api_base_url(self.base_url)
            key = require_non_empty(self.api_key, "api_key")
            execution_id = require_non_empty(self.execution_id, "execution_id")
        except N8nValidationError as exc:
            return error_response(400, "N8nValidationError", exc.message)

        include = self.include_data.strip().lower() in {"true", "1", "yes"}
        params = {"includeData": str(include).lower()}
        url = build_api_url(api_base, f"executions/{execution_id}")
        response_body, status, error = api_request("GET", url, key, params=params)
        return build_result(response_body, status, error)
