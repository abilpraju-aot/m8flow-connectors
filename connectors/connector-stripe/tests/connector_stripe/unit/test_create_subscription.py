"""Unit tests for CreateSubscription command."""
from unittest.mock import patch

from connector_stripe.commands.create_subscription import CreateSubscription


class TestCreateSubscription:
    def test_successful_create(self) -> None:
        success_data = {
            "id": "sub_123",
            "object": "subscription",
            "status": "active",
            "customer": "cus_abc123",
        }
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreateSubscription("sk_test_123", "cus_abc123", "price_xyz789")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "subscriptions"
            assert call_args[0][2]["customer"] == "cus_abc123"
            assert call_args[0][2]["items[0][price]"] == "price_xyz789"

    def test_with_optional_params(self) -> None:
        success_data = {"id": "sub_123", "object": "subscription", "status": "incomplete"}
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreateSubscription(
                api_key="sk_test_123",
                customer_id="cus_abc123",
                price_id="price_xyz789",
                payment_behavior="error_if_incomplete",
                default_payment_method="pm_card123",
                metadata='{"plan": "premium"}',
                idempotency_key="sub-idem-123",
            )
            response = cmd.execute({}, {})
            assert response["error"] is None
            call_args = mock_post.call_args
            assert call_args[0][2]["payment_behavior"] == "error_if_incomplete"
            assert call_args[0][2]["default_payment_method"] == "pm_card123"
            assert call_args[0][2]["metadata"] == {"plan": "premium"}
            assert call_args[0][3] == "sub-idem-123"

    def test_invalid_customer_id(self) -> None:
        cmd = CreateSubscription("sk_test_123", "invalid_customer", "price_xyz789")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "cus_" in response["error"]["message"]

    def test_invalid_price_id(self) -> None:
        cmd = CreateSubscription("sk_test_123", "cus_abc123", "invalid_price")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "price_" in response["error"]["message"]

    def test_missing_customer_id(self) -> None:
        cmd = CreateSubscription("sk_test_123", "", "price_xyz789")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"

    def test_invalid_payment_behavior(self) -> None:
        cmd = CreateSubscription("sk_test_123", "cus_abc123", "price_xyz789", payment_behavior="invalid_behavior")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "payment_behavior" in response["error"]["message"]

    def test_stripe_api_error(self) -> None:
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.return_value = (
                {},
                400,
                {"error_code": "StripeValidationError", "message": "No such customer: cus_invalid"},
            )
            cmd = CreateSubscription("sk_test_123", "cus_invalid", "price_xyz789")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"]["error_code"] == "StripeValidationError"

    def test_auto_generates_idempotency_key(self) -> None:
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.return_value = ({"id": "sub_123"}, 200, None)
            cmd = CreateSubscription("sk_test_123", "cus_abc123", "price_xyz789")
            cmd.execute({}, {})
            call_args = mock_post.call_args
            idempotency_key = call_args[0][3]
            assert idempotency_key is not None
            assert len(idempotency_key) == 36
