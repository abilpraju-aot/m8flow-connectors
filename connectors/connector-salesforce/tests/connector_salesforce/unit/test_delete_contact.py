"""Unit tests for DeleteContact command."""
from unittest.mock import patch

from connector_salesforce.commands.delete_contact import DeleteContact


class TestDeleteContact:
    def test_successful_delete(self) -> None:
        with patch("connector_salesforce.commands.delete_contact.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 204, None, "tok", "https://na1.salesforce.com")
            cmd = DeleteContact("tok", "https://na1.salesforce.com", "003xx")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 204
            assert response["error"] is None

    def test_missing_record_id(self) -> None:
        cmd = DeleteContact("tok", "https://na1.salesforce.com", "")
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "SalesforceValidationError"
