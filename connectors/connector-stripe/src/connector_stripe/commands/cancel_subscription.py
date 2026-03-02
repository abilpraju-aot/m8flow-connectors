"""Cancel a Stripe Subscription."""
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import delete
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import generate_idempotency_key
from connector_stripe.stripe_client import post
from connector_stripe.validation import StripeValidationError
from connector_stripe.validation import validate_boolean_string
from connector_stripe.validation import validate_stripe_id


class CancelSubscription(ConnectorCommand):
    """Cancel a Stripe Subscription immediately or at period end."""

    def __init__(
        self,
        api_key: str,
        subscription_id: str,
        cancel_at_period_end: str = "false",
        idempotency_key: str = "",
    ):
        """
        :param api_key: Stripe secret API key (sk_test_... or sk_live_...).
        :param subscription_id: Stripe subscription ID (sub_...) to cancel.
        :param cancel_at_period_end: If true, cancel at end of billing period; if false, cancel immediately.
        :param idempotency_key: Optional unique key to prevent duplicate operations.
        """
        self.api_key = api_key
        self.subscription_id = subscription_id
        self.cancel_at_period_end = cancel_at_period_end
        self.idempotency_key = idempotency_key

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            subscription_id = validate_stripe_id(self.subscription_id, "sub_", "subscription_id")
        except StripeValidationError as exc:
            return error_response(400, "StripeValidationError", exc.message)

        cancel_at_period_end = validate_boolean_string(self.cancel_at_period_end, default=False)
        idempotency_key = self.idempotency_key.strip() or generate_idempotency_key()

        if cancel_at_period_end:
            data = {"cancel_at_period_end": "true"}
            response_json, status, error = post(
                f"subscriptions/{subscription_id}",
                self.api_key,
                data,
                idempotency_key,
            )
        else:
            response_json, status, error = delete(
                f"subscriptions/{subscription_id}",
                self.api_key,
            )

        return build_result(response_json, status, error)
