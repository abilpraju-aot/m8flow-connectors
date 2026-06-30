"""List pull requests for a GitHub repository."""
from typing import Any

from connector_github.connector_interface import ConnectorCommand
from connector_github.connector_interface import ConnectorProxyResponseDict
from connector_github.github_client import GITHUB_API_BASE
from connector_github.github_client import build_result
from connector_github.github_client import get_json


class ListPullRequests(ConnectorCommand):
    """List pull requests for a GitHub repository, with optional state and pagination filters."""

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ):
        """
        :param token: GitHub Personal Access Token (PAT) or OAuth token (from m8flow/platform).
        :param owner: Repository owner (user or organisation), e.g. ``octocat``.
        :param repo: Repository name, e.g. ``hello-world``.
        :param state: Filter by PR state: ``open`` (default), ``closed``, or ``all``.
        :param per_page: Number of results per page (1–100). Default is 30.
        :param page: Page number to fetch. Default is 1.
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.state = state
        self.per_page = per_page
        self.page = page

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        url = f"{GITHUB_API_BASE}/repos/{self.owner}/{self.repo}/pulls"
        params: dict[str, Any] = {
            "state": self.state,
            "per_page": self.per_page,
            "page": self.page,
        }
        response_json, status, error = get_json(url, self.token, params=params)
        return build_result(response_json, status, error)
