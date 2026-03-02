"""Unit tests for CreateCharge command."""
from unittest.mock import patch

from connector_stripe.commands.create_charge import CreateCharge


class TestCreateCharge:
    def test_successful_create_charge_with_payment_method(self) -> None:
        """Test that pm_ prefixed IDs use payment_method parameter."""
        with patch("connector_stripe.commands.create_charge.request_form") as mock_req:
            mock_req.return_value = ({"id": "ch_123", "paid": True}, 200, None)
            cmd = CreateCharge("sk_test_123", "1200", "usd", payment_method="pm_card_visa")
            response = cmd.execute({}, {"task_id": "task-c", "execution_id": "exec-1"})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            assert mock_req.call_args[0][1] == "charges"
            form_data = mock_req.call_args[1]["form_data"]
            assert form_data["payment_method"] == "pm_card_visa"
            assert "source" not in form_data
            assert mock_req.call_args[1]["idempotency_key"].startswith("m8stripe_create_charge_")

    def test_successful_create_charge_with_legacy_source(self) -> None:
        """Test that non-pm_ IDs use source parameter (legacy tokens)."""
        with patch("connector_stripe.commands.create_charge.request_form") as mock_req:
            mock_req.return_value = ({"id": "ch_123", "paid": True}, 200, None)
            cmd = CreateCharge("sk_test_123", "1200", "usd", payment_method="tok_visa")
            response = cmd.execute({}, {"task_id": "task-c", "execution_id": "exec-1"})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            form_data = mock_req.call_args[1]["form_data"]
            assert form_data["source"] == "tok_visa"
            assert "payment_method" not in form_data

    def test_requires_customer_or_payment_method(self) -> None:
        cmd = CreateCharge("sk_test_123", "1000", "usd")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "Either customer_id or payment_method" in response["error"]["message"]
