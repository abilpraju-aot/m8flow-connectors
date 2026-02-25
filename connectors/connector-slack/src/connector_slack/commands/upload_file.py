"""Upload a file to a Slack channel or DM via the external-upload API.
Uses files.getUploadURLExternal + files.completeUploadExternal (files.upload was sunset Nov 2025)."""
from __future__ import annotations

import os
from typing import Any

from connector_slack.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_slack.slack_client import (
    build_result,
    complete_upload_external,
    error_response,
    get_upload_url_external,
    upload_file_bytes,
)

# Directory the connector reads uploaded files from (host-side mount).
ATTACHMENTS_DIR = os.environ.get("M8FLOW_CONNECTOR_SLACK_ATTACHMENTS_DIR", "../slack_attachments")

# User-facing mount path; file paths supplied by the workflow are resolved under this root.
ALLOWED_UPLOAD_DIR = os.environ.get("M8FLOW_CONNECTOR_SLACK_UPLOAD_FILE_DIR", "/attachments")

# --- Limits ---
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
    """Return the effective per-file upload size limit in bytes, clamped to [1 .. HARD_UPLOAD_LIMIT_MB]."""
    requested_mb = _env_int(UPLOAD_LIMIT_ENV, DEFAULT_UPLOAD_LIMIT_MB)
    if requested_mb <= 0:
        requested_mb = DEFAULT_UPLOAD_LIMIT_MB
    effective_mb = min(requested_mb, HARD_UPLOAD_LIMIT_MB)
    return effective_mb * 1024 * 1024


def _resolve_and_validate_upload_path(path_value: str) -> str:
    """Ensure *path_value* is a safe, absolute path under ALLOWED_UPLOAD_DIR.

    Returns the resolved filesystem path ready for ``open()``.
    """
    if not path_value or not isinstance(path_value, str):
        raise ValueError("Upload 'filepath' must be a non-empty string.")

    allowed_root = os.path.realpath(ALLOWED_UPLOAD_DIR)

    if os.name != "nt" and (":" in path_value[:3] or path_value.startswith("\\\\")):
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


def _enforce_upload_limit(filename: str, size_bytes: int, limit_bytes: int) -> None:
    if size_bytes > limit_bytes:
        limit_mb = limit_bytes / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise ValueError(
            f"File '{filename}' is too large: {actual_mb:.2f} MB. "
            f"Limit is {limit_mb:.2f} MB (hard max {HARD_UPLOAD_LIMIT_MB} MB)."
        )


class UploadFile(ConnectorCommand):
    """Upload a file to a Slack channel or DM."""

    def __init__(
        self,
        token: str,
        channel: str,
        content: str = "",
        filename: str = "",
        initial_comment: str = "",
        filepath: str = "",
    ):
        self.token = token
        self.channel = channel
        self.content = content or ""
        self.filename = filename or ""
        self.initial_comment = initial_comment or ""
        self.filepath = filepath or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        limit_bytes = _get_upload_limit_bytes()

        if self.filepath:
            try:
                safe_path = _resolve_and_validate_upload_path(self.filepath)

                if not os.path.isfile(safe_path):
                    return error_response(
                        400, "SlackFileNotFound", f"No such file in upload directory: {self.filepath}"
                    )

                size = os.path.getsize(safe_path)
                effective_filename = self.filename or os.path.basename(safe_path)
                _enforce_upload_limit(effective_filename, size, limit_bytes)

                with open(safe_path, "rb") as f:
                    content_bytes = f.read()

                _enforce_upload_limit(effective_filename, len(content_bytes), limit_bytes)
            except ValueError as exc:
                return error_response(400, "SlackUploadValidation", str(exc))

        else:
            if not self.content.strip():
                return error_response(400, "SlackMissingContent", "File content must not be empty.")

            effective_filename = self.filename or "upload.txt"
            content_bytes = self.content.encode("utf-8")

            try:
                _enforce_upload_limit(effective_filename, len(content_bytes), limit_bytes)
            except ValueError as exc:
                return error_response(400, "SlackUploadValidation", str(exc))

        url_json, url_status, url_err = get_upload_url_external(
            self.token, effective_filename, len(content_bytes),
        )
        if url_err:
            return build_result(url_json, url_status, url_err)

        upload_url = url_json.get("upload_url", "")
        file_id = url_json.get("file_id", "")
        if not upload_url or not file_id:
            return error_response(500, "SlackUploadFailed", "Slack did not return upload_url or file_id.")

        put_status, put_err = upload_file_bytes(upload_url, effective_filename, content_bytes)
        if put_err:
            return error_response(put_status, put_err["error_code"], put_err["message"])

        complete_json, complete_status, complete_err = complete_upload_external(
            self.token, file_id, effective_filename,
            channel_id=self.channel, initial_comment=self.initial_comment,
        )
        return build_result(complete_json, complete_status, complete_err)
