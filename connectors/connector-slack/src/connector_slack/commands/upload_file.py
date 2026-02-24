"""Upload a file to a Slack channel or DM. Channel can be channel ID or user ID for DM.
Slack files.upload is deprecated (sunset Nov 2025); migration to files.getUploadURLExternal/files.completeUploadExternal recommended later.
File size is limited by M8FLOW_CONNECTOR_SLACK_UPLOAD_FILE_LIMIT_MB (default 50 MB, hard max 100 MB) so workflows get a clear error instead of timeouts."""
import os
from typing import Any

from connector_slack.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_slack.slack_client import build_result, error_response, post_multipart

SLACK_UPLOAD_URL = "https://slack.com/api/files.upload"

# --- File size limits (mirror SMTP attachment handling) ---
HARD_UPLOAD_LIMIT_MB = 100
DEFAULT_UPLOAD_LIMIT_MB = 50
UPLOAD_LIMIT_ENV = "M8FLOW_CONNECTOR_SLACK_UPLOAD_FILE_LIMIT_MB"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def _get_upload_limit_bytes() -> int:
    """
    Returns the effective upload file size limit in bytes.
    - Hard cap: HARD_UPLOAD_LIMIT_MB
    - Configurable via UPLOAD_LIMIT_ENV (clamped to [1..HARD])
    - Defaults to DEFAULT_UPLOAD_LIMIT_MB if unset/invalid
    """
    requested_mb = _env_int(UPLOAD_LIMIT_ENV, DEFAULT_UPLOAD_LIMIT_MB)
    if requested_mb <= 0:
        requested_mb = DEFAULT_UPLOAD_LIMIT_MB
    effective_mb = min(requested_mb, HARD_UPLOAD_LIMIT_MB)
    return effective_mb * 1024 * 1024


def _enforce_upload_limit(filename: str, size_bytes: int, limit_bytes: int) -> None:
    if size_bytes > limit_bytes:
        limit_mb = limit_bytes / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise ValueError(
            f"File '{filename}' is too large: {actual_mb:.2f} MB. "
            f"Limit is {limit_mb:.2f} MB (hard max {HARD_UPLOAD_LIMIT_MB} MB)."
        )


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
        limit_bytes = _get_upload_limit_bytes()
        try:
            _enforce_upload_limit(self.filename, len(content_bytes), limit_bytes)
        except ValueError as exc:
            return error_response(400, "SlackFileTooLarge", str(exc))
        files = {"file": (self.filename, content_bytes)}
        data: dict[str, str] = {"channels": self.channel}
        if self.initial_comment:
            data["initial_comment"] = self.initial_comment
        response_json, status, error = post_multipart(SLACK_UPLOAD_URL, self.token, files, data)
        return build_result(response_json, status, error)
