"""Upload a file to a Slack channel or DM via the external-upload API.
Uses files.getUploadURLExternal + files.completeUploadExternal (files.upload was sunset Nov 2025)."""
from typing import Any

from connector_slack.connector_interface import ConnectorCommand, ConnectorProxyResponseDict
from connector_slack.slack_client import (
    build_result,
    complete_upload_external,
    error_response,
    get_upload_url_external,
    upload_file_bytes,
)


class UploadFile(ConnectorCommand):
    """Upload a file to a Slack channel or DM."""

    def __init__(self, token: str, channel: str, content: str = "", filename: str = "", initial_comment: str = ""):
        self.token = token
        self.channel = channel
        self.content = content or ""
        self.filename = filename or "upload.txt"
        self.initial_comment = initial_comment or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not self.content.strip():
            return error_response(400, "SlackMissingContent", "File content must not be empty.")

        content_bytes = self.content.encode("utf-8")

        url_json, url_status, url_err = get_upload_url_external(self.token, self.filename, len(content_bytes))
        if url_err:
            return build_result(url_json, url_status, url_err)

        upload_url = url_json.get("upload_url", "")
        file_id = url_json.get("file_id", "")
        if not upload_url or not file_id:
            return error_response(500, "SlackUploadFailed", "Slack did not return upload_url or file_id.")

        put_status, put_err = upload_file_bytes(upload_url, self.filename, content_bytes)
        if put_err:
            return error_response(put_status, put_err["error_code"], put_err["message"])

        complete_json, complete_status, complete_err = complete_upload_external(
            self.token, file_id, self.filename, channel_id=self.channel, initial_comment=self.initial_comment,
        )
        return build_result(complete_json, complete_status, complete_err)
