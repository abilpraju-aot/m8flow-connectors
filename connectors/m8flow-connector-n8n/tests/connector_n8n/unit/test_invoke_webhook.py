"""Unit tests for InvokeWebhook command."""
import json
from unittest.mock import patch

from connector_n8n.commands.invoke_webhook import InvokeWebhook


class TestInvokeWebhook:
    def test_successful_invoke(self) -> None:
        response = {"message": "ok"}
        with patch("connector_n8n.commands.invoke_webhook.invoke_webhook") as mock_invoke:
            mock_invoke.return_value = (response, 200, None)
            cmd = InvokeWebhook("https://n8n.example.com/webhook/test", payload='{"message": "hello"}')
            result = cmd.execute({}, {})
            assert result["error"] is None
            assert result["command_response"]["http_status"] == 200
            assert json.loads(result["command_response"]["body"]) == response

    def test_invalid_payload(self) -> None:
        cmd = InvokeWebhook("https://n8n.example.com/webhook/test", payload="not-json")
        result = cmd.execute({}, {})
        assert result["error"] is not None
        assert result["error"]["error_code"] == "N8nValidationError"

    def test_webhook_error(self) -> None:
        with patch("connector_n8n.commands.invoke_webhook.invoke_webhook") as mock_invoke:
            mock_invoke.return_value = (
                {},
                404,
                {"error_code": "N8nWebhookNotFound", "message": "webhook not registered"},
            )
            cmd = InvokeWebhook("https://n8n.example.com/webhook/missing")
            result = cmd.execute({}, {})
            assert result["error"] is not None
            assert result["error"]["error_code"] == "N8nWebhookNotFound"
