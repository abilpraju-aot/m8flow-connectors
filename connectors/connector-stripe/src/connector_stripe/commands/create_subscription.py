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
    """Create a Stripe Subscription for recurring billing.

    Supports two payment flows:
    - Pass a pre-existing ``default_payment_method`` (pm_xxx), OR
    - Provide a ``card_token`` (e.g. tok_visa) which will create and attach
      a PaymentMethod automatically.
    """

    def __init__(
        self,
        api_key: str,
        customer_id: str,
        price_id: str,
        payment_behavior: str = "default_incomplete",
        default_payment_method: str = "",
        metadata: str = "",
        idempotency_key: str = "",
        card_token: str = "",
    ):
        self.api_key = api_key
        self.customer_id = customer_id
        self.price_id = price_id
        self.payment_behavior = payment_behavior
        self.default_payment_method = default_payment_method
        self.metadata = metadata
        self.idempotency_key = idempotency_key
        self.card_token = card_token

    def _create_and_attach_payment_method(self, customer_id: str) -> tuple[str | None, ConnectorProxyResponseDict | None]:
        """Create a PaymentMethod from a card token and attach it to the customer.

        Returns (pm_id, None) on success or (None, error_response) on failure.
        """
        pm_data: dict[str, Any] = {
            "type": "card",
            "card[token]": self.card_token.strip(),
        }
        pm_json, pm_status, pm_error = post("payment_methods", self.api_key, pm_data)
        if pm_error:
            return None, build_result(pm_json, pm_status, pm_error)

        pm_id = pm_json.get("id", "")
        if not pm_id:
            return None, error_response(500, "StripeAPIError", "PaymentMethod created but no id returned")

        attach_data: dict[str, Any] = {"customer": customer_id}
        attach_json, attach_status, attach_error = post(f"payment_methods/{pm_id}/attach", self.api_key, attach_data)
        if attach_error:
            return None, build_result(attach_json, attach_status, attach_error)

        return pm_id, None

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

        payment_method_id = self.default_payment_method.strip()

        if self.card_token.strip():
            pm_id, err_response = self._create_and_attach_payment_method(customer_id)
            if err_response:
                return err_response
            payment_method_id = pm_id  # type: ignore[assignment]

        data: dict[str, Any] = {
            "customer": customer_id,
            "items[0][price]": price_id,
            "payment_behavior": payment_behavior,
        }

        if payment_method_id:
            data["default_payment_method"] = payment_method_id
        if metadata:
            data["metadata"] = metadata

        idempotency_key = self.idempotency_key.strip() or generate_idempotency_key()
        response_json, status, error = post("subscriptions", self.api_key, data, idempotency_key)
        return build_result(response_json, status, error)
