from __future__ import annotations

import base64
import binascii
import mimetypes
import os
import ssl
from email.message import EmailMessage
from smtplib import SMTP
from typing import Any

from spiffworkflow_connector_command.command_interface import CommandErrorDict
from spiffworkflow_connector_command.command_interface import CommandResponseDict
from spiffworkflow_connector_command.command_interface import ConnectorCommand
from spiffworkflow_connector_command.command_interface import ConnectorProxyResponseDict

# This is the ONLY directory attachments may be read from when using "path".
# Mount your host folder to this path in docker-compose.
ALLOWED_ATTACHMENTS_DIR = os.environ.get("M8FLOW_CONNECTOR_SMTP_ATTACHMENTS_USER_ACCESS_DIR", "/attachments")

# --- Limits / timeouts ---
HARD_ATTACHMENTS_LIMIT_MB = 100
DEFAULT_ATTACHMENTS_LIMIT_MB = 100
ATTACHMENTS_LIMIT_ENV = "M8FLOW_CONNECTOR_SMTP_ATTACHMENTS_LIMIT_IN_MB"

DEFAULT_SMTP_TIMEOUT_SECONDS = 30
SMTP_TIMEOUT_ENV = "M8FLOW_CONNECTOR_SMTP_TIMEOUT_SECONDS"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def _get_attachments_limit_bytes() -> int:
    """
    Returns the effective attachments size limit in bytes.
    - Hard cap: HARD_ATTACHMENTS_LIMIT_MB
    - Configurable via ATTACHMENTS_LIMIT_ENV (clamped to [1..HARD])
    - Defaults to DEFAULT_ATTACHMENTS_LIMIT_MB if unset/invalid
    """
    requested_mb = _env_int(ATTACHMENTS_LIMIT_ENV, DEFAULT_ATTACHMENTS_LIMIT_MB)

    if requested_mb <= 0:
        requested_mb = DEFAULT_ATTACHMENTS_LIMIT_MB

    effective_mb = min(requested_mb, HARD_ATTACHMENTS_LIMIT_MB)
    return effective_mb * 1024 * 1024


def _get_smtp_timeout_seconds() -> int:
    timeout = _env_int(SMTP_TIMEOUT_ENV, DEFAULT_SMTP_TIMEOUT_SECONDS)
    # avoid weird values
    if timeout <= 0:
        timeout = DEFAULT_SMTP_TIMEOUT_SECONDS
    return timeout


