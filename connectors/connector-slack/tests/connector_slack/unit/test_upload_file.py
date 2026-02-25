from unittest.mock import patch

from connector_slack.commands.upload_file import UploadFile

MODULE = "connector_slack.commands.upload_file"
GET_URL = f"{MODULE}.get_upload_url_external"
UPLOAD_BYTES = f"{MODULE}.upload_file_bytes"
COMPLETE = f"{MODULE}.complete_upload_external"


def _mock_success(m_url, m_up, m_done):
    m_url.return_value = (
        {"ok": True, "upload_url": "https://files.slack.com/upload/v1/abc", "file_id": "F1"},
        200, None,
    )
    m_up.return_value = (200, None)
    m_done.return_value = ({"ok": True, "files": [{"id": "F1", "title": "t.txt"}]}, 200, None)


class TestUploadFile:
    def test_success(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            r = UploadFile("tok", "C1", "hello", "t.txt", "comment").execute({}, {})
            assert r["command_response"]["http_status"] == 200
            assert r["error"] is None
            m_url.assert_called_once_with("tok", "t.txt", 5)
            m_up.assert_called_once_with("https://files.slack.com/upload/v1/abc", "t.txt", b"hello")
            m_done.assert_called_once_with("tok", "F1", "t.txt", channel_id="C1", initial_comment="comment")

    def test_empty_content_returns_error(self) -> None:
        with patch(GET_URL) as m_url:
            r = UploadFile("tok", "C1", "", "t.txt").execute({}, {})
            assert r["error"]["error_code"] == "SlackMissingContent"
            m_url.assert_not_called()

    def test_get_url_error_returns_early(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = ({}, 403, {"error_code": "SlackPermissionError", "message": "missing_scope"})
            r = UploadFile("tok", "C1", "data", "x.txt").execute({}, {})
            assert r["error"]["error_code"] == "SlackPermissionError"
            m_up.assert_not_called()
            m_done.assert_not_called()

    def test_upload_bytes_error_returns_early(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = (
                {"ok": True, "upload_url": "https://x", "file_id": "F1"}, 200, None,
            )
            m_up.return_value = (500, {"error_code": "SlackUploadFailed", "message": "HTTP 500"})
            r = UploadFile("tok", "C1", "data", "x.txt").execute({}, {})
            assert r["error"]["error_code"] == "SlackUploadFailed"
            m_done.assert_not_called()

    def test_complete_error_returned(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = (
                {"ok": True, "upload_url": "https://x", "file_id": "F1"}, 200, None,
            )
            m_up.return_value = (200, None)
            m_done.return_value = ({}, 400, {"error_code": "SlackMessageFailed", "message": "channel_not_found"})
            r = UploadFile("tok", "C1", "data", "x.txt").execute({}, {})
            assert r["error"]["error_code"] == "SlackMessageFailed"

    def test_default_filename(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            UploadFile("tok", "C1", "data").execute({}, {})
            assert m_url.call_args[0][1] == "upload.txt"
