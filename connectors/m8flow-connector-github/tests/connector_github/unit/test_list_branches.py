"""Unit tests for ListBranches command."""
import json
from unittest.mock import patch

from connector_github.commands.list_branches import ListBranches

SAMPLE_BRANCHES = [
    {"name": "main", "protected": True},
    {"name": "develop", "protected": False},
    {"name": "feature/new-ui", "protected": False},
]


class TestListBranches:
    def test_list_all_branches(self) -> None:
        with patch("connector_github.commands.list_branches.get_json") as mock_get:
            mock_get.return_value = (SAMPLE_BRANCHES, 200, None)
            cmd = ListBranches("ghp_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"] == {
                "body": json.dumps(SAMPLE_BRANCHES),
                "mimetype": "application/json",
                "http_status": 200,
                "parsed_body": SAMPLE_BRANCHES,
            }
            assert response["error"] is None
            call_url = mock_get.call_args[0][0]
            assert "branches" in call_url
            # No protected filter when not specified
            call_params = mock_get.call_args[1]["params"]
            assert "protected" not in call_params

    def test_list_protected_branches(self) -> None:
        protected_only = [{"name": "main", "protected": True}]
        with patch("connector_github.commands.list_branches.get_json") as mock_get:
            mock_get.return_value = (protected_only, 200, None)
            cmd = ListBranches("ghp_token", "octocat", "hello-world", protected="true")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            call_params = mock_get.call_args[1]["params"]
            assert call_params["protected"] == "true"

    def test_list_unprotected_branches(self) -> None:
        with patch("connector_github.commands.list_branches.get_json") as mock_get:
            mock_get.return_value = (SAMPLE_BRANCHES[1:], 200, None)
            cmd = ListBranches("ghp_token", "octocat", "hello-world", protected="false")
            cmd.execute({}, {})
            call_params = mock_get.call_args[1]["params"]
            assert call_params["protected"] == "false"

    def test_pagination_params(self) -> None:
        with patch("connector_github.commands.list_branches.get_json") as mock_get:
            mock_get.return_value = (SAMPLE_BRANCHES, 200, None)
            cmd = ListBranches("ghp_token", "octocat", "hello-world", per_page=50, page=3)
            cmd.execute({}, {})
            call_params = mock_get.call_args[1]["params"]
            assert call_params["per_page"] == 50
            assert call_params["page"] == 3

    def test_auth_error(self) -> None:
        with patch("connector_github.commands.list_branches.get_json") as mock_get:
            mock_get.return_value = (
                {},
                401,
                {"error_code": "GitHubAuthError", "message": "GitHub authentication failed. Check your token."},
            )
            cmd = ListBranches("bad_token", "octocat", "hello-world")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"]["error_code"] == "GitHubAuthError"

    def test_repo_not_found(self) -> None:
        with patch("connector_github.commands.list_branches.get_json") as mock_get:
            mock_get.return_value = (
                {},
                404,
                {"error_code": "GitHubNotFoundError", "message": "GitHub resource not found: Not Found"},
            )
            cmd = ListBranches("ghp_token", "octocat", "nonexistent")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 404
            assert response["error"]["error_code"] == "GitHubNotFoundError"
