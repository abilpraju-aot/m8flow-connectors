import json
from unittest.mock import patch

from connector_slack.commands.send_direct_message import SendDirectMessage


class TestSendDirectMessage:
    def test_successful_dm(self) -> None:
        success_response = {"ok": True, "channel": "D123", "ts": "1503435956.000247", "message": {"text": "DM sent"}}
        with patch("connector_slack.commands.send_direct_message.post_json") as mock_post_json:
            mock_post_json.return_value = (success_response, 200, None)
            cmd = SendDirectMessage("xxx", "U12345", "hello!")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            call_body = mock_post_json.call_args[0][2]
            assert call_body["channel"] == "U12345"
            assert call_body["text"] == "hello!"
            assert "blocks" not in call_body

    def test_successful_dm_with_blocks(self) -> None:
        success_response = {"ok": True, "channel": "D123", "ts": "123.456"}
        blocks_json = '[{"type": "section", "text": {"type": "mrkdwn", "text": "DM block"}}]'
        with patch("connector_slack.commands.send_direct_message.post_json") as mock_post_json:
            mock_post_json.return_value = (success_response, 200, None)
            cmd = SendDirectMessage("xxx", "U999", "fallback", blocks=blocks_json)
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            call_body = mock_post_json.call_args[0][2]
            assert call_body["channel"] == "U999"
            assert call_body["blocks"] == [{"type": "section", "text": {"type": "mrkdwn", "text": "DM block"}}]

    def test_invalid_blocks_json(self) -> None:
        cmd = SendDirectMessage("xxx", "U123", "hi", blocks="not json [")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "SlackMessageFailed"
        assert "Invalid blocks JSON" in response["error"]["message"]

    def test_error_from_slack(self) -> None:
        with patch("connector_slack.commands.send_direct_message.post_json") as mock_post_json:
            mock_post_json.return_value = (
                {},
                400,
                {"error_code": "SlackMessageFailed", "message": "user_not_found"},
            )
            cmd = SendDirectMessage("xxx", "U000", "hi")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"]["message"] == "user_not_found"
