"""Unit tests for CreateSubscription command."""
from unittest.mock import patch

from connector_stripe.commands.create_subscription import CreateSubscription


class TestCreateSubscription:
    def test_successful_create_subscription(self) -> None:
        with patch("connector_stripe.commands.create_subscription.request_form") as mock_req:
            mock_req.return_value = ({"id": "sub_123", "status": "active"}, 200, None)
            cmd = CreateSubscription("sk_test_123", "cus_123", "price_123", quantity="2")
            response = cmd.execute({}, {"task_id": "task-s", "execution_id": "exec-1"})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            form_data = mock_req.call_args[1]["form_data"]
            assert form_data["customer"] == "cus_123"
            assert form_data["items[0][price]"] == "price_123"
            assert form_data["items[0][quantity]"] == "2"
            assert mock_req.call_args[1]["idempotency_key"].startswith("m8stripe_create_subscription_")

    def test_missing_customer_returns_validation_error(self) -> None:
        cmd = CreateSubscription("sk_test_123", "", "price_123")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"

    def test_invalid_payment_method_negative(self) -> None:
        with patch("connector_stripe.commands.create_subscription.request_form") as mock_req:
            mock_req.return_value = (
                {},
                400,
                {"error_code": "StripeValidationError", "message": "No such PaymentMethod: pm_bad"},
            )
            cmd = CreateSubscription(
                "sk_test_123",
                "cus_123",
                "price_123",
                payment_method="pm_bad",
                idempotency_key="idem-sub-1",
            )
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"] is not None
            assert response["error"]["error_code"] == "StripeValidationError"
            assert mock_req.call_args[1]["idempotency_key"] == "idem-sub-1"
