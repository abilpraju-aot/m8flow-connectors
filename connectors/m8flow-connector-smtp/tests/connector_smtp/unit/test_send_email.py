from __future__ import annotations

import base64
from unittest.mock import patch

from connector_smtp.commands.send_email import ATTACHMENTS_LIMIT_ENV
from connector_smtp.commands.send_email import DEFAULT_ATTACHMENTS_LIMIT_MB
from connector_smtp.commands.send_email import DEFAULT_SMTP_TIMEOUT_SECONDS
from connector_smtp.commands.send_email import HARD_ATTACHMENTS_LIMIT_MB
from connector_smtp.commands.send_email import SMTP_TIMEOUT_ENV
from connector_smtp.commands.send_email import SendHTMLEmail
from connector_smtp.commands.send_email import _dedupe_keep_order
from connector_smtp.commands.send_email import _env_int
from connector_smtp.commands.send_email import _estimated_base64_decoded_size
from connector_smtp.commands.send_email import _get_attachments_limit_bytes
from connector_smtp.commands.send_email import _get_smtp_timeout_seconds
from connector_smtp.commands.send_email import _guess_content_type
from connector_smtp.commands.send_email import _read_attachment_bytes
from connector_smtp.commands.send_email import _resolve_and_validate_attachment_path
from connector_smtp.commands.send_email import _split_recipients


class TestEnvHelpers:
    def test_env_int_returns_default_for_missing_blank_and_invalid(self, monkeypatch) -> None:
        monkeypatch.delenv("SOME_ENV", raising=False)
        assert _env_int("SOME_ENV", 7) == 7

        monkeypatch.setenv("SOME_ENV", "  ")
        assert _env_int("SOME_ENV", 7) == 7

        monkeypatch.setenv("SOME_ENV", "invalid")
        assert _env_int("SOME_ENV", 7) == 7

    def test_env_int_parses_valid_value(self, monkeypatch) -> None:
        monkeypatch.setenv("SOME_ENV", " 12 ")
        assert _env_int("SOME_ENV", 3) == 12

    def test_get_attachments_limit_bytes_uses_default_and_hard_cap(self, monkeypatch) -> None:
        monkeypatch.delenv(ATTACHMENTS_LIMIT_ENV, raising=False)
        assert _get_attachments_limit_bytes() == DEFAULT_ATTACHMENTS_LIMIT_MB * 1024 * 1024

        monkeypatch.setenv(ATTACHMENTS_LIMIT_ENV, "0")
        assert _get_attachments_limit_bytes() == DEFAULT_ATTACHMENTS_LIMIT_MB * 1024 * 1024

        monkeypatch.setenv(ATTACHMENTS_LIMIT_ENV, str(HARD_ATTACHMENTS_LIMIT_MB + 50))
        assert _get_attachments_limit_bytes() == HARD_ATTACHMENTS_LIMIT_MB * 1024 * 1024

    def test_get_smtp_timeout_seconds_uses_default_for_invalid_values(self, monkeypatch) -> None:
        monkeypatch.delenv(SMTP_TIMEOUT_ENV, raising=False)
        assert _get_smtp_timeout_seconds() == DEFAULT_SMTP_TIMEOUT_SECONDS

        monkeypatch.setenv(SMTP_TIMEOUT_ENV, "-1")
        assert _get_smtp_timeout_seconds() == DEFAULT_SMTP_TIMEOUT_SECONDS

        monkeypatch.setenv(SMTP_TIMEOUT_ENV, "15")
        assert _get_smtp_timeout_seconds() == 15


