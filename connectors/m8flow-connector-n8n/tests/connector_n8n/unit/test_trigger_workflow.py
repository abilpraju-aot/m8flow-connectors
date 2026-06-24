"""Unit tests for TriggerWorkflow command."""
import json
from unittest.mock import patch

from connector_n8n.commands.trigger_workflow import TriggerWorkflow

WEBHOOK_URL = "https://n8n.example.com/webhook/abc-123"


class TestTriggerWorkflow:
    def test_successful_post(self) -> None:
        result_body = {"received": True, "id": 7}
        with patch("connector_n8n.commands.trigger_workflow.call_webhook") as mock_call:
            mock_call.return_value = (result_body, 200, None)
            cmd = TriggerWorkflow(WEBHOOK_URL, payload={"customerId": 42})
            response = cmd.execute({}, {})
            assert response["command_response"] == {
                "body": json.dumps(result_body),
                "mimetype": "application/json",
                "http_status": 200,
                "parsed_body": result_body,
            }
            assert response["error"] is None
            args, kwargs = mock_call.call_args
            assert args[0] == WEBHOOK_URL
            assert args[1] == "POST"
            assert kwargs["payload"] == {"customerId": 42}
            assert kwargs["auth_type"] == "none"

    def test_header_auth_passed_through(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.call_webhook") as mock_call:
            mock_call.return_value = ({"ok": 1}, 200, None)
            cmd = TriggerWorkflow(
                WEBHOOK_URL,
                auth_type="header",
                auth_header_name="Authorization",
                auth_header_value="Bearer secret",
            )
            cmd.execute({}, {})
            kwargs = mock_call.call_args[1]
            assert kwargs["auth_type"] == "header"
            assert kwargs["auth_header_name"] == "Authorization"
            assert kwargs["auth_header_value"] == "Bearer secret"

    def test_basic_auth_passed_through(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.call_webhook") as mock_call:
            mock_call.return_value = ({"ok": 1}, 200, None)
            cmd = TriggerWorkflow(WEBHOOK_URL, auth_type="basic", username="user", password="pass")
            cmd.execute({}, {})
            kwargs = mock_call.call_args[1]
            assert kwargs["auth_type"] == "basic"
            assert kwargs["username"] == "user"
            assert kwargs["password"] == "pass"

    def test_non_json_text_response(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.call_webhook") as mock_call:
            mock_call.return_value = ("OK", 200, None)
            cmd = TriggerWorkflow(WEBHOOK_URL)
            response = cmd.execute({}, {})
            assert response["command_response"]["parsed_body"] == "OK"
            assert response["error"] is None

    def test_missing_webhook_url(self) -> None:
        cmd = TriggerWorkflow("")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "N8nInvalidInput"

    def test_auth_error(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.call_webhook") as mock_call:
            mock_call.return_value = (
                {},
                401,
                {"error_code": "N8nAuthError", "message": "n8n authentication failed. Check your API key."},
            )
            cmd = TriggerWorkflow(WEBHOOK_URL)
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"]["error_code"] == "N8nAuthError"
