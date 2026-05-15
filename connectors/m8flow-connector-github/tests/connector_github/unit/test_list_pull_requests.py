"""Unit tests for ListPullRequests command."""
import json
from unittest.mock import patch

from connector_github.commands.list_pull_requests import ListPullRequests

SAMPLE_PRS = [
    {
        "number": 42,
        "title": "Add new feature",
        "state": "open",
        "user": {"login": "octocat"},
        "head": {"ref": "feature-branch"},
        "base": {"ref": "main"},
    },
    {
        "number": 41,
        "title": "Fix bug",
        "state": "open",
        "user": {"login": "monalisa"},
        "head": {"ref": "fix-bug"},
        "base": {"ref": "main"},
    },
]


class TestListPullRequests:
    def test_list_open_prs(self) -> None:
        with patch("connector_github.commands.list_pull_requests.get_json") as mock_get:
            mock_get.return_value = (SAMPLE_PRS, 200, None)
            cmd = ListPullRequests("ghp_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"] == {
                "body": json.dumps(SAMPLE_PRS),
                "mimetype": "application/json",
                "http_status": 200,
            }
            assert response["error"] is None
            call_url, call_token = mock_get.call_args[0][0], mock_get.call_args[0][1]
            assert "pulls" in call_url
            assert call_token == "ghp_token"
            call_params = mock_get.call_args[1]["params"]
            assert call_params["state"] == "open"

    def test_list_closed_prs(self) -> None:
        with patch("connector_github.commands.list_pull_requests.get_json") as mock_get:
            mock_get.return_value = ([], 200, None)
            cmd = ListPullRequests("ghp_token", "octocat", "hello-world", state="closed")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            call_params = mock_get.call_args[1]["params"]
            assert call_params["state"] == "closed"

    def test_pagination_params(self) -> None:
        with patch("connector_github.commands.list_pull_requests.get_json") as mock_get:
            mock_get.return_value = (SAMPLE_PRS, 200, None)
            cmd = ListPullRequests("ghp_token", "octocat", "hello-world", per_page=10, page=2)
            cmd.execute({}, {})
            call_params = mock_get.call_args[1]["params"]
            assert call_params["per_page"] == 10
            assert call_params["page"] == 2

    def test_auth_error(self) -> None:
        with patch("connector_github.commands.list_pull_requests.get_json") as mock_get:
            mock_get.return_value = (
                {},
                401,
                {"error_code": "GitHubAuthError", "message": "GitHub authentication failed. Check your token."},
            )
            cmd = ListPullRequests("bad_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"]["error_code"] == "GitHubAuthError"

    def test_repo_not_found(self) -> None:
        with patch("connector_github.commands.list_pull_requests.get_json") as mock_get:
            mock_get.return_value = (
                {},
                404,
                {"error_code": "GitHubNotFoundError", "message": "GitHub resource not found: Not Found"},
            )
            cmd = ListPullRequests("ghp_token", "octocat", "nonexistent")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 404
            assert response["error"]["error_code"] == "GitHubNotFoundError"
