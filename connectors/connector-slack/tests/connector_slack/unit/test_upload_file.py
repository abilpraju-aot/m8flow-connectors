import base64
import os
from unittest.mock import patch

from connector_slack.commands.upload_file import (
    UPLOAD_LIMIT_ENV,
    UploadFile,
    _estimated_base64_decoded_size,
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
        assert r["error"]["error_code"] == "ValueError"
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
        return patch(f"{MODULE}.ATTACHMENTS_DIR", tmpdir)

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
            assert r["error"]["error_code"] == "ValueError"

    def test_filepath_traversal_rejected(self, tmp_path) -> None:
        allowed = str(tmp_path / "uploads")
        (tmp_path / "uploads").mkdir()
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")
        traversal = str(tmp_path / "uploads" / ".." / "secret.txt")

        with self._patch_allowed_dir(allowed):
            r = UploadFile("tok", "C1", filepath=traversal).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "ValueError"

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
            assert r["error"]["error_code"] == "ValueError"
            assert "too large" in r["error"]["message"]

    def test_filepath_relative_path_rejected(self) -> None:
        r = UploadFile("tok", "C1", filepath="relative/path.txt").execute({}, {})
        assert r["error"] is not None
        assert r["error"]["error_code"] == "ValueError"

    def test_filepath_prefix_overlap_rejected(self, tmp_path) -> None:
        """A dir like /slack_attachments_evil must not pass when allowed is /slack_attachments."""
        allowed = str(tmp_path / "uploads")
        (tmp_path / "uploads").mkdir()
        evil_dir = tmp_path / "uploads_evil"
        evil_dir.mkdir()
        evil_file = evil_dir / "steal.txt"
        evil_file.write_bytes(b"gotcha")

        with self._patch_allowed_dir(allowed):
            r = UploadFile("tok", "C1", filepath=str(evil_file)).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "ValueError"

    def test_filepath_oserror_caught(self, tmp_path) -> None:
        """OSError during file read must return a structured error, not a 500."""
        allowed = str(tmp_path)
        target = tmp_path / "unreadable.bin"
        target.write_bytes(b"data")

        with (
            self._patch_allowed_dir(allowed),
            patch("builtins.open", side_effect=OSError("disk I/O error")),
        ):
            r = UploadFile("tok", "C1", filepath=str(target)).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "OSError"
            assert "disk I/O error" in r["error"]["message"]
            assert "spiff__logs" in r

    def test_filepath_permission_error_caught(self, tmp_path) -> None:
        """PermissionError must return a structured error, not a 500."""
        allowed = str(tmp_path)
        target = tmp_path / "secret.bin"
        target.write_bytes(b"x")

        with (
            self._patch_allowed_dir(allowed),
            patch("builtins.open", side_effect=PermissionError("access denied")),
        ):
            r = UploadFile("tok", "C1", filepath=str(target)).execute({}, {})
            assert r["error"] is not None
            assert r["error"]["error_code"] == "PermissionError"
            assert "spiff__logs" in r


class TestUploadFileSpiffLogs:
    """Verify spiff__logs is present in all response paths."""

    def test_success_includes_logs(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            r = UploadFile("tok", "C1", "hello", "t.txt").execute({}, {})
            assert "spiff__logs" in r
            assert any("upload completed successfully" in l for l in r["spiff__logs"])

    def test_empty_content_includes_logs(self) -> None:
        r = UploadFile("tok", "C1", "", "t.txt").execute({}, {})
        assert "spiff__logs" in r

    def test_error_response_includes_logs(self) -> None:
        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            m_url.return_value = ({}, 403, {"error_code": "SlackPermissionError", "message": "missing_scope"})
            r = UploadFile("tok", "C1", "data", "x.txt").execute({}, {})
            assert "spiff__logs" in r


class TestUploadFileBase64:
    """Tests for base64 content upload."""

    def test_base64_success(self) -> None:
        """Valid base64 content uploads successfully."""
        binary_data = b"\x00\x01\x02\xff\xfe\xfd"
        b64_content = base64.b64encode(binary_data).decode("ascii")

        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            r = UploadFile(
                "tok", "C1", filename="binary.bin", content_base64=b64_content,
            ).execute({}, {})

            assert r["error"] is None
            assert r["command_response"]["http_status"] == 200
            m_url.assert_called_once_with("tok", "binary.bin", len(binary_data))
            m_up.assert_called_once_with(
                "https://files.slack.com/upload/v1/abc", "binary.bin", binary_data,
            )

    def test_base64_invalid_returns_error(self) -> None:
        """Invalid base64 content returns structured error."""
        r = UploadFile(
            "tok", "C1", filename="bad.bin", content_base64="not-valid-base64!!!",
        ).execute({}, {})

        assert r["error"] is not None
        assert r["error"]["error_code"] == "SlackInvalidBase64"
        assert "Invalid base64" in r["error"]["message"]
        assert "spiff__logs" in r

    def test_base64_exceeds_limit(self) -> None:
        """Size limit is enforced on base64 content."""
        large_data = b"x" * (51 * 1024 * 1024)
        b64_content = base64.b64encode(large_data).decode("ascii")

        r = UploadFile(
            "tok", "C1", filename="huge.bin", content_base64=b64_content,
        ).execute({}, {})

        assert r["error"] is not None
        assert r["error"]["error_code"] == "ValueError"
        assert "too large" in r["error"]["message"]

    def test_base64_default_filename(self) -> None:
        """Uses 'upload.bin' when no filename provided for base64 content."""
        b64_content = base64.b64encode(b"test data").decode("ascii")

        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            UploadFile("tok", "C1", content_base64=b64_content).execute({}, {})
            assert m_url.call_args[0][1] == "upload.bin"

    def test_base64_includes_logs(self) -> None:
        """Verify spiff__logs is present for base64 uploads."""
        b64_content = base64.b64encode(b"hello").decode("ascii")

        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            r = UploadFile("tok", "C1", content_base64=b64_content).execute({}, {})
            assert "spiff__logs" in r
            assert any("base64 mode" in log for log in r["spiff__logs"])

    def test_base64_priority_over_content(self) -> None:
        """base64 content takes priority over plain text content."""
        b64_content = base64.b64encode(b"binary").decode("ascii")

        with patch(GET_URL) as m_url, patch(UPLOAD_BYTES) as m_up, patch(COMPLETE) as m_done:
            _mock_success(m_url, m_up, m_done)
            r = UploadFile(
                "tok", "C1", content="plain text", content_base64=b64_content,
            ).execute({}, {})

            assert r["error"] is None
            m_up.assert_called_once_with(
                "https://files.slack.com/upload/v1/abc", "upload.bin", b"binary",
            )


class TestEstimatedBase64DecodedSize:
    """Tests for the _estimated_base64_decoded_size helper function."""

    def test_empty_string(self) -> None:
        assert _estimated_base64_decoded_size("") == 0

    def test_no_padding(self) -> None:
        data = b"abc"
        b64 = base64.b64encode(data).decode("ascii")
        assert _estimated_base64_decoded_size(b64) == len(data)

    def test_single_padding(self) -> None:
        data = b"ab"
        b64 = base64.b64encode(data).decode("ascii")
        assert _estimated_base64_decoded_size(b64) == len(data)

    def test_double_padding(self) -> None:
        data = b"a"
        b64 = base64.b64encode(data).decode("ascii")
        assert _estimated_base64_decoded_size(b64) == len(data)

    def test_with_whitespace(self) -> None:
        data = b"hello world"
        b64 = base64.b64encode(data).decode("ascii")
        b64_with_spaces = " ".join(b64[i:i+4] for i in range(0, len(b64), 4))
        assert _estimated_base64_decoded_size(b64_with_spaces) == len(data)
