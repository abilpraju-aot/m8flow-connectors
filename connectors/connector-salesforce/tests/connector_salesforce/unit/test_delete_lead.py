"""Unit tests for DeleteLead command."""
from unittest.mock import patch

from connector_salesforce.commands.delete_lead import DeleteLead


class TestDeleteLead:
    def test_successful_delete(self) -> None:
        with patch("connector_salesforce.commands.delete_lead.request_with_retry") as mock_req:
            mock_req.return_value = ({}, 204, None, "tok", "https://na1.salesforce.com")
            cmd = DeleteLead("tok", "https://na1.salesforce.com", "00Qxx")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 204
            assert response["error"] is None
            assert mock_req.call_args[0][5] == "DELETE"

    def test_missing_record_id(self) -> None:
        cmd = DeleteLead("tok", "https://na1.salesforce.com", "")
        response = cmd.execute({}, {})
        assert response["error"]["error_code"] == "SalesforceValidationError"
