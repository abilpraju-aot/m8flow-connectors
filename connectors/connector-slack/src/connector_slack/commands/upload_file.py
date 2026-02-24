"""Upload a file to a Slack channel or DM. Channel can be channel ID or user ID for DM.
Slack files.upload is deprecated (sunset Nov 2025); migration to files.getUploadURLExternal/files.completeUploadExternal recommended later."""
from typing import Any

from connector_slack.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_slack.slack_client import build_result, post_multipart

SLACK_UPLOAD_URL = "https://slack.com/api/files.upload"


class UploadFile(ConnectorCommand):
    """Upload a file to a Slack channel or DM. Single channel/user for MVP."""

    def __init__(self, token: str, channel: str, content: str, filename: str, initial_comment: str = ""):
        """
        :param token: Slack OAuth access token (from m8flow/platform).
        :param channel: Channel ID or user ID (for DM). Single destination for MVP.
        :param content: File contents (workflow can provide as string or base64-decoded string).
        :param filename: Name of the file as shown in Slack.
        :param initial_comment: Optional plain-text message shown with the file (Block Kit not supported by Slack here).
        """
        self.token = token
        self.channel = channel
        self.content = content
        self.filename = filename
        self.initial_comment = initial_comment or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        content_bytes = self.content.encode("utf-8") if isinstance(self.content, str) else self.content
        files = {"file": (self.filename, content_bytes)}
        data: dict[str, str] = {"channels": self.channel}
        if self.initial_comment:
            data["initial_comment"] = self.initial_comment
        response_json, status, error = post_multipart(SLACK_UPLOAD_URL, self.token, files, data)
        return build_result(response_json, status, error)
