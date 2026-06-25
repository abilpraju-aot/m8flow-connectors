"""Discover webhook URLs from an n8n workflow definition."""
from typing import Any

from connector_n8n.connector_interface import ConnectorCommand
from connector_n8n.connector_interface import ConnectorProxyResponseDict
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import build_api_url
from connector_n8n.n8n_client import build_result
from connector_n8n.n8n_client import error_response
from connector_n8n.validation import N8nValidationError
from connector_n8n.validation import normalize_api_base_url
from connector_n8n.validation import normalize_instance_host
from connector_n8n.validation import require_non_empty

WEBHOOK_NODE_TYPES = frozenset({"n8n-nodes-base.webhook", "@n8n/n8n-nodes-langchain.webhook"})


def extract_webhook_urls(workflow: dict[str, Any], instance_host: str) -> list[dict[str, str]]:
    """Parse webhook nodes from a workflow and build production/test URLs."""
    webhooks: list[dict[str, str]] = []
    nodes = workflow.get("nodes", [])
    if not isinstance(nodes, list):
        return webhooks

    host = instance_host.rstrip("/")
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type", ""))
        if node_type not in WEBHOOK_NODE_TYPES:
            continue
        parameters = node.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
        path = str(parameters.get("path", "")).strip().lstrip("/")
        if not path:
            continue
        webhooks.append(
            {
                "node_name": str(node.get("name", "")),
                "path": path,
                "http_method": str(parameters.get("httpMethod", "GET")),
                "production_url": f"{host}/webhook/{path}",
                "test_url": f"{host}/webhook-test/{path}",
            }
        )
    return webhooks


class GetWorkflowWebhooks(ConnectorCommand):
    """Resolve webhook URLs for a workflow by inspecting its webhook trigger nodes."""

    def __init__(self, base_url: str, api_key: str, workflow_id: str, instance_host: str):
        """
        :param base_url: n8n API base URL, e.g. https://my-n8n.example.com/api/v1
        :param api_key: n8n API key (X-N8N-API-KEY header).
        :param workflow_id: Target workflow ID.
        :param instance_host: Public n8n host, e.g. https://my-n8n.example.com
        """
        self.base_url = base_url
        self.api_key = api_key
        self.workflow_id = workflow_id
        self.instance_host = instance_host

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_base = normalize_api_base_url(self.base_url)
            key = require_non_empty(self.api_key, "api_key")
            workflow_id = require_non_empty(self.workflow_id, "workflow_id")
            host = normalize_instance_host(self.instance_host)
        except N8nValidationError as exc:
            return error_response(400, "N8nValidationError", exc.message)

        url = build_api_url(api_base, f"workflows/{workflow_id}")
        workflow_body, status, error = api_request("GET", url, key)
        if error is not None:
            return build_result(workflow_body, status, error)

        if not isinstance(workflow_body, dict):
            return error_response(500, "N8nApiError", "Unexpected workflow response format")

        webhooks = extract_webhook_urls(workflow_body, host)
        response = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_body.get("name"),
            "active": workflow_body.get("active"),
            "webhooks": webhooks,
        }
        return build_result(response, status, None)
