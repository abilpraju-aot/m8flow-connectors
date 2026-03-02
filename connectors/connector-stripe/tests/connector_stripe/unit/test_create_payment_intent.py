"""Unit tests for CreatePaymentIntent command."""
from unittest.mock import patch

from connector_stripe.commands.create_payment_intent import CreatePaymentIntent


class TestCreatePaymentIntent:
    def test_successful_create_payment_intent(self) -> None:
        with patch("connector_stripe.commands.create_payment_intent.request_form") as mock_req:
            mock_req.return_value = ({"id": "pi_123", "status": "requires_confirmation"}, 200, None)
            cmd = CreatePaymentIntent("sk_test_123", "1099", "USD", customer_id="cus_123", payment_method="pm_123")
            response = cmd.execute({}, {"task_id": "task-a", "execution_id": "exec-1"})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            assert mock_req.call_args[0][0] == "POST"
            assert mock_req.call_args[0][1] == "payment_intents"
            assert mock_req.call_args[1]["idempotency_key"].startswith("m8stripe_create_payment_intent_")
            form_data = mock_req.call_args[1]["form_data"]
            assert form_data["amount"] == "1099"
            assert form_data["currency"] == "usd"
            assert form_data["customer"] == "cus_123"
            assert form_data["payment_method"] == "pm_123"

    def test_invalid_amount_returns_validation_error(self) -> None:
        cmd = CreatePaymentIntent("sk_test_123", "0", "usd")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"] is not None
        assert response["error"]["error_code"] == "StripeValidationError"

    def test_provided_idempotency_key_is_used(self) -> None:
        with patch("connector_stripe.commands.create_payment_intent.request_form") as mock_req:
            mock_req.return_value = ({"id": "pi_123"}, 200, None)
            cmd = CreatePaymentIntent("sk_test_123", "1000", "usd", idempotency_key="idem-manual")
            _response = cmd.execute({}, {"task_id": "task-a"})
            assert mock_req.call_args[1]["idempotency_key"] == "idem-manual"
