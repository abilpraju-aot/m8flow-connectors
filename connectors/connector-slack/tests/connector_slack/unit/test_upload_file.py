import os
import tempfile
from unittest.mock import patch

from connector_slack.commands.upload_file import UploadFile

MODULE = "connector_slack.commands.upload_file"

GET_URL = f"{MODULE}.get_upload_url_external"
UPLOAD_BYTES = f"{MODULE}.upload_file_bytes"
COMPLETE = f"{MODULE}.complete_upload_external"


def _mock_upload_success(mock_get_url, mock_upload, mock_complete):
    """Wire up the three-step upload mocks for a happy-path scenario."""
    mock_get_url.return_value = (
        {"ok": True, "upload_url": "https://files.slack.com/upload/v1/test", "file_id": "F_TEST"},
        200, None,
    )
    mock_upload.return_value = (200, None)
    mock_complete.return_value = (
        {"ok": True, "files": [{"id": "F_TEST", "title": "report.txt"}]},
        200, None,
    )


class TestUploadFile:
    def test_successful_upload(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_upload_success(m_url, m_up, m_done)
            cmd = UploadFile("xxx", "C123", "file content here", "report.txt")
            response = cmd.execute({}, {})

            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None

            m_url.assert_called_once_with("xxx", "report.txt", len(b"file content here"))
            m_up.assert_called_once_with(
                "https://files.slack.com/upload/v1/test", "report.txt", b"file content here",
            )
            m_done.assert_called_once_with(
                "xxx", "F_TEST", "report.txt", channel_id="C123", initial_comment="",
            )

    def test_successful_upload_with_initial_comment(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_upload_success(m_url, m_up, m_done)
            cmd = UploadFile("xxx", "U123", "data", "data.txt", initial_comment="See attached")
            response = cmd.execute({}, {})

            assert response["command_response"]["http_status"] == 200
            m_done.assert_called_once_with(
                "xxx", "F_TEST", "data.txt", channel_id="U123", initial_comment="See attached",
            )

    def test_get_url_error_returns_early(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = (
                {}, 403,
                {"error_code": "SlackPermissionError", "message": "missing_scope"},
            )
            cmd = UploadFile("xxx", "C123", "content", "x.txt")
            response = cmd.execute({}, {})

            assert response["command_response"]["http_status"] == 403
            assert response["error"]["error_code"] == "SlackPermissionError"
            m_up.assert_not_called()
            m_done.assert_not_called()

    def test_upload_bytes_error_returns_early(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = (
                {"ok": True, "upload_url": "https://files.slack.com/upload/v1/x", "file_id": "F1"},
                200, None,
            )
            m_up.return_value = (500, {"error_code": "SlackUploadFailed", "message": "HTTP 500"})

            cmd = UploadFile("xxx", "C123", "content", "x.txt")
            response = cmd.execute({}, {})

            assert response["error"]["error_code"] == "SlackUploadFailed"
            m_done.assert_not_called()

    def test_complete_error_returned(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = (
                {"ok": True, "upload_url": "https://files.slack.com/upload/v1/x", "file_id": "F1"},
                200, None,
            )
            m_up.return_value = (200, None)
            m_done.return_value = (
                {}, 400,
                {"error_code": "SlackMessageFailed", "message": "channel_not_found"},
            )
            cmd = UploadFile("xxx", "C123", "content", "x.txt")
            response = cmd.execute({}, {})

            assert response["error"]["error_code"] == "SlackMessageFailed"

    def test_upload_over_limit_returns_error_and_does_not_call_api(self) -> None:
        with patch(GET_URL) as m_url:
            with patch(f"{MODULE}._get_upload_limit_bytes", return_value=10):
                cmd = UploadFile("xxx", "C123", "x" * 20, "big.txt")
                response = cmd.execute({}, {})
                assert response["error"] is not None
                assert response["error"]["error_code"] == "SlackFileTooLarge"
                assert "too large" in response["error"]["message"].lower()
                m_url.assert_not_called()

    def test_upload_at_limit_succeeds(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_upload_success(m_url, m_up, m_done)
            with patch(f"{MODULE}._get_upload_limit_bytes", return_value=5):
                cmd = UploadFile("xxx", "C123", "12345", "exact.txt")
                response = cmd.execute({}, {})
                assert response["command_response"]["http_status"] == 200
                assert response["error"] is None
                m_up.assert_called_once()
                assert m_up.call_args[0][2] == b"12345"

    def test_upload_via_path_under_allowed_dir_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "from_path.txt")
            with open(file_path, "wb") as f:
                f.write(b"content from path")
            with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
                _mock_upload_success(m_url, m_up, m_done)
                with patch(f"{MODULE}.ALLOWED_ATTACHMENTS_DIR", tmpdir):
                    with patch(f"{MODULE}._get_upload_limit_bytes", return_value=1024):
                        cmd = UploadFile("xxx", "C123", "", "from_path.txt", path=file_path)
                        response = cmd.execute({}, {})
                        assert response["command_response"]["http_status"] == 200
                        assert response["error"] is None
                        m_up.assert_called_once()
                        assert m_up.call_args[0][2] == b"content from path"

    def test_upload_path_outside_allowed_dir_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as allowed_dir:
            with tempfile.TemporaryDirectory() as other_dir:
                outside_path = os.path.join(other_dir, "outside.txt")
                with open(outside_path, "wb") as f:
                    f.write(b"outside")
                with patch(GET_URL) as m_url:
                    with patch(f"{MODULE}.ALLOWED_ATTACHMENTS_DIR", allowed_dir):
                        cmd = UploadFile("xxx", "C123", "", "x.txt", path=outside_path)
                        response = cmd.execute({}, {})
                        assert response["error"] is not None
                        assert response["error"]["error_code"] == "SlackFileInvalidPath"
                        m_url.assert_not_called()

    def test_empty_content_and_no_path_returns_error(self) -> None:
        with patch(GET_URL) as m_url:
            cmd = UploadFile("xxx", "C123", "", "x.txt")
            response = cmd.execute({}, {})
            assert response["error"] is not None
            assert response["error"]["error_code"] == "SlackMissingContent"
            m_url.assert_not_called()
