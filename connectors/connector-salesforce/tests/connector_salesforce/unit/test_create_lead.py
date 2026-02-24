"""Unit tests for CreateLead command."""
from unittest.mock import patch

from connector_salesforce.commands.create_lead import CreateLead


class TestCreateLead:
    def test_successful_create(self) -> None:
        success_data = {"id": "00Qxx", "success": True}
        with patch("connector_salesforce.commands.create_lead.request_with_retry") as mock_req:
            mock_req.return_value = (success_data, 201, None, "tok", "https://na1.salesforce.com")
            cmd = CreateLead("tok", "https://na1.salesforce.com", '{"LastName":"Doe","Company":"Acme"}')
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 201
            assert response["error"] is None
            mock_req.assert_called_once()
            assert mock_req.call_args[0][5] == "POST"
            assert mock_req.call_args[0][6] == "Lead"
            assert mock_req.call_args[1]["body"]["LastName"] == "Doe"
            assert mock_req.call_args[1]["body"]["Company"] == "Acme"

    def test_invalid_fields_json(self) -> None:
        cmd = CreateLead("tok", "https://na1.salesforce.com", "not valid json {")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"] is not None
        assert response["error"]["error_code"] == "SalesforceValidationError"
        assert "Invalid fields JSON" in response["error"]["message"]

    def test_missing_required_fields(self) -> None:
        cmd = CreateLead("tok", "https://na1.salesforce.com", '{"LastName":"Doe"}')
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "SalesforceValidationError"
        assert "Company" in response["error"]["message"] or "required" in response["error"]["message"].lower()

    def test_api_error_from_salesforce(self) -> None:
        with patch("connector_salesforce.commands.create_lead.request_with_retry") as mock_req:
            mock_req.return_value = (
                {},
                400,
                {"error_code": "SalesforceValidationError", "message": "Required fields are missing: [Company]"},
                "tok",
                "https://na1.salesforce.com",
            )
            cmd = CreateLead("tok", "https://na1.salesforce.com", '{"LastName":"Doe","Company":"Acme"}')
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"]["error_code"] == "SalesforceValidationError"
