import os
from unittest.mock import patch

from connector_slack.commands.upload_file import (
    UPLOAD_LIMIT_ENV,
    UploadFile,
    _get_upload_limit_bytes,
)

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


class TestUploadFileSizeLimit:
    """Tests for per-file size limit enforcement."""

    def test_content_exceeds_limit(self) -> None:
        big_content = "x" * (51 * 1024 * 1024)
        r = UploadFile("tok", "C1", big_content, "big.txt").execute({}, {})
        assert r["error"] is not None
        assert r["error"]["error_code"] == "SlackUploadValidation"
        assert "too large" in r["error"]["message"]

    def test_content_within_limit(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            r = UploadFile("tok", "C1", "small", "ok.txt").execute({}, {})
            assert r["error"] is None

    def test_env_var_overrides_default_limit(self) -> None:
        with patch.dict(os.environ, {UPLOAD_LIMIT_ENV: "1"}):
            limit = _get_upload_limit_bytes()
            assert limit == 1 * 1024 * 1024

    def test_env_var_clamped_to_hard_max(self) -> None:
        with patch.dict(os.environ, {UPLOAD_LIMIT_ENV: "999"}):
            limit = _get_upload_limit_bytes()
            assert limit == 100 * 1024 * 1024

    def test_env_var_invalid_falls_back_to_default(self) -> None:
        with patch.dict(os.environ, {UPLOAD_LIMIT_ENV: "notanumber"}):
            limit = _get_upload_limit_bytes()
            assert limit == 50 * 1024 * 1024

    def test_env_var_zero_falls_back_to_default(self) -> None:
        with patch.dict(os.environ, {UPLOAD_LIMIT_ENV: "0"}):
            limit = _get_upload_limit_bytes()
            assert limit == 50 * 1024 * 1024


class TestUploadFileFromPath:
    """Tests for filepath-based upload."""

    def _patch_allowed_dir(self, tmpdir: str):
        return patch(f"{MODULE}.ALLOWED_UPLOAD_DIR", tmpdir)

    def test_filepath_success(self, tmp_path) -> None:
        file = tmp_path / "report.pdf"
        file.write_bytes(b"PDF_CONTENT")
        allowed = str(tmp_path)

        with (
            self._patch_allowed_dir(allowed),
            patch(GET_URL) as m_url,
            patch(UPLOAD_BYTES) as m_up,
            patch(COMPLETE) as m_done,
        ):
            _mock_success(m_url, m_up, m_done)
            r = UploadFile(
                "tok", "C1", filename="report.pdf",
                filepath=str(file),
            ).execute({}, {})

            assert r["error"] is None
            m_url.assert_called_once_with("tok", "report.pdf", 11)
            m_up.assert_called_once_with(
                "https://files.slack.com/upload/v1/abc", "report.pdf", b"PDF_CONTENT",
            )

    def test_filepath_uses_basename_when_no_filename(self, tmp_path) -> None:
        file = tmp_path / "auto_name.csv"
        file.write_bytes(b"a,b")
        allowed = str(tmp_path)

        with (
            self._patch_allowed_dir(allowed),
            patch(GET_URL) as m_url,
            patch(UPLOAD_BYTES) as m_up,
            patch(COMPLETE) as m_done,
        ):
            _mock_success(m_url, m_up, m_done)
            UploadFile("tok", "C1", filepath=str(file)).execute({}, {})
            assert m_url.call_args[0][1] == "auto_name.csv"

    def test_filepath_outside_allowed_dir(self, tmp_path) -> None:
        allowed = str(tmp_path / "safe")
        (tmp_path / "safe").mkdir()
        outside = tmp_path / "evil.txt"
        outside.write_bytes(b"bad")

        with self._patch_allowed_dir(allowed):
            r = UploadFile("tok", "C1", filepath=str(outside)).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "SlackUploadValidation"

    def test_filepath_traversal_rejected(self, tmp_path) -> None:
        allowed = str(tmp_path / "uploads")
        (tmp_path / "uploads").mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")
        traversal = str(tmp_path / "uploads" / ".." / "secret.txt")

        with self._patch_allowed_dir(allowed):
            r = UploadFile("tok", "C1", filepath=traversal).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "SlackUploadValidation"

    def test_filepath_file_not_found(self, tmp_path) -> None:
        allowed = str(tmp_path)
        missing = str(tmp_path / "nope.txt")

        with self._patch_allowed_dir(allowed):
            r = UploadFile("tok", "C1", filepath=missing).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "SlackFileNotFound"

    def test_filepath_too_large(self, tmp_path) -> None:
        allowed = str(tmp_path)
        big = tmp_path / "huge.bin"
        big.write_bytes(b"x" * 10)

        with (
            self._patch_allowed_dir(allowed),
            patch(f"{MODULE}._get_upload_limit_bytes", return_value=5),
        ):
            r = UploadFile("tok", "C1", filepath=str(big)).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "SlackUploadValidation"
            assert "too large" in r["error"]["message"]

    def test_filepath_relative_path_rejected(self) -> None:
        r = UploadFile("tok", "C1", filepath="relative/path.txt").execute({}, {})
        assert r["error"] is not None
        assert r["error"]["error_code"] == "SlackUploadValidation"
