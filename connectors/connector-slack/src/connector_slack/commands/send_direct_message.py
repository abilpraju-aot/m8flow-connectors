"""Send a direct message to a Slack user by user ID (e.g. U12345)."""
import json
from typing import Any

from connector_slack.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_slack.slack_client import build_result, error_response, post_json

SLACK_URL = "https://slack.com/api/chat.postMessage"


class SendDirectMessage(ConnectorCommand):
    """Send a direct message to a Slack user. User selector is by ID only."""

    def __init__(self, token: str, user_id: str, message: str, blocks: str = ""):
        """
        :param token: Slack OAuth access token (from m8flow/platform).
        :param user_id: Slack user ID (e.g. U12345). DM channel is the user ID.
        :param message: Text to send (markdown supported).
        :param blocks: Optional JSON string of Block Kit blocks array for structured messages.
        """
        self.token = token
        self.user_id = user_id
        self.message = message
        self.blocks = blocks

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        body: dict[str, Any] = {"channel": self.user_id, "text": self.message}
        if self.blocks.strip():
            try:
                body["blocks"] = json.loads(self.blocks)
            except (json.JSONDecodeError, TypeError) as exc:
                return error_response(400, "SlackMessageFailed", f"Invalid blocks JSON: {exc}")
        response_json, status, error = post_json(SLACK_URL, self.token, body)
        return build_result(response_json, status, error)
