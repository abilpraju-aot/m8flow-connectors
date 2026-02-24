"""Negative tests for Salesforce client error mapping (401, 403, validation, API errors)."""
from unittest.mock import patch

from connector_salesforce.salesforce_client import _parse_salesforce_errors
from connector_salesforce.salesforce_client import get
from connector_salesforce.salesforce_client import refresh_access_token


class TestSalesforceAuthErrors:
    def test_401_returns_salesforce_auth_error(self) -> None:
        status, err = _parse_salesforce_errors(b'{"errorCode":"INVALID_SESSION_ID","message":"Session expired"}', 401)
        assert status == 401
        assert err is not None
        assert err["error_code"] == "SalesforceAuthError"
        assert "Authentication failed" in err["message"] or "token" in err["message"].lower()

    def test_get_returns_error_on_401_response(self) -> None:
        with patch("connector_salesforce.salesforce_client._request") as mock_req:
            mock_req.return_value = (
                {}, 401,
                {"error_code": "SalesforceAuthError", "message": "Authentication failed or token expired."},
            )
            _data, status, error = get("https://na1.salesforce.com", "token", "Lead/00Qxx")
            assert status == 401
            assert error is not None
            assert error["error_code"] == "SalesforceAuthError"


class TestSalesforcePermissionErrors:
    def test_403_returns_salesforce_permission_error(self) -> None:
        status, err = _parse_salesforce_errors(b'{"message":"Insufficient privileges"}', 403)
        assert status == 403
        assert err is not None
        assert err["error_code"] == "SalesforcePermissionError"


class TestSalesforceValidationErrors:
    def test_400_returns_salesforce_validation_error(self) -> None:
        body = b'[{"errorCode":"REQUIRED_FIELD_MISSING","message":"Required fields are missing: [LastName]"}]'
        status, err = _parse_salesforce_errors(body, 400)
        assert status == 400
        assert err is not None
        assert err["error_code"] == "SalesforceValidationError"


class TestTokenRefresh:
    def test_refresh_failure_returns_auth_error(self) -> None:
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.headers = {"Content-Type": "application/json"}
            mock_post.return_value.json.return_value = {"error": "invalid_grant", "error_description": "expired"}
            tok, inst, err = refresh_access_token("refresh", "cid", "csec", "https://na1.salesforce.com")
            assert tok is None
            assert err is not None
            assert err["error_code"] == "SalesforceAuthError"
