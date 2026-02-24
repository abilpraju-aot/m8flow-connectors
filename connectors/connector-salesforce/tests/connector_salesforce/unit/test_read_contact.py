"""Unit tests for ReadContact command."""
from unittest.mock import patch

from connector_salesforce.commands.read_contact import ReadContact


class TestReadContact:
    def test_successful_read(self) -> None:
        record = {"Id": "003xx", "LastName": "Smith"}
        with patch("connector_salesforce.commands.read_contact.request_with_retry") as mock_req:
            mock_req.return_value = (record, 200, None, "tok", "https://na1.salesforce.com")
            cmd = ReadContact("tok", "https://na1.salesforce.com", "003xx")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            assert mock_req.call_args[0][6] == "Contact/003xx"

    def test_missing_record_id(self) -> None:
        cmd = ReadContact("tok", "https://na1.salesforce.com", "  ")
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "SalesforceValidationError"
