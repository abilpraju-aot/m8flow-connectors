"""Unit tests for ListExecutions command."""
from unittest.mock import patch

from connector_n8n.commands.list_executions import ListExecutions

BASE_URL = "https://n8n.example.com"
SAMPLE = {"data": [{"id": "10", "finished": True, "status": "success"}], "nextCursor": None}


class TestListExecutions:
    def test_list_all(self) -> None:
        with patch("connector_n8n.commands.list_executions.api_request") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListExecutions(BASE_URL, "key")
            response = cmd.execute({}, {})
            assert response["error"] is None
            args = mock_req.call_args[0]
            assert args[1] == "https://n8n.example.com/api/v1/executions"
            params = mock_req.call_args[1]["params"]
            assert params == {"limit": 100}

    def test_filters(self) -> None:
        with patch("connector_n8n.commands.list_executions.api_request") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListExecutions(BASE_URL, "key", workflow_id="42", status="error", limit=20, cursor="cur")
            cmd.execute({}, {})
            params = mock_req.call_args[1]["params"]
            assert params == {"limit": 20, "workflowId": "42", "status": "error", "cursor": "cur"}

    def test_status_ignored_when_invalid(self) -> None:
        with patch("connector_n8n.commands.list_executions.api_request") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListExecutions(BASE_URL, "key", status="bogus")
            cmd.execute({}, {})
            params = mock_req.call_args[1]["params"]
            assert "status" not in params

    def test_missing_credentials(self) -> None:
        cmd = ListExecutions("", "")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "N8nInvalidInput"
