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

# This is the ONLY directory file content may be read from when using "path". Mount your host folder to this path in docker-compose.
ALLOWED_ATTACHMENTS_DIR = os.environ.get("M8FLOW_CONNECTOR_SLACK_UPLOAD_FILE_DIR", "/attachments")


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


def _resolve_and_validate_upload_path(path_value: str) -> str:
    """
    Enforce upload path safety:
      - Must be an absolute path under ALLOWED_ATTACHMENTS_DIR (default: /attachments)
      - Must not traverse outside (..)
      - Must resolve to a real path under the allowed directory
    Returns a resolved filesystem path safe to open().
    """
    if not path_value or not isinstance(path_value, str):
        raise ValueError("Upload 'path' must be a non-empty string.")

    allowed_root = os.path.realpath(ALLOWED_ATTACHMENTS_DIR)

    if ":" in path_value[:3] or path_value.startswith("\\\\"):
        raise ValueError(
            f"Upload path must be under '{allowed_root}'. Windows/UNC paths are not allowed: {path_value!r}"
        )

    if not os.path.isabs(path_value):
        raise ValueError(
            f"Upload path must be an absolute path under '{allowed_root}'. Got: {path_value!r}"
        )

    candidate = os.path.realpath(path_value)

    try:
        common = os.path.commonpath([allowed_root, candidate])
    except ValueError:
        raise ValueError(f"Upload path is invalid: {path_value!r}")

    if common != allowed_root:
        raise ValueError(
            f"Upload path must be under '{allowed_root}'. Got: {path_value!r}"
        )

    return candidate


class UploadFile(ConnectorCommand):
    """Upload a file to a Slack channel or DM. Single channel/user for MVP.
    Provide either content (inline) or path (file under ALLOWED_ATTACHMENTS_DIR / M8FLOW_CONNECTOR_SLACK_UPLOAD_FILE_DIR). Path wins if both are set."""

    def __init__(
        self,
        token: str,
        channel: str,
        content: str | bytes = "",
        filename: str = "",
        initial_comment: str = "",
        path: str = "",
    ):
        """
        :param token: Slack OAuth access token (from m8flow/platform).
        :param channel: Channel ID or user ID (for DM). Single destination for MVP.
        :param content: File contents (workflow can provide as string or bytes). Ignored if path is set.
        :param filename: Name of the file as shown in Slack.
        :param initial_comment: Optional plain-text message shown with the file (Block Kit not supported by Slack here).
        :param path: Optional path to file under ALLOWED_ATTACHMENTS_DIR. If set, file is read from disk instead of using content.
        """
        self.token = token
        self.channel = channel
        self.content = content if content is not None else ""
        self.filename = filename or ""
        self.initial_comment = initial_comment or ""
        self.path = (path or "").strip()

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        limit_bytes = _get_upload_limit_bytes()

        if self.path:
            try:
                safe_path = _resolve_and_validate_upload_path(self.path)
                if not os.path.isfile(safe_path):
                    return error_response(
                        400, "SlackFileInvalidPath", f"No such file in upload directory: {safe_path}"
                    )
                size = os.path.getsize(safe_path)
                _enforce_upload_limit(self.filename or os.path.basename(safe_path), size, limit_bytes)
                with open(safe_path, "rb") as f:
                    content_bytes = f.read()
                _enforce_upload_limit(self.filename or os.path.basename(safe_path), len(content_bytes), limit_bytes)
            except (ValueError, FileNotFoundError) as exc:
                return error_response(400, "SlackFileInvalidPath", str(exc))
            except OSError as exc:
                return error_response(400, "SlackFileInvalidPath", str(exc))
        else:
            if self.content is None or (isinstance(self.content, str) and not self.content.strip()) or (isinstance(self.content, bytes) and len(self.content) == 0):
                return error_response(400, "SlackFileInvalidPath", "Provide either content or path.")
            content_bytes = self.content.encode("utf-8") if isinstance(self.content, str) else self.content
            try:
                _enforce_upload_limit(self.filename or "upload", len(content_bytes), limit_bytes)
            except ValueError as exc:
                return error_response(400, "SlackFileTooLarge", str(exc))

        display_filename = self.filename or (os.path.basename(self.path) if self.path else "upload")
        files = {"file": (display_filename, content_bytes)}
        data: dict[str, str] = {"channels": self.channel}
        if self.initial_comment:
            data["initial_comment"] = self.initial_comment
        response_json, status, error = post_multipart(SLACK_UPLOAD_URL, self.token, files, data)
        return build_result(response_json, status, error)
