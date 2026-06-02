"""Unit tests for GetExecution command."""
from unittest.mock import patch

from connector_n8n.commands.get_execution import GetExecution

SAMPLE = {"id": "exec-123", "finished": True, "status": "success", "data": {"result": 1}}


class TestGetExecution:
    def test_gets_execution(self) -> None:
        with patch("connector_n8n.commands.get_execution.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = GetExecution("https://n8n.example.com", "api-key", "exec-123")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["command_response"]["parsed_body"]["status"] == "success"
            assert response["error"] is None
            call_args = mock_req.call_args
            assert call_args[0][1] == "https://n8n.example.com/api/v1/executions/exec-123"
            assert call_args[1]["headers"]["X-N8N-API-KEY"] == "api-key"
            assert call_args[1]["params"]["includeData"] == "true"

    def test_include_data_false(self) -> None:
        with patch("connector_n8n.commands.get_execution.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = GetExecution("https://n8n.example.com", "api-key", "exec-123", include_data=False)
            cmd.execute({}, {})
            assert mock_req.call_args[1]["params"]["includeData"] == "false"

    def test_missing_execution_id_is_error(self) -> None:
        with patch("connector_n8n.commands.get_execution.request_with_retry") as mock_req:
            cmd = GetExecution("https://n8n.example.com", "api-key", "")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nConfigError"
            mock_req.assert_not_called()

    def test_not_found(self) -> None:
        with patch("connector_n8n.commands.get_execution.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 404, {"error_code": "N8nNotFoundError", "message": "n8n resource not found"})
            cmd = GetExecution("https://n8n.example.com", "api-key", "missing")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 404
            assert response["error"]["error_code"] == "N8nNotFoundError"

    def test_auth_error(self) -> None:
        with patch("connector_n8n.commands.get_execution.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 401, {"error_code": "N8nAuthError", "message": "n8n authentication failed."})
            cmd = GetExecution("https://n8n.example.com", "bad-key", "exec-123")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nAuthError"