def _split_recipients(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.replace(";", ",")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _guess_content_type(filename: str, explicit: str | None) -> tuple[str, str]:
    if explicit and "/" in explicit:
        maintype, subtype = explicit.split("/", 1)
        return maintype, subtype

    guessed, _ = mimetypes.guess_type(filename)
    if guessed and "/" in guessed:
        maintype, subtype = guessed.split("/", 1)
        return maintype, subtype

    return "application", "octet-stream"


def _resolve_and_validate_attachment_path(path_value: str) -> str:
    """
    Enforce attachment path safety:
      - Must be an absolute path under ALLOWED_ATTACHMENTS_DIR (default: /attachments)
      - Must not traverse outside (..)
      - Must resolve to a real path under the allowed directory
    Returns a resolved filesystem path safe to open().
    """
    if not path_value or not isinstance(path_value, str):
        raise ValueError("Attachment 'path' must be a non-empty string.")

    allowed_root = os.path.realpath(ALLOWED_ATTACHMENTS_DIR)

    if ":" in path_value[:3] or path_value.startswith("\\\\"):
        raise ValueError(
            f"Attachment path must be under '{allowed_root}'. Windows/UNC paths are not allowed: {path_value!r}"
        )

    if not os.path.isabs(path_value):
        raise ValueError(
            f"Attachment path must be an absolute path under '{allowed_root}'. Got: {path_value!r}"
        )

    candidate = os.path.realpath(path_value)

    try:
        common = os.path.commonpath([allowed_root, candidate])
    except ValueError as err:
        raise ValueError(f"Attachment path is invalid: {path_value!r}") from err

    if common != allowed_root:
        raise ValueError(
            f"Attachment path must be under '{allowed_root}'. Got: {path_value!r}"
        )

    return candidate


def _estimated_base64_decoded_size(b64_text: str) -> int:
    """
    Estimate decoded size without decoding:
      decoded_bytes ~= (len(cleaned) * 3 / 4) - padding
    We also strip whitespace/newlines.
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


def _enforce_attachment_limit(name: str, size_bytes: int, limit_bytes: int) -> None:
    if size_bytes > limit_bytes:
        limit_mb = limit_bytes / (1024 * 1024)
        actual_mb = size_bytes / (1024 * 1024)
        raise ValueError(
            f"Attachment '{name}' is too large: {actual_mb:.2f} MB. "
            f"Limit is {limit_mb:.2f} MB (hard max {HARD_ATTACHMENTS_LIMIT_MB} MB)."
        )


def _read_attachment_bytes(
    att: dict[str, Any],
    index: int,
    limit_bytes: int,
) -> tuple[str, bytes, str | None]:
    """
    Attachment dict format (one of):

    1) File path (must exist inside container AND under ALLOWED_ATTACHMENTS_DIR):
       {"filename": "report.pdf", "path": "/attachments/report.pdf", "content_type": "application/pdf"}

    2) Base64 content:
       {"filename": "report.pdf", "content_base64": "<BASE64>", "content_type": "application/pdf"}

    content_type optional.
    Returns (filename, payload_bytes, content_type).
    """
    filename = str(att.get("filename") or "").strip()
    if not filename:
        raise ValueError(f"Attachment #{index} missing required field 'filename'.")

    path = att.get("path")
    content_b64 = att.get("content_base64")
    content_type = att.get("content_type")

    if path:
        safe_path = _resolve_and_validate_attachment_path(str(path))
        if not os.path.isfile(safe_path):
            raise FileNotFoundError(f"No such file in attachments folder: {safe_path}")

        # Size check before reading into memory
        size = os.path.getsize(safe_path)
        _enforce_attachment_limit(filename, size, limit_bytes)

        with open(safe_path, "rb") as f:
            payload = f.read()

        # Safety check (in case size changed between stat and read)
        _enforce_attachment_limit(filename, len(payload), limit_bytes)

        return filename, payload, str(content_type) if content_type else None

    if content_b64:
        # Estimate decoded size first to avoid decoding a massive string
        est = _estimated_base64_decoded_size(str(content_b64))
        _enforce_attachment_limit(filename, est, limit_bytes)

        try:
            payload = base64.b64decode(str(content_b64), validate=True)
        except binascii.Error as exc:
            raise ValueError(f"Attachment '{filename}' has invalid base64 content: {exc}") from exc

        _enforce_attachment_limit(filename, len(payload), limit_bytes)

        return filename, payload, str(content_type) if content_type else None

    raise ValueError(f"Attachment '{filename}' must provide either 'path' or 'content_base64'.")


class SendHTMLEmail(ConnectorCommand):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        email_subject: str,
        email_body: str,
        email_to: str,
        email_from: str,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        smtp_starttls: bool | None = False,
        email_body_html: str | None = None,
        email_cc: str | None = None,
        email_bcc: str | None = None,
        email_reply_to: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_starttls = smtp_starttls

        self.email_subject = email_subject
        self.email_body = email_body
        self.email_body_html = email_body_html

        self.email_to = email_to
        self.email_cc = email_cc
        self.email_bcc = email_bcc
        self.email_from = email_from
        self.email_reply_to = email_reply_to

        self.attachments = attachments or []

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        logs: list[str] = []
        error: CommandErrorDict | None = None

        limit_bytes = _get_attachments_limit_bytes()
        smtp_timeout = _get_smtp_timeout_seconds()

        message = EmailMessage()
        message["Subject"] = self.email_subject
        message["From"] = self.email_from
        message["To"] = self.email_to

        if self.email_cc:
            message["Cc"] = self.email_cc

        if self.email_reply_to:
            message["Reply-To"] = self.email_reply_to

        message.set_content(self.email_body or "")

        if self.email_body_html:
            message.add_alternative(self.email_body_html, subtype="html")

        # Attachments (restricted + size limited)
        try:
            logs.append(f"attachments allowed dir: {os.path.realpath(ALLOWED_ATTACHMENTS_DIR)}")
            logs.append(f"attachments size limit: {limit_bytes / (1024 * 1024):.2f} MB (hard max {HARD_ATTACHMENTS_LIMIT_MB} MB)")
            for i, att in enumerate(self.attachments):
                filename, payload, explicit_ct = _read_attachment_bytes(att, i, limit_bytes)
                maintype, subtype = _guess_content_type(filename, explicit_ct)
                message.add_attachment(
                    payload,
                    maintype=maintype,
                    subtype=subtype,
                    filename=filename,
                )
                logs.append(f"attached: {filename} ({maintype}/{subtype}, {len(payload)} bytes)")
        except Exception as exc:
            logs.append(f"attachment error: {str(exc)}")
            error = {"error_code": exc.__class__.__name__, "message": str(exc)}
            return {
                "command_response": {"body": "{}", "mimetype": "application/json"},
                "error": error,
                "command_response_version": 2,
                "spiff__logs": logs,
            }

        to_list = _split_recipients(self.email_to)
        cc_list = _split_recipients(self.email_cc)
        bcc_list = _split_recipients(self.email_bcc)
        envelope_recipients = _dedupe_keep_order(to_list + cc_list + bcc_list)

        if not envelope_recipients:
            error = {"error_code": "ValueError", "message": "No recipients provided (To/Cc/Bcc all empty)."}
            return {
                "command_response": {"body": "{}", "mimetype": "application/json"},
                "error": error,
                "command_response_version": 2,
                "spiff__logs": logs,
            }

        try:
            logs.append(f"will send (smtp timeout: {smtp_timeout}s)")
            with SMTP(self.smtp_host, self.smtp_port, timeout=smtp_timeout) as smtp:
                if self.smtp_starttls:
                    logs.append("will starttls")
                    smtp.starttls(context=ssl.create_default_context())

                if self.smtp_user and self.smtp_password:
                    logs.append("will login")
                    smtp.login(self.smtp_user, self.smtp_password)
                    logs.append("did login")

                smtp.send_message(message, to_addrs=envelope_recipients)
                logs.append(f"did send to {len(envelope_recipients)} recipient(s)")
        except Exception as exc:
            logs.append(f"did error: {str(exc)}")
            error = {"error_code": exc.__class__.__name__, "message": str(exc)}

        return_response: CommandResponseDict = {"body": "{}", "mimetype": "application/json"}
        return {
            "command_response": return_response,
            "error": error,
            "command_response_version": 2,
            "spiff__logs": logs,
        }
