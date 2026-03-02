"""Unit tests for IssueRefund command."""
from unittest.mock import patch

from connector_stripe.commands.issue_refund import IssueRefund


class TestIssueRefund:
    def test_successful_full_refund(self) -> None:
        with patch("connector_stripe.commands.issue_refund.request_form") as mock_req:
            mock_req.return_value = ({"id": "re_123", "status": "succeeded"}, 200, None)
            cmd = IssueRefund("sk_test_123", charge_id="ch_123")
            response = cmd.execute({}, {"task_id": "task-r", "execution_id": "exec-1"})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            form_data = mock_req.call_args[1]["form_data"]
            assert form_data["charge"] == "ch_123"

    def test_successful_partial_refund(self) -> None:
        with patch("connector_stripe.commands.issue_refund.request_form") as mock_req:
            mock_req.return_value = ({"id": "re_124", "status": "succeeded"}, 200, None)
            cmd = IssueRefund("sk_test_123", payment_intent_id="pi_123", amount="500")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            form_data = mock_req.call_args[1]["form_data"]
            assert form_data["payment_intent"] == "pi_123"
            assert form_data["amount"] == "500"

    def test_invalid_reference_combination(self) -> None:
        cmd = IssueRefund("sk_test_123", charge_id="ch_123", payment_intent_id="pi_123")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"

    def test_insufficient_funds_negative(self) -> None:
        with patch("connector_stripe.commands.issue_refund.request_form") as mock_req:
            mock_req.return_value = (
                {},
                402,
                {"error_code": "StripeCardError", "message": "Insufficient funds"},
            )
            cmd = IssueRefund("sk_test_123", charge_id="ch_123", amount="999999")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 402
            assert response["error"] is not None
            assert response["error"]["error_code"] == "StripeCardError"
