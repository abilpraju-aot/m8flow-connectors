import os
import tempfile
from unittest.mock import patch

from connector_slack.commands.upload_file import UploadFile


class TestUploadFile:
    def test_successful_upload(self) -> None:
        success_response = {"ok": True, "file": {"id": "F123", "name": "report.txt"}}
        with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
            mock_post.return_value = (success_response, 200, None)
            cmd = UploadFile("xxx", "C123", "file content here", "report.txt")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_post.assert_called_once()
            files = mock_post.call_args[0][2]
            assert "file" in files
            assert files["file"][0] == "report.txt"
            assert files["file"][1] == b"file content here"
            data = mock_post.call_args[0][3]
            assert data["channels"] == "C123"
            assert "initial_comment" not in data or data.get("initial_comment") == ""

    def test_successful_upload_with_initial_comment(self) -> None:
        success_response = {"ok": True, "file": {"id": "F456"}}
        with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
            mock_post.return_value = (success_response, 200, None)
            cmd = UploadFile("xxx", "U123", "data", "data.txt", initial_comment="See attached")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            data = mock_post.call_args[0][3]
            assert data["channels"] == "U123"
            assert data["initial_comment"] == "See attached"

    def test_error_from_slack(self) -> None:
        with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
            mock_post.return_value = (
                {},
                403,
                {"error_code": "SlackPermissionError", "message": "Slack permission error: missing_scope"},
            )
            cmd = UploadFile("xxx", "C123", "content", "x.txt")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 403
            assert response["error"]["error_code"] == "SlackPermissionError"

    def test_upload_over_limit_returns_error_and_does_not_call_api(self) -> None:
        with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
            with patch("connector_slack.commands.upload_file._get_upload_limit_bytes", return_value=10):
                cmd = UploadFile("xxx", "C123", "x" * 20, "big.txt")
                response = cmd.execute({}, {})
                assert response["error"] is not None
                assert response["error"]["error_code"] == "SlackFileTooLarge"
                assert "too large" in response["error"]["message"].lower()
                mock_post.assert_not_called()

    def test_upload_at_limit_succeeds_and_calls_api(self) -> None:
        success_response = {"ok": True, "file": {"id": "F789"}}
        with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
            mock_post.return_value = (success_response, 200, None)
            with patch("connector_slack.commands.upload_file._get_upload_limit_bytes", return_value=5):
                cmd = UploadFile("xxx", "C123", "12345", "exact.txt")
                response = cmd.execute({}, {})
                assert response["command_response"]["http_status"] == 200
                assert response["error"] is None
                mock_post.assert_called_once()
                assert mock_post.call_args[0][2]["file"][1] == b"12345"

    def test_upload_via_path_under_allowed_dir_succeeds(self) -> None:
        success_response = {"ok": True, "file": {"id": "F_PATH"}}
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "from_path.txt")
            with open(file_path, "wb") as f:
                f.write(b"content from path")
            with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
                mock_post.return_value = (success_response, 200, None)
                with patch("connector_slack.commands.upload_file.ALLOWED_ATTACHMENTS_DIR", tmpdir):
                    with patch("connector_slack.commands.upload_file._get_upload_limit_bytes", return_value=1024):
                        cmd = UploadFile("xxx", "C123", "", "from_path.txt", path=file_path)
                        response = cmd.execute({}, {})
                        assert response["command_response"]["http_status"] == 200
                        assert response["error"] is None
                        mock_post.assert_called_once()
                        assert mock_post.call_args[0][2]["file"][1] == b"content from path"
                        assert mock_post.call_args[0][2]["file"][0] == "from_path.txt"

    def test_upload_path_outside_allowed_dir_returns_error_and_does_not_call_api(self) -> None:
        with tempfile.TemporaryDirectory() as allowed_dir:
            with tempfile.TemporaryDirectory() as other_dir:
                outside_path = os.path.join(other_dir, "outside.txt")
                with open(outside_path, "wb") as f:
                    f.write(b"outside")
                with patch("connector_slack.commands.upload_file.post_multipart") as mock_post:
                    with patch("connector_slack.commands.upload_file.ALLOWED_ATTACHMENTS_DIR", allowed_dir):
                        cmd = UploadFile("xxx", "C123", "", "x.txt", path=outside_path)
                        response = cmd.execute({}, {})
                        assert response["error"] is not None
                        assert response["error"]["error_code"] == "SlackFileInvalidPath"
                        assert "under" in response["error"]["message"].lower() or "path" in response["error"]["message"].lower()
                        mock_post.assert_not_called()
