"""Post message to a Slack channel. Channel can be ID (e.g. C123) or name (e.g. #general)."""
import json
from typing import Any

from connector_slack.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_slack.slack_client import build_result, error_response, post_json

SLACK_URL = "https://slack.com/api/chat.postMessage"


class PostMessage(ConnectorCommand):
    """Send a message to a Slack channel."""

    def __init__(self, token: str, channel: str, message: str, blocks: str | list = ""):
        """
        :param token: Slack OAuth access token (from m8flow/platform).
        :param channel: Channel ID (e.g. C123) or name (e.g. #general).
        :param message: Text to post (markdown supported).
        :param blocks: Block Kit blocks as a JSON string or an already-parsed list.
        """
        self.token = token
        self.channel = channel
        self.message = message
        self.blocks = blocks

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        body: dict[str, Any] = {"channel": self.channel, "text": self.message}
        if isinstance(self.blocks, list):
            body["blocks"] = self.blocks
        elif isinstance(self.blocks, str) and self.blocks.strip():
            try:
                body["blocks"] = json.loads(self.blocks)
            except (json.JSONDecodeError, TypeError) as exc:
                return error_response(400, "SlackMessageFailed", f"Invalid blocks JSON: {exc}")
        response_json, status, error = post_json(SLACK_URL, self.token, body)
        return build_result(response_json, status, error)
