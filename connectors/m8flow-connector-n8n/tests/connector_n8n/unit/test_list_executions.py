"""Unit tests for ListExecutions command."""
from unittest.mock import patch

from connector_n8n.commands.list_executions import ListExecutions

SAMPLE = {"data": [{"id": "exec-1", "status": "success"}, {"id": "exec-2", "status": "error"}]}


class TestListExecutions:
    def test_lists_executions(self) -> None:
        with patch("connector_n8n.commands.list_executions.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListExecutions("https://n8n.example.com", "api-key")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            call_args = mock_req.call_args
            assert call_args[0][1] == "https://n8n.example.com/api/v1/executions"
            assert call_args[1]["params"]["limit"] == 100
            assert "workflowId" not in call_args[1]["params"]

    def test_filters_applied(self) -> None:
        with patch("connector_n8n.commands.list_executions.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListExecutions("https://n8n.example.com", "api-key", workflow_id="42", status="error")
            cmd.execute({}, {})
            params = mock_req.call_args[1]["params"]
            assert params["workflowId"] == "42"
            assert params["status"] == "error"

    def test_missing_config_is_error(self) -> None:
        with patch("connector_n8n.commands.list_executions.request_with_retry") as mock_req:
            cmd = ListExecutions("https://n8n.example.com", "")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nConfigError"
            mock_req.assert_not_called()

    def test_auth_error(self) -> None:
        with patch("connector_n8n.commands.list_executions.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 403, {"error_code": "N8nAuthError", "message": "n8n authentication failed."})
            cmd = ListExecutions("https://n8n.example.com", "bad-key")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 403
            assert response["error"]["error_code"] == "N8nAuthError"
