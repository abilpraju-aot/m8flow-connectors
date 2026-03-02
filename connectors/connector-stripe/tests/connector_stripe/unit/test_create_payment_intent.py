"""Unit tests for CreatePaymentIntent command."""
from unittest.mock import patch

from connector_stripe.commands.create_payment_intent import CreatePaymentIntent


class TestCreatePaymentIntent:
    def test_successful_create(self) -> None:
        success_data = {
            "id": "pi_123",
            "object": "payment_intent",
            "amount": 1000,
            "currency": "usd",
            "status": "requires_payment_method",
        }
        with patch("connector_stripe.commands.create_payment_intent.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreatePaymentIntent("sk_test_123", "1000", "usd")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "payment_intents"
            assert call_args[0][2]["amount"] == 1000
            assert call_args[0][2]["currency"] == "usd"

    def test_with_all_optional_params(self) -> None:
        success_data = {"id": "pi_123", "object": "payment_intent", "status": "requires_confirmation"}
        with patch("connector_stripe.commands.create_payment_intent.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreatePaymentIntent(
                api_key="sk_test_123",
                amount="2000",
                currency="eur",
                customer_id="cus_abc123",
                payment_method="pm_xyz789",
                confirm="true",
                description="Test payment",
                metadata='{"order_id": "123"}',
                idempotency_key="idem-key-123",
            )
            response = cmd.execute({}, {})
            assert response["error"] is None
            call_args = mock_post.call_args
            assert call_args[0][2]["customer"] == "cus_abc123"
            assert call_args[0][2]["payment_method"] == "pm_xyz789"
            assert call_args[0][2]["confirm"] == "true"
            assert call_args[0][2]["description"] == "Test payment"
            assert call_args[0][2]["metadata"] == {"order_id": "123"}
            assert call_args[0][3] == "idem-key-123"

    def test_invalid_amount_not_integer(self) -> None:
        cmd = CreatePaymentIntent("sk_test_123", "not_a_number", "usd")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"] is not None
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "Amount must be a valid integer" in response["error"]["message"]

    def test_invalid_amount_negative(self) -> None:
        cmd = CreatePaymentIntent("sk_test_123", "-100", "usd")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "positive" in response["error"]["message"].lower()

    def test_invalid_currency(self) -> None:
        cmd = CreatePaymentIntent("sk_test_123", "1000", "invalid")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "3-letter ISO code" in response["error"]["message"]

    def test_invalid_customer_id_prefix(self) -> None:
        cmd = CreatePaymentIntent("sk_test_123", "1000", "usd", customer_id="invalid_123")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "cus_" in response["error"]["message"]

    def test_invalid_metadata_json(self) -> None:
        cmd = CreatePaymentIntent("sk_test_123", "1000", "usd", metadata="not valid json {")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "Invalid JSON" in response["error"]["message"]

    def test_auto_generates_idempotency_key(self) -> None:
        with patch("connector_stripe.commands.create_payment_intent.post") as mock_post:
            mock_post.return_value = ({"id": "pi_123"}, 200, None)
            cmd = CreatePaymentIntent("sk_test_123", "1000", "usd")
            cmd.execute({}, {})
            call_args = mock_post.call_args
            idempotency_key = call_args[0][3]
            assert idempotency_key is not None
            assert len(idempotency_key) == 36  # UUID format

    def test_stripe_api_error(self) -> None:
        with patch("connector_stripe.commands.create_payment_intent.post") as mock_post:
            mock_post.return_value = (
                {},
                401,
                {"error_code": "StripeAuthError", "message": "Invalid API key"},
            )
            cmd = CreatePaymentIntent("sk_test_invalid", "1000", "usd")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 401
            assert response["error"]["error_code"] == "StripeAuthError"

    def test_card_error(self) -> None:
        with patch("connector_stripe.commands.create_payment_intent.post") as mock_post:
            mock_post.return_value = (
                {},
                402,
                {"error_code": "StripeCardError", "message": "Your card was declined (decline_code: insufficient_funds)"},
            )
            cmd = CreatePaymentIntent("sk_test_123", "1000", "usd", confirm="true")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 402
            assert response["error"]["error_code"] == "StripeCardError"
            assert "declined" in response["error"]["message"].lower()
