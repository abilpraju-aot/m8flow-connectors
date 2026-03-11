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

    def test_card_subscription_success(self) -> None:
        pm_data = {"id": "pm_card_abc", "object": "payment_method", "type": "card"}
        attach_data = {"id": "pm_card_abc", "customer": "cus_abc123"}
        sub_data = {"id": "sub_456", "object": "subscription", "status": "active"}
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.side_effect = [
                (pm_data, 200, None),
                (attach_data, 200, None),
                (sub_data, 200, None),
            ]
            cmd = CreateSubscription(
                api_key="sk_test_123",
                customer_id="cus_abc123",
                price_id="price_xyz789",
                card_number="4242424242424242",
                exp_month="12",
                exp_year="2026",
                cvc="123",
            )
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            assert mock_post.call_count == 3
            pm_call = mock_post.call_args_list[0]
            assert pm_call[0][0] == "payment_methods"
            assert pm_call[0][2]["type"] == "card"
            assert pm_call[0][2]["card[number]"] == "4242424242424242"
            attach_call = mock_post.call_args_list[1]
            assert attach_call[0][0] == "payment_methods/pm_card_abc/attach"
            assert attach_call[0][2]["customer"] == "cus_abc123"
            sub_call = mock_post.call_args_list[2]
            assert sub_call[0][0] == "subscriptions"
            assert sub_call[0][2]["default_payment_method"] == "pm_card_abc"

    def test_card_payment_method_creation_fails(self) -> None:
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.return_value = (
                {},
                402,
                {"error_code": "StripeCardError", "message": "Your card was declined."},
            )
            cmd = CreateSubscription(
                api_key="sk_test_123",
                customer_id="cus_abc123",
                price_id="price_xyz789",
                card_number="4000000000000002",
                exp_month="12",
                exp_year="2026",
                cvc="123",
            )
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 402
            assert response["error"]["error_code"] == "StripeCardError"
            mock_post.assert_called_once()

    def test_card_attach_fails(self) -> None:
        pm_data = {"id": "pm_card_abc", "object": "payment_method"}
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.side_effect = [
                (pm_data, 200, None),
                ({}, 400, {"error_code": "StripeValidationError", "message": "No such customer"}),
            ]
            cmd = CreateSubscription(
                api_key="sk_test_123",
                customer_id="cus_abc123",
                price_id="price_xyz789",
                card_number="4242424242424242",
                exp_month="12",
                exp_year="2026",
                cvc="123",
            )
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"]["error_code"] == "StripeValidationError"
            assert mock_post.call_count == 2

    def test_partial_card_fields_returns_error(self) -> None:
        cmd = CreateSubscription(
            api_key="sk_test_123",
            customer_id="cus_abc123",
            price_id="price_xyz789",
            card_number="4242424242424242",
            exp_month="12",
        )
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "Missing" in response["error"]["message"]
        assert "cvc" in response["error"]["message"]
        assert "exp_year" in response["error"]["message"]

    def test_no_card_fields_backward_compatible(self) -> None:
        success_data = {"id": "sub_789", "object": "subscription"}
        with patch("connector_stripe.commands.create_subscription.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreateSubscription("sk_test_123", "cus_abc123", "price_xyz789")
            response = cmd.execute({}, {})
            assert response["error"] is None
            mock_post.assert_called_once()
            assert mock_post.call_args[0][0] == "subscriptions"
