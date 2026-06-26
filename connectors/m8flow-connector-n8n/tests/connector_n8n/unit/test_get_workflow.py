"""Unit tests for GetWorkflow command."""
from unittest.mock import patch

from connector_n8n.commands.get_workflow import GetWorkflow

BASE_URL = "https://n8n.example.com"


class TestGetWorkflow:
    def test_successful_get(self) -> None:
        wf = {"id": "42", "name": "Onboard", "active": True}
        with patch("connector_n8n.commands.get_workflow.api_request") as mock_req:
            mock_req.return_value = (wf, 200, None)
            cmd = GetWorkflow(BASE_URL, "key", "42")
            response = cmd.execute({}, {})
            assert response["command_response"]["parsed_body"] == wf
            assert response["error"] is None
            args = mock_req.call_args[0]
            assert args[1] == "https://n8n.example.com/api/v1/workflows/42"

    def test_missing_workflow_id(self) -> None:
        cmd = GetWorkflow(BASE_URL, "key", "")
        response = cmd.execute({}, {})
        # Errors are surfaced as data (no top-level error) so the workflow does not hang.
        assert response["error"] is None
        assert response["command_response"]["http_status"] == 400
        assert response["command_response"]["parsed_body"]["error_code"] == "N8nInvalidInput"

    def test_not_found(self) -> None:
        with patch("connector_n8n.commands.get_workflow.api_request") as mock_req:
            mock_req.return_value = (
                {},
                404,
                {"error_code": "N8nNotFoundError", "message": "n8n resource not found: workflow"},
            )
            cmd = GetWorkflow(BASE_URL, "key", "999")
            response = cmd.execute({}, {})
            assert response["error"] is None
            assert response["command_response"]["http_status"] == 404
            assert response["command_response"]["parsed_body"]["error_code"] == "N8nNotFoundError"
