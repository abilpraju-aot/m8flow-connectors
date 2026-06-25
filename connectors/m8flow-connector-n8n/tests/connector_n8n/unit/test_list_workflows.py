"""Unit tests for ListWorkflows command."""
import json
from unittest.mock import patch

from connector_n8n.commands.list_workflows import ListWorkflows


class TestListWorkflows:
    def test_successful_list(self) -> None:
        api_response = {
            "data": [{"id": "wf1", "name": "Demo", "active": True, "tags": []}],
            "nextCursor": None,
        }
        with patch("connector_n8n.commands.list_workflows.api_request") as mock_api:
            mock_api.return_value = (api_response, 200, None)
            cmd = ListWorkflows("https://n8n.example.com/api/v1", "api-key")
            result = cmd.execute({}, {})
            body = json.loads(result["command_response"]["body"])
            assert result["error"] is None
            assert body["summary"][0]["id"] == "wf1"

    def test_missing_api_key(self) -> None:
        cmd = ListWorkflows("https://n8n.example.com/api/v1", "")
        result = cmd.execute({}, {})
        assert result["error"] is not None
        assert result["error"]["error_code"] == "N8nValidationError"
