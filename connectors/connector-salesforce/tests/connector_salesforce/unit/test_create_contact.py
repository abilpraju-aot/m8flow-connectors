"""Unit tests for CreateContact command."""
from unittest.mock import patch

from connector_salesforce.commands.create_contact import CreateContact


class TestCreateContact:
    def test_successful_create(self) -> None:
        success_data = {"id": "003xx", "success": True}
        with patch("connector_salesforce.commands.create_contact.request_with_retry") as mock_req:
            mock_req.return_value = (success_data, 201, None, "tok", "https://na1.salesforce.com")
            cmd = CreateContact("tok", "https://na1.salesforce.com", '{"LastName":"Smith"}')
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 201
            assert response["error"] is None
            mock_req.assert_called_once()
            assert mock_req.call_args[0][6] == "Contact"
            assert mock_req.call_args[1]["body"]["LastName"] == "Smith"

    def test_missing_required_last_name(self) -> None:
        cmd = CreateContact("tok", "https://na1.salesforce.com", "{}")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "SalesforceValidationError"
