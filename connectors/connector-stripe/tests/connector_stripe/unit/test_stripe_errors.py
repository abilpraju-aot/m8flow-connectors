"""Tests for Stripe client error mapping and idempotency behavior."""

from connector_stripe.stripe_client import _parse_stripe_error
from connector_stripe.stripe_client import resolve_idempotency_key


class TestStripeErrors:
    def test_auth_error_mapping(self) -> None:
        status, err = _parse_stripe_error(b'{"error":{"type":"invalid_request_error","message":"Invalid API Key"}}', 401)
        assert status == 401
        assert err["error_code"] == "StripeAuthError"

    def test_card_error_mapping(self) -> None:
        status, err = _parse_stripe_error(
            b'{"error":{"type":"card_error","code":"card_declined","message":"Your card was declined."}}',
            402,
        )
        assert status == 402
        assert err["error_code"] == "StripeCardError"

    def test_rate_limit_error_mapping(self) -> None:
        status, err = _parse_stripe_error(b'{"error":{"message":"Too many requests"}}', 429)
        assert status == 429
        assert err["error_code"] == "StripeRateLimitError"

    def test_validation_error_mapping(self) -> None:
        status, err = _parse_stripe_error(
            b'{"error":{"type":"invalid_request_error","message":"Invalid payment method"}}',
            400,
        )
        assert status == 400
        assert err["error_code"] == "StripeValidationError"


class TestIdempotencyResolution:
    def test_deterministic_auto_key_with_task_data(self) -> None:
        payload = {"amount": 1000, "currency": "usd"}
        task_data = {"task_id": "task-1", "execution_id": "exec-1"}
        key_a = resolve_idempotency_key("", "create_payment_intent", payload, task_data)
        key_b = resolve_idempotency_key("", "create_payment_intent", payload, task_data)
        assert key_a == key_b
        assert key_a.startswith("m8stripe_create_payment_intent_")

    def test_fallback_key_when_no_task_data(self) -> None:
        payload = {"amount": 1000, "currency": "usd"}
        key = resolve_idempotency_key("", "create_payment_intent", payload, None)
        assert key.startswith("m8stripe_create_payment_intent_")

    def test_preserves_provided_key(self) -> None:
        key = resolve_idempotency_key("client-key", "create_payment_intent", {"amount": 10}, {})
        assert key == "client-key"
