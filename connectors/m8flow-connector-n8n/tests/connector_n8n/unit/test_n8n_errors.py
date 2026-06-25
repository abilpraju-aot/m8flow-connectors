"""Unit tests for n8n client error normalization."""
import json
from unittest.mock import MagicMock
from unittest.mock import patch

import requests
from connector_n8n.n8n_client import api_request
from connector_n8n.n8n_client import invoke_webhook


class TestN8nErrors:
    def test_api_auth_error(self) -> None:
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 401
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"message": "Unauthorized"}'
        mock_response.json.return_value = {"message": "Unauthorized"}

        with patch("connector_n8n.n8n_client.requests.request", return_value=mock_response):
            body, status, error = api_request("GET", "https://n8n.example.com/api/v1/workflows", "bad-key")
            assert status == 401
            assert error is not None
            assert error["error_code"] == "N8nAuthError"
            assert body == {}

    def test_webhook_not_registered(self) -> None:
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 404
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"message": "The requested webhook is not registered."}'
        mock_response.json.return_value = {"message": "The requested webhook is not registered."}

        with patch("connector_n8n.n8n_client.requests.request", return_value=mock_response):
            body, status, error = invoke_webhook("POST", "https://n8n.example.com/webhook/missing")
            assert status == 404
            assert error is not None
            assert error["error_code"] == "N8nWebhookNotFound"
            assert body == {}

    def test_connection_error(self) -> None:
        with patch(
            "connector_n8n.n8n_client.requests.request",
            side_effect=requests.exceptions.ConnectionError("connection refused"),
        ):
            body, status, error = api_request("GET", "https://n8n.example.com/api/v1/workflows", "key")
            assert status == 500
            assert error is not None
            assert error["error_code"] == "N8nConnectionError"
            assert body == {}

    def test_timeout_error(self) -> None:
        with patch(
            "connector_n8n.n8n_client.requests.request",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            body, status, error = invoke_webhook("POST", "https://n8n.example.com/webhook/test")
            assert status == 504
            assert error is not None
            assert error["error_code"] == "N8nTimeout"
            assert body == {}

    def test_success_json_response(self) -> None:
        mock_response = MagicMock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = json.dumps({"ok": True})
        mock_response.json.return_value = {"ok": True}

        with patch("connector_n8n.n8n_client.requests.request", return_value=mock_response):
            body, status, error = api_request("GET", "https://n8n.example.com/api/v1/workflows", "key")
            assert status == 200
            assert error is None
            assert body == {"ok": True}
