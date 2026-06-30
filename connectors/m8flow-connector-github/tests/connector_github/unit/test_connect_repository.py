"""Unit tests for ConnectRepository command."""
import json
from unittest.mock import patch

from connector_github.commands.connect_repository import ConnectRepository


class TestConnectRepository:
    def test_successful_connect(self) -> None:
        repo_response = {
            "id": 1296269,
            "name": "hello-world",
            "full_name": "octocat/hello-world",
            "private": False,
            "default_branch": "main",
        }
        with patch("connector_github.commands.connect_repository.get_json") as mock_get:
            mock_get.return_value = (repo_response, 200, None)
            cmd = ConnectRepository("ghp_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"] == {
                "body": json.dumps(repo_response),
                "mimetype": "application/json",
                "http_status": 200,
                "parsed_body": repo_response,
            }
            assert response["error"] is None
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            assert "octocat/hello-world" in call_url

    def test_auth_error(self) -> None:
        with patch("connector_github.commands.connect_repository.get_json") as mock_get:
            mock_get.return_value = (
                {},
                401,
                {"error_code": "GitHubAuthError", "message": "GitHub authentication failed. Check your token."},
            )
            cmd = ConnectRepository("bad_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"] is not None
            assert response["error"]["error_code"] == "GitHubAuthError"

    def test_repo_not_found(self) -> None:
        with patch("connector_github.commands.connect_repository.get_json") as mock_get:
            mock_get.return_value = (
                {},
                404,
                {"error_code": "GitHubNotFoundError", "message": "GitHub resource not found: Not Found"},
            )
            cmd = ConnectRepository("ghp_token", "octocat", "nonexistent")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 404
            assert response["error"] is not None
            assert response["error"]["error_code"] == "GitHubNotFoundError"

    def test_network_error(self) -> None:
        with patch("connector_github.commands.connect_repository.get_json") as mock_get:
            mock_get.return_value = (
                {},
                500,
                {"error_code": "ConnectionError", "message": "Connection refused"},
            )
            cmd = ConnectRepository("ghp_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 500
            assert response["error"] is not None
