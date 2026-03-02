"""Create a Stripe Charge (legacy API)."""
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import generate_idempotency_key
from connector_stripe.stripe_client import post
from connector_stripe.validation import StripeValidationError
from connector_stripe.validation import validate_amount
from connector_stripe.validation import validate_currency
from connector_stripe.validation import validate_optional_json
from connector_stripe.validation import validate_optional_stripe_id
from connector_stripe.validation import validate_required


class CreateCharge(ConnectorCommand):
    """Create a Stripe Charge using the legacy Charges API."""

    def __init__(
        self,
        api_key: str,
        amount: str,
        currency: str,
        source: str,
        customer_id: str = "",
        description: str = "",
        metadata: str = "",
        idempotency_key: str = "",
    ):
        """
        :param api_key: Stripe secret API key (sk_test_... or sk_live_...).
        :param amount: Amount in smallest currency unit (e.g., 1000 = $10.00 for USD).
        :param currency: 3-letter ISO currency code (e.g., usd, eur, gbp).
        :param source: Payment source token (tok_...) or card ID.
        :param customer_id: Optional Stripe customer ID (cus_...).
        :param description: Optional description for the charge.
        :param metadata: Optional JSON string of metadata key-value pairs.
        :param idempotency_key: Optional unique key to prevent duplicate operations.
        """
        self.api_key = api_key
        self.amount = amount
        self.currency = currency
        self.source = source
        self.customer_id = customer_id
        self.description = description
        self.metadata = metadata
        self.idempotency_key = idempotency_key

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            amount_int = validate_amount(self.amount)
            currency = validate_currency(self.currency)
            source = validate_required(self.source, "source")
            customer_id = validate_optional_stripe_id(self.customer_id, "cus_", "customer_id")
            metadata = validate_optional_json(self.metadata, "metadata")
        except StripeValidationError as exc:
            return error_response(400, "StripeValidationError", exc.message)

        data: dict[str, Any] = {
            "amount": amount_int,
            "currency": currency,
            "source": source,
        }

        if customer_id:
            data["customer"] = customer_id
        if self.description.strip():
            data["description"] = self.description.strip()
        if metadata:
            data["metadata"] = metadata

        idempotency_key = self.idempotency_key.strip() or generate_idempotency_key()
        response_json, status, error = post("charges", self.api_key, data, idempotency_key)
        return build_result(response_json, status, error)
