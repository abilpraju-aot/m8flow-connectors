"""Unit tests for TriggerWorkflow command."""
import json
from unittest.mock import patch

from connector_n8n.commands.trigger_workflow import TriggerWorkflow

SAMPLE_RESPONSE = {"executionId": "exec-123", "data": {"result": "ok", "summary": "AI generated text"}}


class TestTriggerWorkflow:
    def test_invokes_webhook_with_payload(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE_RESPONSE, 200, None)
            cmd = TriggerWorkflow(
                webhook_url="https://n8n.example.com/webhook/abc",
                payload=json.dumps({"name": "Ada", "score": 42}),
            )
            response = cmd.execute({}, {})

            assert response["command_response"]["http_status"] == 200
            assert response["command_response"]["parsed_body"] == SAMPLE_RESPONSE
            assert response["error"] is None
            # Request mapping: URL, method and JSON body forwarded correctly.
            call_args = mock_req.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "https://n8n.example.com/webhook/abc"
            assert call_args[1]["json_body"] == {"name": "Ada", "score": 42}

    def test_builds_url_from_base_and_path(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(base_url="https://n8n.example.com/", webhook_path="/webhook/xyz")
            cmd.execute({}, {})
            assert mock_req.call_args[0][1] == "https://n8n.example.com/webhook/xyz"

    def test_accepts_dict_payload(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc", payload={"k": "v"})
            cmd.execute({}, {})
            assert mock_req.call_args[1]["json_body"] == {"k": "v"}

    def test_missing_url_is_config_error(self) -> None:
        cmd = TriggerWorkflow(payload="{}")
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "N8nConfigError"
        assert response["command_response"]["http_status"] == 400

    def test_invalid_json_payload_is_config_error_without_http_call(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc", payload="{not json")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nConfigError"
            mock_req.assert_not_called()

    def test_header_auth_passes_api_key(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(
                webhook_url="https://n8n.example.com/webhook/abc",
                auth_type="header",
                api_key="secret-key",
            )
            cmd.execute({}, {})
            assert mock_req.call_args[1]["headers"]["X-N8N-API-KEY"] == "secret-key"

    def test_bearer_auth_passes_token(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(
                webhook_url="https://n8n.example.com/webhook/abc",
                auth_type="bearer",
                bearer_token="tok-123",  # noqa: S106
            )
            cmd.execute({}, {})
            assert mock_req.call_args[1]["headers"]["Authorization"] == "Bearer tok-123"

    def test_basic_auth_passes_tuple(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(
                webhook_url="https://n8n.example.com/webhook/abc",
                auth_type="basic",
                basic_username="user",
                basic_password="pass",  # noqa: S106
            )
            cmd.execute({}, {})
            assert mock_req.call_args[1]["basic_auth"] == ("user", "pass")

    def test_missing_auth_credential_is_config_error(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc", auth_type="header")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nConfigError"
            mock_req.assert_not_called()

    def test_auth_failure(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = (
                {},
                401,
                {"error_code": "N8nAuthError", "message": "n8n authentication failed."},
            )
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"]["error_code"] == "N8nAuthError"

    def test_timeout(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = (
                {},
                504,
                {"error_code": "N8nTimeoutError", "message": "n8n request timed out after 30s."},
            )
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nTimeoutError"

    def test_execution_failure(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = (
                {},
                500,
                {"error_code": "N8nExecutionFailed", "message": "n8n workflow/webhook execution failed: boom"},
            )
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 500
            assert response["error"]["error_code"] == "N8nExecutionFailed"

    def test_invalid_response(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = (
                {},
                200,
                {"error_code": "N8nInvalidResponse", "message": "Unreadable (non JSON) response from n8n."},
            )
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nInvalidResponse"

    def test_query_params_forwarded(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(
                webhook_url="https://n8n.example.com/webhook/abc",
                query_params=json.dumps({"source": "m8flow"}),
            )
            cmd.execute({}, {})
            assert mock_req.call_args[1]["params"] == {"source": "m8flow"}

    def test_max_retries_forwarded(self) -> None:
        with patch("connector_n8n.commands.trigger_workflow.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 200, None)
            cmd = TriggerWorkflow(webhook_url="https://n8n.example.com/webhook/abc", max_retries=3, timeout=10)
            cmd.execute({}, {})
            assert mock_req.call_args[1]["max_retries"] == 3
            assert mock_req.call_args[1]["timeout"] == 10
