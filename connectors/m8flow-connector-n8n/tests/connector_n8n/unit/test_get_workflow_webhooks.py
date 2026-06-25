"""Unit tests for GetWorkflowWebhooks command."""
import json
from unittest.mock import patch

from connector_n8n.commands.get_workflow_webhooks import GetWorkflowWebhooks
from connector_n8n.commands.get_workflow_webhooks import extract_webhook_urls


class TestExtractWebhookUrls:
    def test_extracts_production_and_test_urls(self) -> None:
        workflow = {
            "nodes": [
                {
                    "name": "Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {"path": "m8flow-test", "httpMethod": "POST"},
                }
            ]
        }
        urls = extract_webhook_urls(workflow, "https://n8n.example.com")
        assert urls[0]["production_url"] == "https://n8n.example.com/webhook/m8flow-test"
        assert urls[0]["test_url"] == "https://n8n.example.com/webhook-test/m8flow-test"


class TestGetWorkflowWebhooks:
    def test_successful_discovery(self) -> None:
        workflow = {
            "name": "Demo",
            "active": True,
            "nodes": [
                {
                    "name": "Webhook",
                    "type": "n8n-nodes-base.webhook",
                    "parameters": {"path": "demo", "httpMethod": "POST"},
                }
            ],
        }
        with patch("connector_n8n.commands.get_workflow_webhooks.api_request") as mock_api:
            mock_api.return_value = (workflow, 200, None)
            cmd = GetWorkflowWebhooks(
                "https://n8n.example.com/api/v1",
                "api-key",
                "wf-1",
                "https://n8n.example.com",
            )
            result = cmd.execute({}, {})
            body = json.loads(result["command_response"]["body"])
            assert result["error"] is None
            assert body["webhooks"][0]["production_url"] == "https://n8n.example.com/webhook/demo"
