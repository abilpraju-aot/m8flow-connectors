import json
from unittest.mock import patch

from connector_slack.commands.post_message import PostMessage


class TestPostMessage:
    def test_successful_post(self) -> None:
        success_response = {
            "ok": True,
            "channel": "C123456",
            "ts": "1503435956.000247",
            "message": {
                "text": "Here's a message for you",
                "username": "ecto1",
                "bot_id": "B123456",
                "type": "message",
                "subtype": "bot_message",
                "ts": "1503435956.000247",
            },
        }
        with patch("connector_slack.commands.post_message.post_json") as mock_post_json:
            mock_post_json.return_value = (success_response, 200, None)
            poster = PostMessage("xxx", "my_channel", "hello world!")
            response = poster.execute({}, {})
            assert response["command_response"] == {
                "body": json.dumps(success_response),
                "mimetype": "application/json",
                "http_status": 200,
            }
            assert response["error"] is None
            mock_post_json.assert_called_once()
            call_body = mock_post_json.call_args[0][2]
            assert call_body["channel"] == "my_channel"
            assert call_body["text"] == "hello world!"
            assert "blocks" not in call_body

    def test_successful_post_with_blocks(self) -> None:
        success_response = {"ok": True, "channel": "C123", "ts": "123.456"}
        blocks_json = '[{"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}]'
        with patch("connector_slack.commands.post_message.post_json") as mock_post_json:
            mock_post_json.return_value = (success_response, 200, None)
            poster = PostMessage("xxx", "C123", "fallback", blocks=blocks_json)
            response = poster.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            call_body = mock_post_json.call_args[0][2]
            assert call_body["blocks"] == [{"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}]
            assert call_body["text"] == "fallback"

    def test_invalid_blocks_json(self) -> None:
        poster = PostMessage("xxx", "my_channel", "hello", blocks="not valid json {")
        response = poster.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"] is not None
        assert response["error"]["error_code"] == "SlackMessageFailed"
        assert "Invalid blocks JSON" in response["error"]["message"]

    def test_connection_error(self) -> None:
        with patch("connector_slack.commands.post_message.post_json") as mock_post_json:
            mock_post_json.return_value = (
                {},
                404,
                {"error_code": "SlackMessageFailed", "message": "Unreadable (non JSON) response from Slack"},
            )
            poster = PostMessage("xxx", "my_channel", "hello world!")
            response = poster.execute({}, {})
            assert response["command_response"] == {
                "body": "{}",
                "mimetype": "application/json",
                "http_status": 404,
            }
            assert response["error"] is not None
            assert response["error"]["error_code"] == "SlackMessageFailed"
            assert response["error"]["message"] == "Unreadable (non JSON) response from Slack"

    def test_error_from_slack(self) -> None:
        with patch("connector_slack.commands.post_message.post_json") as mock_post_json:
            mock_post_json.return_value = (
                {},
                400,
                {"error_code": "SlackMessageFailed", "message": "[ERROR] missing required field: channel"},
            )
            poster = PostMessage("xxx", "my_channel", "hello world!")
            response = poster.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"] is not None
            assert response["error"]["error_code"] == "SlackMessageFailed"
            assert response["error"]["message"] == "[ERROR] missing required field: channel"
