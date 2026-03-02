"""Unit tests for CreateCharge command."""
from unittest.mock import patch

from connector_stripe.commands.create_charge import CreateCharge


class TestCreateCharge:
    def test_successful_create(self) -> None:
        success_data = {
            "id": "ch_123",
            "object": "charge",
            "amount": 1000,
            "currency": "usd",
            "status": "succeeded",
        }
        with patch("connector_stripe.commands.create_charge.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreateCharge("sk_test_123", "1000", "usd", "tok_visa")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "charges"
            assert call_args[0][2]["amount"] == 1000
            assert call_args[0][2]["currency"] == "usd"
            assert call_args[0][2]["source"] == "tok_visa"

    def test_with_optional_params(self) -> None:
        success_data = {"id": "ch_123", "object": "charge", "status": "succeeded"}
        with patch("connector_stripe.commands.create_charge.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CreateCharge(
                api_key="sk_test_123",
                amount="5000",
                currency="gbp",
                source="tok_mastercard",
                customer_id="cus_abc123",
                description="Order #456",
                metadata='{"order_id": "456"}',
                idempotency_key="charge-idem-123",
            )
            response = cmd.execute({}, {})
            assert response["error"] is None
            call_args = mock_post.call_args
            assert call_args[0][2]["customer"] == "cus_abc123"
            assert call_args[0][2]["description"] == "Order #456"
            assert call_args[0][2]["metadata"] == {"order_id": "456"}
            assert call_args[0][3] == "charge-idem-123"

    def test_missing_source(self) -> None:
        cmd = CreateCharge("sk_test_123", "1000", "usd", "")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "source" in response["error"]["message"].lower()

    def test_invalid_amount(self) -> None:
        cmd = CreateCharge("sk_test_123", "abc", "usd", "tok_visa")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"

    def test_invalid_currency(self) -> None:
        cmd = CreateCharge("sk_test_123", "1000", "xy", "tok_visa")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "3-letter" in response["error"]["message"]

    def test_card_declined(self) -> None:
        with patch("connector_stripe.commands.create_charge.post") as mock_post:
            mock_post.return_value = (
                {},
                402,
                {"error_code": "StripeCardError", "message": "Your card was declined"},
            )
            cmd = CreateCharge("sk_test_123", "1000", "usd", "tok_chargeDeclined")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 402
            assert response["error"]["error_code"] == "StripeCardError"

    def test_idempotency_key_passthrough(self) -> None:
        with patch("connector_stripe.commands.create_charge.post") as mock_post:
            mock_post.return_value = ({"id": "ch_123"}, 200, None)
            cmd = CreateCharge("sk_test_123", "1000", "usd", "tok_visa", idempotency_key="my-key-123")
            cmd.execute({}, {})
            call_args = mock_post.call_args
            assert call_args[0][3] == "my-key-123"
