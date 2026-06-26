"""Unit tests for GetExecution command."""
from unittest.mock import patch

from connector_n8n.commands.get_execution import GetExecution

BASE_URL = "https://n8n.example.com"


class TestGetExecution:
    def test_successful_get(self) -> None:
        execution = {"id": "10", "finished": True, "status": "success"}
        with patch("connector_n8n.commands.get_execution.api_request") as mock_req:
            mock_req.return_value = (execution, 200, None)
            cmd = GetExecution(BASE_URL, "key", "10")
            response = cmd.execute({}, {})
            assert response["command_response"]["parsed_body"] == execution
            assert response["error"] is None
            args = mock_req.call_args[0]
            assert args[1] == "https://n8n.example.com/api/v1/executions/10"
            params = mock_req.call_args[1]["params"]
            assert "includeData" not in params

    def test_include_data(self) -> None:
        with patch("connector_n8n.commands.get_execution.api_request") as mock_req:
            mock_req.return_value = ({"id": "10"}, 200, None)
            cmd = GetExecution(BASE_URL, "key", "10", include_data=True)
            cmd.execute({}, {})
            params = mock_req.call_args[1]["params"]
            assert params["includeData"] == "true"

    def test_missing_execution_id(self) -> None:
        cmd = GetExecution(BASE_URL, "key", "")
        response = cmd.execute({}, {})
        # Errors are surfaced as data (no top-level error) so the workflow does not hang.
        assert response["error"] is None
        assert response["command_response"]["http_status"] == 400
        assert response["command_response"]["parsed_body"]["error_code"] == "N8nInvalidInput"

    def test_not_found(self) -> None:
        with patch("connector_n8n.commands.get_execution.api_request") as mock_req:
            mock_req.return_value = (
                {},
                404,
                {"error_code": "N8nNotFoundError", "message": "n8n resource not found: execution"},
            )
            cmd = GetExecution(BASE_URL, "key", "999")
            response = cmd.execute({}, {})
            assert response["error"] is None
            assert response["command_response"]["http_status"] == 404
            assert response["command_response"]["parsed_body"]["error_code"] == "N8nNotFoundError"
