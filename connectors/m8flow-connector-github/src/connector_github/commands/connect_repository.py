"""Connect to a GitHub repository and return its metadata."""
from typing import Any

from connector_github.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_github.github_client import GITHUB_API_BASE, build_result, get_json


class ConnectRepository(ConnectorCommand):
    """Verify access to a GitHub repository and return its metadata."""

    def __init__(self, token: str, owner: str, repo: str):
        """
        :param token: GitHub Personal Access Token (PAT) or OAuth token (from m8flow/platform).
        :param owner: Repository owner (user or organisation), e.g. ``octocat``.
        :param repo: Repository name, e.g. ``hello-world``.
        """
        self.token = token
        self.owner = owner
        self.repo = repo

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        url = f"{GITHUB_API_BASE}/repos/{self.owner}/{self.repo}"
        response_json, status, error = get_json(url, self.token)
        return build_result(response_json, status, error)