class TestRecipientHelpers:
    def test_split_recipients_supports_commas_semicolons_and_trimming(self) -> None:
        assert _split_recipients("a@example.com; b@example.com, c@example.com ") == [
            "a@example.com",
            "b@example.com",
            "c@example.com",
        ]

    def test_split_recipients_returns_empty_list_for_empty_input(self) -> None:
        assert _split_recipients(None) == []
        assert _split_recipients("") == []

    def test_dedupe_keep_order_preserves_first_occurrence(self) -> None:
        assert _dedupe_keep_order(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


class TestAttachmentHelpers:
    def test_guess_content_type_prefers_explicit_type(self) -> None:
        assert _guess_content_type("report.pdf", "text/plain") == ("text", "plain")

    def test_guess_content_type_uses_filename_and_falls_back(self) -> None:
        assert _guess_content_type("report.pdf", None) == ("application", "pdf")
        assert _guess_content_type("report.unknownext", None) == ("application", "octet-stream")

    def test_resolve_and_validate_attachment_path_accepts_allowed_absolute_path(self, monkeypatch) -> None:
        monkeypatch.setattr("connector_smtp.commands.send_email.ALLOWED_ATTACHMENTS_DIR", "/attachments")
        resolved = _resolve_and_validate_attachment_path("/attachments/subdir/report.pdf")
        assert resolved.endswith("attachments\\subdir\\report.pdf") or resolved.endswith("/attachments/subdir/report.pdf")

    def test_resolve_and_validate_attachment_path_rejects_relative_or_outside_paths(self, monkeypatch) -> None:
        monkeypatch.setattr("connector_smtp.commands.send_email.ALLOWED_ATTACHMENTS_DIR", "/attachments")

        try:
            _resolve_and_validate_attachment_path("report.pdf")
            raise AssertionError("Expected ValueError for relative path")
        except ValueError as exc:
            assert "absolute path" in str(exc)

        try:
            _resolve_and_validate_attachment_path("/tmp/report.pdf")  # noqa: S108
            raise AssertionError("Expected ValueError for outside path")
        except ValueError as exc:
            assert "must be under" in str(exc)

    def test_estimated_base64_decoded_size_handles_padding(self) -> None:
        assert _estimated_base64_decoded_size("YQ==") == 1
        assert _estimated_base64_decoded_size("YWI=") == 2
        assert _estimated_base64_decoded_size("YWJj") == 3

    def test_read_attachment_bytes_from_base64(self) -> None:
        payload_b64 = base64.b64encode(b"hello").decode("ascii")
        filename, payload, content_type = _read_attachment_bytes(
            {"filename": "hello.txt", "content_base64": payload_b64, "content_type": "text/plain"},
            0,
            1024,
        )
        assert filename == "hello.txt"
        assert payload == b"hello"
        assert content_type == "text/plain"

    def test_read_attachment_bytes_from_file(self, tmp_path, monkeypatch) -> None:
        attachment_file = tmp_path / "hello.txt"
        attachment_file.write_bytes(b"hello from file")

        monkeypatch.setattr(
            "connector_smtp.commands.send_email._resolve_and_validate_attachment_path",
            lambda _: str(attachment_file),
        )

        filename, payload, content_type = _read_attachment_bytes(
            {"filename": "hello.txt", "path": "/attachments/hello.txt"},
            0,
            1024,
        )
        assert filename == "hello.txt"
        assert payload == b"hello from file"
        assert content_type is None

    def test_read_attachment_bytes_rejects_invalid_input(self) -> None:
        try:
            _read_attachment_bytes({"filename": "hello.txt"}, 0, 1024)
            raise AssertionError("Expected ValueError when attachment content is missing")
        except ValueError as exc:
            assert "either 'path' or 'content_base64'" in str(exc)

        try:
            _read_attachment_bytes({"content_base64": "aGVsbG8="}, 0, 1024)
            raise AssertionError("Expected ValueError when filename is missing")
        except ValueError as exc:
            assert "missing required field 'filename'" in str(exc)

    def test_read_attachment_bytes_rejects_invalid_base64_and_large_content(self) -> None:
        try:
            _read_attachment_bytes({"filename": "bad.txt", "content_base64": "not-base64"}, 0, 1024)
            raise AssertionError("Expected ValueError for invalid base64")
        except ValueError as exc:
            assert "invalid base64" in str(exc)

        oversized = base64.b64encode(b"abcd").decode("ascii")
        try:
            _read_attachment_bytes({"filename": "big.bin", "content_base64": oversized}, 0, 3)
            raise AssertionError("Expected ValueError for oversized attachment")
        except ValueError as exc:
            assert "too large" in str(exc)


class TestSendHtmlEmail:
    def test_execute_success_with_html_tls_login_and_attachment(self, monkeypatch) -> None:
        monkeypatch.setenv(SMTP_TIMEOUT_ENV, "11")
        attachment_payload = base64.b64encode(b"hello attachment").decode("ascii")

        with patch("connector_smtp.commands.send_email.SMTP") as mock_smtp, patch(
            "connector_smtp.commands.send_email.ssl.create_default_context"
        ) as mock_context:
            smtp_instance = mock_smtp.return_value.__enter__.return_value
            mock_context.return_value = object()

            response = SendHTMLEmail(
                smtp_host="smtp.example.com",
                smtp_port=587,
                smtp_user="user",
                smtp_password="pass",  # noqa: S106
                smtp_starttls=True,
                email_subject="Subject",
                email_body="Plain body",
                email_body_html="<p>HTML body</p>",
                email_to="to@example.com, shared@example.com",
                email_cc="shared@example.com, cc@example.com",
                email_bcc="bcc@example.com",
                email_from="from@example.com",
                email_reply_to="reply@example.com",
                attachments=[
                    {
                        "filename": "hello.txt",
                        "content_base64": attachment_payload,
                        "content_type": "text/plain",
                    }
                ],
            ).execute({}, {})

            assert response["error"] is None
            assert response["command_response"]["body"] == "{}"
            assert "did send to 4 recipient(s)" in response["spiff__logs"]
            mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=11)
            smtp_instance.starttls.assert_called_once_with(context=mock_context.return_value)
            smtp_instance.login.assert_called_once_with("user", "pass")
            smtp_instance.send_message.assert_called_once()

            sent_message = smtp_instance.send_message.call_args.args[0]
            sent_to = smtp_instance.send_message.call_args.kwargs["to_addrs"]
            assert sent_message["Subject"] == "Subject"
            assert sent_message["From"] == "from@example.com"
            assert sent_message["To"] == "to@example.com, shared@example.com"
            assert sent_message["Cc"] == "shared@example.com, cc@example.com"
            assert sent_message["Reply-To"] == "reply@example.com"
            assert sent_to == [
                "to@example.com",
                "shared@example.com",
                "cc@example.com",
                "bcc@example.com",
            ]

            attachments = list(sent_message.iter_attachments())
            assert len(attachments) == 1
            assert attachments[0].get_filename() == "hello.txt"
            assert attachments[0].get_content_type() == "text/plain"

    def test_execute_returns_error_when_no_recipients_exist(self) -> None:
        with patch("connector_smtp.commands.send_email.SMTP") as mock_smtp:
            response = SendHTMLEmail(
                smtp_host="smtp.example.com",
                smtp_port=25,
                email_subject="Subject",
                email_body="Body",
                email_to="",
                email_cc="",
                email_bcc="",
                email_from="from@example.com",
            ).execute({}, {})

            assert response["error"] == {
                "error_code": "ValueError",
                "message": "No recipients provided (To/Cc/Bcc all empty).",
            }
            mock_smtp.assert_not_called()

    def test_execute_returns_attachment_error_before_opening_smtp(self) -> None:
        with patch("connector_smtp.commands.send_email.SMTP") as mock_smtp:
            response = SendHTMLEmail(
                smtp_host="smtp.example.com",
                smtp_port=25,
                email_subject="Subject",
                email_body="Body",
                email_to="to@example.com",
                email_from="from@example.com",
                attachments=[{"filename": "broken.txt"}],
            ).execute({}, {})

            assert response["error"]["error_code"] == "ValueError"
            assert "either 'path' or 'content_base64'" in response["error"]["message"]
            assert any("attachment error:" in log for log in response["spiff__logs"])
            mock_smtp.assert_not_called()

    def test_execute_returns_smtp_error(self) -> None:
        with patch("connector_smtp.commands.send_email.SMTP") as mock_smtp:
            smtp_instance = mock_smtp.return_value.__enter__.return_value
            smtp_instance.send_message.side_effect = RuntimeError("boom")

            response = SendHTMLEmail(
                smtp_host="smtp.example.com",
                smtp_port=25,
                email_subject="Subject",
                email_body="Body",
                email_to="to@example.com",
                email_from="from@example.com",
            ).execute({}, {})

            assert response["error"] == {"error_code": "RuntimeError", "message": "boom"}
            assert any("did error: boom" == log for log in response["spiff__logs"])
