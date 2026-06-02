"""Unit tests for the shared n8n client: auth, request, error mapping, and retry."""
import logging
from unittest.mock import MagicMock
from unittest.mock import patch

import requests
from connector_n8n import n8n_client


def _resp(status: int, json_body: object = None, content_type: str = "application/json", raw: bytes | None = None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.headers = {"Content-Type": content_type}
    if raw is not None:
        resp.content = raw
    else:
        resp.content = b"{}" if json_body is not None else b""
    resp.json.return_value = json_body if json_body is not None else {}
    return resp


class TestBuildAuth:
    def test_none(self) -> None:
        headers, basic, error = n8n_client.build_auth("none")
        assert headers == {} and basic is None and error is None

    def test_header(self) -> None:
        headers, basic, error = n8n_client.build_auth("header", api_key="k")
        assert headers["X-N8N-API-KEY"] == "k" and error is None

    def test_header_custom_name(self) -> None:
        headers, _basic, _error = n8n_client.build_auth("header", api_key="k", auth_header_name="X-Custom")
        assert headers["X-Custom"] == "k"

    def test_header_missing_key(self) -> None:
        _headers, _basic, error = n8n_client.build_auth("header")
        assert error is not None and error["error_code"] == "N8nConfigError"

    def test_bearer(self) -> None:
        headers, _basic, error = n8n_client.build_auth("bearer", bearer_token="t")  # noqa: S106
        assert headers["Authorization"] == "Bearer t" and error is None

    def test_basic(self) -> None:
        _headers, basic, error = n8n_client.build_auth("basic", basic_username="u", basic_password="p")  # noqa: S106
        assert basic == ("u", "p") and error is None

    def test_basic_missing_password(self) -> None:
        _headers, _basic, error = n8n_client.build_auth("basic", basic_username="u")
        assert error is not None and error["error_code"] == "N8nConfigError"

    def test_unknown_type(self) -> None:
        _headers, _basic, error = n8n_client.build_auth("oauth")
        assert error is not None and error["error_code"] == "N8nConfigError"


class TestRequestJson:
    def test_success(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request") as mock_req:
            mock_req.return_value = _resp(200, {"ok": True})
            body, status, error = n8n_client.request_json("POST", "https://n8n/webhook", json_body={"a": 1})
            assert body == {"ok": True} and status == 200 and error is None

    def test_empty_success_body(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request") as mock_req:
            mock_req.return_value = _resp(200, None, content_type="text/plain")
            body, status, error = n8n_client.request_json("POST", "https://n8n/webhook")
            assert body == {} and status == 200 and error is None

    def test_non_json_success_is_invalid_response(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request") as mock_req:
            mock_req.return_value = _resp(200, None, content_type="text/html", raw=b"<html></html>")
            _body, _status, error = n8n_client.request_json("GET", "https://n8n/webhook")
            assert error is not None and error["error_code"] == "N8nInvalidResponse"

    def test_auth_error_mapping(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request") as mock_req:
            mock_req.return_value = _resp(401, {"message": "unauthorized"})
            _body, status, error = n8n_client.request_json("GET", "https://n8n/api")
            assert status == 401 and error["error_code"] == "N8nAuthError"

    def test_not_found_mapping(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request") as mock_req:
            mock_req.return_value = _resp(404, {"message": "missing"})
            _body, status, error = n8n_client.request_json("GET", "https://n8n/api")
            assert status == 404 and error["error_code"] == "N8nNotFoundError"

    def test_server_error_is_execution_failed(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request") as mock_req:
            mock_req.return_value = _resp(500, {"message": "boom"})
            _body, status, error = n8n_client.request_json("POST", "https://n8n/webhook")
            assert status == 500 and error["error_code"] == "N8nExecutionFailed"

    def test_timeout_mapping(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request", side_effect=requests.Timeout()):
            _body, status, error = n8n_client.request_json("POST", "https://n8n/webhook", timeout=5)
            assert status == 504 and error["error_code"] == "N8nTimeoutError"

    def test_transport_error_mapping(self) -> None:
        with patch("connector_n8n.n8n_client.requests.request", side_effect=requests.ConnectionError("down")):
            _body, status, error = n8n_client.request_json("POST", "https://n8n/webhook")
            assert status == 500 and error["error_code"] == "ConnectionError"


class TestRequestWithRetry:
    def test_retries_on_5xx_then_succeeds(self) -> None:
        with patch("connector_n8n.n8n_client.request_json") as mock_one:
            mock_one.side_effect = [
                ({}, 503, {"error_code": "N8nExecutionFailed", "message": "x"}),
                ({"ok": True}, 200, None),
            ]
            body, status, error = n8n_client.request_with_retry("POST", "https://n8n/webhook", max_retries=2)
            assert status == 200 and error is None and body == {"ok": True}
            assert mock_one.call_count == 2

    def test_does_not_retry_on_4xx(self) -> None:
        with patch("connector_n8n.n8n_client.request_json") as mock_one:
            mock_one.return_value = ({}, 401, {"error_code": "N8nAuthError", "message": "x"})
            _body, status, _error = n8n_client.request_with_retry("GET", "https://n8n/api", max_retries=3)
            assert status == 401
            assert mock_one.call_count == 1

    def test_exhausts_retries(self) -> None:
        with patch("connector_n8n.n8n_client.request_json") as mock_one:
            mock_one.return_value = ({}, 504, {"error_code": "N8nTimeoutError", "message": "x"})
            _body, status, error = n8n_client.request_with_retry("POST", "https://n8n/webhook", max_retries=2)
            assert status == 504 and error["error_code"] == "N8nTimeoutError"
            assert mock_one.call_count == 3  # initial + 2 retries


class TestSecretSafety:
    def test_credentials_never_logged(self, caplog) -> None:  # type: ignore[no-untyped-def]
        with caplog.at_level(logging.DEBUG, logger="connector_n8n.n8n_client"):
            with patch("connector_n8n.n8n_client.requests.request") as mock_req:
                mock_req.return_value = _resp(401, {"message": "unauthorized"})
                headers, _basic, _error = n8n_client.build_auth("header", api_key="super-secret-key")
                n8n_client.request_json("GET", "https://n8n/api", headers=headers)
        assert "super-secret-key" not in caplog.text
