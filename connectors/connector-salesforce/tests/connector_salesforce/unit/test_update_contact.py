"""Unit tests for UpdateContact command."""
from unittest.mock import patch

from connector_salesforce.commands.update_contact import UpdateContact


class TestUpdateContact:
    def test_successful_update(self) -> None:
        with patch("connector_salesforce.commands.update_contact.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 204, None, "tok", "https://na1.salesforce.com")
            cmd = UpdateContact("tok", "https://na1.salesforce.com", "003xx", '{"Email":"new@example.com"}')
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 204
            assert response["error"] is None
            assert mock_req.call_args[1]["body"]["Email"] == "new@example.com"

    def test_empty_fields_rejected(self) -> None:
        cmd = UpdateContact("tok", "https://na1.salesforce.com", "003xx", "{}")
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "SalesforceValidationError"
        assert "one field" in response["error"]["message"].lower()
