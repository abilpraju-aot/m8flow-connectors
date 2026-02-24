"""Negative tests for invalid token and missing permissions (Slack error mapping)."""
from unittest.mock import patch

from connector_slack.slack_client import post_json, post_multipart


class TestSlackAuthErrors:
    def test_invalid_auth_returns_slack_auth_error(self) -> None:
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.headers = {"Content-Type": "application/json"}
            mock_post.return_value.json.return_value = {"ok": False, "error": "invalid_auth"}
            _body, status, error = post_json("https://slack.com/api/chat.postMessage", "token", {"channel": "C1", "text": "x"})
            assert status == 401
            assert error is not None
            assert error["error_code"] == "SlackAuthError"
            assert "authentication failed" in error["message"].lower() or "token was revoked" in error["message"]

    def test_token_revoked_returns_slack_auth_error(self) -> None:
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.headers = {"Content-Type": "application/json"}
            mock_post.return_value.json.return_value = {"ok": False, "error": "token_revoked"}
            _body, status, error = post_json("https://slack.com/api/chat.postMessage", "token", {"channel": "C1", "text": "x"})
            assert status == 401
            assert error is not None
            assert error["error_code"] == "SlackAuthError"


class TestSlackPermissionErrors:
    def test_missing_scope_returns_slack_permission_error(self) -> None:
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.headers = {"Content-Type": "application/json"}
            mock_post.return_value.json.return_value = {
                "ok": False,
                "error": "missing_scope",
                "response_metadata": {"messages": ["required scope: files:write"]},
            }
            _body, status, error = post_json("https://slack.com/api/chat.postMessage", "token", {"channel": "C1", "text": "x"})
            assert status == 403
            assert error is not None
            assert error["error_code"] == "SlackPermissionError"
            assert "required scope" in error["message"] or "permission" in error["message"].lower()


class TestSlackErrorMappingInUpload:
    def test_invalid_auth_on_upload_returns_slack_auth_error(self) -> None:
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.headers = {"Content-Type": "application/json"}
            mock_post.return_value.json.return_value = {"ok": False, "error": "invalid_auth"}
            _body, status, error = post_multipart(
                "https://slack.com/api/files.upload", "token", {"file": ("x.txt", b"data")}, {"channels": "C1"}
            )
            assert status == 401
            assert error is not None
            assert error["error_code"] == "SlackAuthError"
