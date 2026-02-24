"""Unit tests for ReadLead command."""
from unittest.mock import patch

from connector_salesforce.commands.read_lead import ReadLead


class TestReadLead:
    def test_successful_read(self) -> None:
        record = {"Id": "00Qxx", "LastName": "Doe", "Company": "Acme"}
        with patch("connector_salesforce.commands.read_lead.request_with_retry") as mock_req:
            mock_req.return_value = (record, 200, None, "tok", "https://na1.salesforce.com")
            cmd = ReadLead("tok", "https://na1.salesforce.com", "00Qxx")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_req.assert_called_once()
            assert mock_req.call_args[0][5] == "GET"
            assert "Lead/00Qxx" in mock_req.call_args[0][6]

    def test_missing_record_id(self) -> None:
        cmd = ReadLead("tok", "https://na1.salesforce.com", "")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "SalesforceValidationError"
        assert "record_id" in response["error"]["message"].lower()

    def test_401_returns_error(self) -> None:
        with patch("connector_salesforce.commands.read_lead.request_with_retry") as mock_req:
            mock_req.return_value = (
                {},
                401,
                {"error_code": "SalesforceAuthError", "message": "Authentication failed or token expired."},
                "tok",
                "https://na1.salesforce.com",
            )
            cmd = ReadLead("tok", "https://na1.salesforce.com", "00Qxx")
            response = cmd.execute({}, {})
            assert response["error"]["error_code"] == "SalesforceAuthError"
