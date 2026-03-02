"""Create a Stripe Subscription for recurring billing."""
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import generate_idempotency_key
from connector_stripe.stripe_client import post
from connector_stripe.validation import StripeValidationError
from connector_stripe.validation import validate_optional_json
from connector_stripe.validation import validate_required
from connector_stripe.validation import validate_stripe_id


class CreateSubscription(ConnectorCommand):
    """Create a Stripe Subscription for recurring billing."""

    def __init__(
        self,
        api_key: str,
        customer_id: str,
        price_id: str,
        payment_behavior: str = "default_incomplete",
        default_payment_method: str = "",
        metadata: str = "",
        idempotency_key: str = "",
    ):
        """
        :param api_key: Stripe secret API key (sk_test_... or sk_live_...).
        :param customer_id: Stripe customer ID (cus_...).
        :param price_id: Stripe price ID (price_...) for the subscription item.
        :param payment_behavior: Payment behavior (default_incomplete, error_if_incomplete, allow_incomplete).
        :param default_payment_method: Optional default payment method ID (pm_...).
        :param metadata: Optional JSON string of metadata key-value pairs.
        :param idempotency_key: Optional unique key to prevent duplicate operations.
        """
        self.api_key = api_key
        self.customer_id = customer_id
        self.price_id = price_id
        self.payment_behavior = payment_behavior
        self.default_payment_method = default_payment_method
        self.metadata = metadata
        self.idempotency_key = idempotency_key

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            customer_id = validate_stripe_id(self.customer_id, "cus_", "customer_id")
            price_id = validate_stripe_id(self.price_id, "price_", "price_id")
            payment_behavior = validate_required(self.payment_behavior, "payment_behavior")
            metadata = validate_optional_json(self.metadata, "metadata")
        except StripeValidationError as exc:
            return error_response(400, "StripeValidationError", exc.message)

        valid_behaviors = ("default_incomplete", "error_if_incomplete", "allow_incomplete", "pending_if_incomplete")
        if payment_behavior not in valid_behaviors:
            return error_response(
                400,
                "StripeValidationError",
                f"payment_behavior must be one of {valid_behaviors}, got: {payment_behavior}",
            )

        data: dict[str, Any] = {
            "customer": customer_id,
            "items[0][price]": price_id,
            "payment_behavior": payment_behavior,
        }

        if self.default_payment_method.strip():
            data["default_payment_method"] = self.default_payment_method.strip()
        if metadata:
            data["metadata"] = metadata

        idempotency_key = self.idempotency_key.strip() or generate_idempotency_key()
        response_json, status, error = post("subscriptions", self.api_key, data, idempotency_key)
        return build_result(response_json, status, error)
