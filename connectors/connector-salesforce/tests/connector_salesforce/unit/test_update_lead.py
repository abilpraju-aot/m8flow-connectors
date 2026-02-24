"""Unit tests for UpdateLead command."""
from unittest.mock import patch

from connector_salesforce.commands.update_lead import UpdateLead


class TestUpdateLead:
    def test_successful_update(self) -> None:
        with patch("connector_salesforce.commands.update_lead.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 204, None, "tok", "https://na1.salesforce.com")
            cmd = UpdateLead("tok", "https://na1.salesforce.com", "00Qxx", '{"Status":"Closed"}')
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 204
            assert response["error"] is None
            assert mock_req.call_args[0][5] == "PATCH"
            assert mock_req.call_args[1]["body"]["Status"] == "Closed"

    def test_missing_record_id(self) -> None:
        cmd = UpdateLead("tok", "https://na1.salesforce.com", "", '{"Status":"Open"}')
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "SalesforceValidationError"

    def test_invalid_fields_json(self) -> None:
        cmd = UpdateLead("tok", "https://na1.salesforce.com", "00Qxx", "not json")
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "SalesforceValidationError"
        assert "Invalid fields JSON" in response["error"]["message"]
