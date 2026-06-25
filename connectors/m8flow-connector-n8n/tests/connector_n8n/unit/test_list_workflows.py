"""Unit tests for ListWorkflows command."""
import json
from unittest.mock import patch

from connector_n8n.commands.list_workflows import ListWorkflows

BASE_URL = "https://n8n.example.com"
SAMPLE = {"data": [{"id": "1", "name": "Onboard", "active": True}], "nextCursor": None}


class TestListWorkflows:
    def test_list_all(self) -> None:
        with patch("connector_n8n.commands.list_workflows.api_request") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListWorkflows(BASE_URL, "key")
            response = cmd.execute({}, {})
            assert response["command_response"] == {
                "body": json.dumps(SAMPLE),
                "mimetype": "application/json",
                "http_status": 200,
                "parsed_body": SAMPLE,
            }
            assert response["error"] is None
            args = mock_req.call_args[0]
            assert args[0] == "GET"
            assert args[1] == "https://n8n.example.com/api/v1/workflows"
            assert args[2] == "key"
            params = mock_req.call_args[1]["params"]
            assert params == {"limit": 100}

    def test_active_and_cursor_filters(self) -> None:
        with patch("connector_n8n.commands.list_workflows.api_request") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListWorkflows(BASE_URL, "key", active="true", limit=50, cursor="abc")
            cmd.execute({}, {})
            params = mock_req.call_args[1]["params"]
            assert params == {"limit": 50, "active": "true", "cursor": "abc"}

    def test_active_ignored_when_invalid(self) -> None:
        with patch("connector_n8n.commands.list_workflows.api_request") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListWorkflows(BASE_URL, "key", active="maybe")
            cmd.execute({}, {})
            params = mock_req.call_args[1]["params"]
            assert "active" not in params

    def test_missing_credentials(self) -> None:
        cmd = ListWorkflows("", "")
        response = cmd.execute({}, {})
        # Errors are surfaced as data (no top-level error) so the workflow does not hang.
        assert response["error"] is None
        assert response["command_response"]["http_status"] == 400
        assert response["command_response"]["parsed_body"]["error_code"] == "N8nInvalidInput"

    def test_auth_error(self) -> None:
        with patch("connector_n8n.commands.list_workflows.api_request") as mock_req:
            mock_req.return_value = (
                {},
                401,
                {"error_code": "N8nAuthError", "message": "n8n authentication failed. Check your API key."},
            )
            cmd = ListWorkflows(BASE_URL, "bad")
            response = cmd.execute({}, {})
            assert response["error"] is None
            assert response["command_response"]["http_status"] == 401
            assert response["command_response"]["parsed_body"]["error_code"] == "N8nAuthError"
