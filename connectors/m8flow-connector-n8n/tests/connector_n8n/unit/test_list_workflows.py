"""Unit tests for ListWorkflows command."""
from unittest.mock import patch

from connector_n8n.commands.list_workflows import ListWorkflows

SAMPLE = {"data": [{"id": "1", "name": "Lead enrichment", "active": True}]}


class TestListWorkflows:
    def test_lists_workflows(self) -> None:
        with patch("connector_n8n.commands.list_workflows.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListWorkflows("https://n8n.example.com", "api-key")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["command_response"]["parsed_body"] == SAMPLE
            assert response["error"] is None
            call_args = mock_req.call_args
            assert call_args[0][1] == "https://n8n.example.com/api/v1/workflows"
            assert call_args[1]["headers"]["X-N8N-API-KEY"] == "api-key"
            assert call_args[1]["params"]["limit"] == 100

    def test_active_filter_applied(self) -> None:
        with patch("connector_n8n.commands.list_workflows.request_with_retry") as mock_req:
            mock_req.return_value = (SAMPLE, 200, None)
            cmd = ListWorkflows("https://n8n.example.com", "api-key", active="true")
            cmd.execute({}, {})
            assert mock_req.call_args[1]["params"]["active"] == "true"

    def test_missing_config_is_error(self) -> None:
        with patch("connector_n8n.commands.list_workflows.request_with_retry") as mock_req:
            cmd = ListWorkflows("", "api-key")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "N8nConfigError"
            mock_req.assert_not_called()

    def test_auth_error(self) -> None:
        with patch("connector_n8n.commands.list_workflows.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 401, {"error_code": "N8nAuthError", "message": "n8n authentication failed."})
            cmd = ListWorkflows("https://n8n.example.com", "bad-key")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"]["error_code"] == "N8nAuthError"

    def test_not_found(self) -> None:
        with patch("connector_n8n.commands.list_workflows.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 404, {"error_code": "N8nNotFoundError", "message": "n8n resource not found"})
            cmd = ListWorkflows("https://n8n.example.com", "api-key")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 404
            assert response["error"]["error_code"] == "N8nNotFoundError"
