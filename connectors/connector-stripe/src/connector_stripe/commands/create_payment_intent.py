"""Create a Stripe Payment Intent for card payments."""
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import generate_idempotency_key
from connector_stripe.stripe_client import post
from connector_stripe.validation import StripeValidationError
from connector_stripe.validation import validate_amount
from connector_stripe.validation import validate_boolean_string
from connector_stripe.validation import validate_currency
from connector_stripe.validation import validate_optional_json
from connector_stripe.validation import validate_optional_stripe_id


class CreatePaymentIntent(ConnectorCommand):
    """Create a Stripe Payment Intent for processing card payments."""

    def __init__(
        self,
        api_key: str,
        amount: str,
        currency: str,
        customer_id: str = "",
        payment_method: str = "",
        confirm: str = "false",
        description: str = "",
        metadata: str = "",
        idempotency_key: str = "",
    ):
        """
        :param api_key: Stripe secret API key (sk_test_... or sk_live_...).
        :param amount: Amount in smallest currency unit (e.g., 1000 = $10.00 for USD).
        :param currency: 3-letter ISO currency code (e.g., usd, eur, gbp).
        :param customer_id: Optional Stripe customer ID (cus_...).
        :param payment_method: Optional payment method ID (pm_...).
        :param confirm: Whether to confirm the payment intent immediately (true/false).
        :param description: Optional description for the payment.
        :param metadata: Optional JSON string of metadata key-value pairs.
        :param idempotency_key: Optional unique key to prevent duplicate operations.
        """
        self.api_key = api_key
        self.amount = amount
        self.currency = currency
        self.customer_id = customer_id
        self.payment_method = payment_method
        self.confirm = confirm
        self.description = description
        self.metadata = metadata
        self.idempotency_key = idempotency_key

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            amount_int = validate_amount(self.amount)
            currency = validate_currency(self.currency)
            customer_id = validate_optional_stripe_id(self.customer_id, "cus_", "customer_id")
            payment_method = validate_optional_stripe_id(self.payment_method, "pm_", "payment_method")
            confirm = validate_boolean_string(self.confirm, default=False)
            metadata = validate_optional_json(self.metadata, "metadata")
        except StripeValidationError as exc:
            return error_response(400, "StripeValidationError", exc.message)

        data: dict[str, Any] = {
            "amount": amount_int,
            "currency": currency,
        }

        if customer_id:
            data["customer"] = customer_id
        if payment_method:
            data["payment_method"] = payment_method
        if confirm:
            data["confirm"] = "true"
        if self.description.strip():
            data["description"] = self.description.strip()
        if metadata:
            data["metadata"] = metadata

        idempotency_key = self.idempotency_key.strip() or generate_idempotency_key()
        response_json, status, error = post("payment_intents", self.api_key, data, idempotency_key)
        return build_result(response_json, status, error)
