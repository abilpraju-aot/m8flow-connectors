"""Upload a file to a Slack channel or DM via the external-upload API.
Uses files.getUploadURLExternal + files.completeUploadExternal (files.upload was sunset Nov 2025)."""
import base64
import binascii
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

# The ONLY directory files may be read from for upload.
# Mount your host folder to this path in docker-compose.
ATTACHMENTS_DIR = os.environ.get("M8FLOW_CONNECTOR_SLACK_ATTACHMENTS_USER_ACCESS_DIR", "/slack_attachments")

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
    """Ensure *path_value* is a safe, absolute path under ATTACHMENTS_DIR.

    Returns the resolved filesystem path ready for ``open()``.
    """
    if not path_value or not isinstance(path_value, str):
        raise ValueError("Upload 'filepath' must be a non-empty string.")

    allowed_root = os.path.realpath(ATTACHMENTS_DIR)

    if not os.path.isabs(path_value):
        raise ValueError(
            f"Upload path must be an absolute path under '{allowed_root}'. Got: {path_value!r}"
        )

    candidate = os.path.realpath(path_value)

    if candidate != allowed_root and not candidate.startswith(allowed_root + os.sep):
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


def _estimated_base64_decoded_size(b64_text: str) -> int:
    """Estimate decoded size without decoding.

    This allows enforcing size limits before allocating memory for large payloads.
    Formula: decoded_bytes ~= (len(cleaned) * 3 / 4) - padding
    """
    s = "".join(str(b64_text).split())
    if not s:
        return 0
    padding = 0
    if s.endswith("=="):
        padding = 2
    elif s.endswith("="):
        padding = 1
    return (len(s) * 3) // 4 - padding


class UploadFile(ConnectorCommand):
    """Upload a file to a Slack channel or DM."""

    def __init__(
        self,
        token: str,
        channel: str,
        filename: str = "",
        initial_comment: str = "",
        filepath: str = "",
        content_base64: str = "",
    ):
        self.token = token
        self.channel = channel
        self.filename = filename or ""
        self.initial_comment = initial_comment or ""
        self.filepath = filepath or ""
        self.content_base64 = content_base64 or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        logs: list[str] = []

        try:
            limit_bytes = _get_upload_limit_bytes()
            logs.append(f"upload attachments dir: {os.path.realpath(ATTACHMENTS_DIR)}")
            logs.append(
                f"upload size limit: {limit_bytes / (1024 * 1024):.2f} MB"
                f" (hard max {HARD_UPLOAD_LIMIT_MB} MB)"
            )

            if self.filepath:
                logs.append(f"filepath mode: {self.filepath!r}")
                safe_path = _resolve_and_validate_upload_path(self.filepath)
                logs.append(f"resolved path: {safe_path}")
                with os.scandir('.') as entries:
                    for entry in entries:
                        if entry.is_file():
                            logs.append(f"File: {entry.name}")
                        elif entry.is_dir():
                            logs.append(f"Directory: {entry.name}")
                if not os.path.isfile(safe_path):
                    logs.append(f"file not found: {safe_path}")
                    return self._result(
                        logs, 400, "SlackFileNotFound",
                        f"No such file in upload directory: {self.filepath}",
                    )

                size = os.path.getsize(safe_path)
                effective_filename = self.filename or os.path.basename(safe_path)
                _enforce_upload_limit(effective_filename, size, limit_bytes)
                logs.append(f"file ok: {effective_filename} ({size} bytes)")

                with open(safe_path, "rb") as f:
                    content_bytes = f.read()

                _enforce_upload_limit(effective_filename, len(content_bytes), limit_bytes)
            elif self.content_base64:
                effective_filename = self.filename or "upload.bin"
                logs.append(f"base64 mode: decoding content for {effective_filename!r}")
                est = _estimated_base64_decoded_size(self.content_base64)
                _enforce_upload_limit(effective_filename, est, limit_bytes)
                try:
                    content_bytes = base64.b64decode(self.content_base64, validate=True)
                except binascii.Error as exc:
                    logs.append(f"base64 decode error: {exc}")
                    return self._result(
                        logs, 400, "SlackInvalidBase64",
                        f"Invalid base64 content: {exc}",
                    )
                _enforce_upload_limit(effective_filename, len(content_bytes), limit_bytes)
                logs.append(f"base64 mode: {effective_filename} ({len(content_bytes)} bytes)")
            else:
                logs.append("no content source provided")
                return self._result(
                    logs, 400, "SlackMissingContent",
                    "Either 'filepath' or 'content_base64' must be provided.",
                )

            logs.append("requesting upload URL from Slack")
            url_json, url_status, url_err = get_upload_url_external(
                self.token, effective_filename, len(content_bytes),
            )
            if url_err:
                logs.append(f"get_upload_url error: {url_err}")
                result = build_result(url_json, url_status, url_err)
                result["spiff__logs"] = logs  # type: ignore[typeddict-unknown-key]
                return result

            upload_url = url_json.get("upload_url", "")
            file_id = url_json.get("file_id", "")
            if not upload_url or not file_id:
                logs.append("Slack did not return upload_url or file_id")
                return self._result(
                    logs, 500, "SlackUploadFailed",
                    "Slack did not return upload_url or file_id.",
                )

            logs.append(f"uploading {len(content_bytes)} bytes to pre-signed URL")
            put_status, put_err = upload_file_bytes(upload_url, effective_filename, content_bytes)
            if put_err:
                logs.append(f"upload bytes error: {put_err}")
                return self._result(logs, put_status, put_err["error_code"], put_err["message"])

            logs.append("completing upload")
            cj, cs, ce = complete_upload_external(
                self.token, file_id, effective_filename,
                channel_id=self.channel, initial_comment=self.initial_comment,
            )
            if ce:
                logs.append(f"complete error: {ce}")
            else:
                logs.append("upload completed successfully")
            result = build_result(cj, cs, ce)
            result["spiff__logs"] = logs  # type: ignore[typeddict-unknown-key]
            return result

        except Exception as exc:
            logs.append(f"unhandled error: {exc.__class__.__name__}: {exc}")
            return self._result(logs, 500, exc.__class__.__name__, str(exc))

    @staticmethod
    def _result(
        logs: list[str],
        http_status: int,
        error_code: str,
        message: str,
    ) -> ConnectorProxyResponseDict:
        return {  # type: ignore[typeddict-unknown-key]
            "command_response": {"body": "{}", "mimetype": "application/json", "http_status": http_status},
            "error": {"error_code": error_code, "message": message},
            "command_response_version": 2,
            "spiff__logs": logs,
        }
