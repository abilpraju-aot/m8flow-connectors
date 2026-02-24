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
