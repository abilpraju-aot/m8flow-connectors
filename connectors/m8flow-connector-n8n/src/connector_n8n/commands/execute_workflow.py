"""Execute an n8n workflow via the REST API."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import build_api_url
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.validation import N8nValidationError
from connector_n8n.validation import normalize_api_base_url
from connector_n8n.validation import parse_json_field
from connector_n8n.validation import require_non_empty


class ExecuteWorkflow(ConnectorCommand):
    """Trigger workflow execution through the n8n REST API."""

    def __init__(self, base_url: str, api_key: str, workflow_id: str, input_data: str = "{}"):
        """
        :param base_url: n8n API base URL, e.g. https://my-n8n.example.com/api/v1
        :param api_key: n8n API key (X-N8N-API-KEY header).
        :param workflow_id: Target workflow ID.
        :param input_data: JSON string input payload for the workflow execution.
        """
        self.base_url = base_url
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.input_data = input_data

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_base = normalize_api_base_url(self.base_url)
            key = require_non_empty(self.api_key, "api_key")
            workflow_id = require_non_empty(self.workflow_id, "workflow_id")
            input_payload = parse_json_field("input_data", self.input_data)
        except N8nValidationError as exc:
            return error_response(400, "N8nValidationError", exc.message)

        url = build_api_url(api_base, f"workflows/{workflow_id}/run")
        body: dict[str, Any] = {}
        if isinstance(input_payload, dict) and input_payload:
            body["data"] = input_payload
        response_body, status, error = api_request("POST", url, key, body=body or None)
        return build_result(response_body, status, error)
