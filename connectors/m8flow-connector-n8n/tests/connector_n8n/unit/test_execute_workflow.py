"""Unit tests for ExecuteWorkflow and GetExecution commands."""
import json
from unittest.mock import patch

from connector_n8n.commands.execute_workflow import ExecuteWorkflow
from connector_n8n.commands.get_execution import GetExecution


class TestExecuteWorkflow:
    def test_successful_execute(self) -> None:
        api_response = {"executionId": "exec-1", "status": "running"}
        with patch("connector_n8n.commands.execute_workflow.api_request") as mock_api:
            mock_api.return_value = (api_response, 200, None)
            cmd = ExecuteWorkflow(
                "https://n8n.example.com/api/v1",
                "api-key",
                "wf-1",
                input_data='{"message": "hello"}',
            )
            result = cmd.execute({}, {})
            assert result["error"] is None
            assert json.loads(result["command_response"]["body"])["executionId"] == "exec-1"


class TestGetExecution:
    def test_successful_get(self) -> None:
        api_response = {"id": "exec-1", "status": "success", "finished": True}
        with patch("connector_n8n.commands.get_execution.api_request") as mock_api:
            mock_api.return_value = (api_response, 200, None)
            cmd = GetExecution("https://n8n.example.com/api/v1", "api-key", "exec-1", include_data="true")
            result = cmd.execute({}, {})
            assert result["error"] is None
            body = json.loads(result["command_response"]["body"])
            assert body["status"] == "success"
