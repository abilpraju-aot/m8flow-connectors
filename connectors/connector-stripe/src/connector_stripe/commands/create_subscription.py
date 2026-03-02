"""Create a Stripe Subscription."""
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import request_form
from connector_stripe.stripe_client import resolve_idempotency_key
from connector_stripe.validation import ValidationError
from connector_stripe.validation import ensure_idempotency_key_length
from connector_stripe.validation import parse_metadata_json
from connector_stripe.validation import parse_optional_positive_int
from connector_stripe.validation import parse_positive_int
from connector_stripe.validation import require_non_empty
from connector_stripe.validation import to_form_payload


class CreateSubscription(ConnectorCommand):
    """Create a Stripe subscription for a customer and price."""

    def __init__(
        self,
        api_key: str,
        customer_id: str,
        price_id: str,
        quantity: str = "1",
        payment_method: str = "",
        trial_period_days: str = "",
        metadata: str = "{}",
        idempotency_key: str = "",
    ):
        self.api_key = api_key
        self.customer_id = customer_id
        self.price_id = price_id
        self.quantity = quantity or "1"
        self.payment_method = payment_method or ""
        self.trial_period_days = trial_period_days or ""
        self.metadata = metadata or "{}"
        self.idempotency_key = idempotency_key or ""

    def execute(self, _config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_key = require_non_empty("api_key", self.api_key)
            customer_id = require_non_empty("customer_id", self.customer_id)
            price_id = require_non_empty("price_id", self.price_id)
            quantity = parse_positive_int("quantity", self.quantity)
            trial_period_days = parse_optional_positive_int("trial_period_days", self.trial_period_days)
            metadata = parse_metadata_json(self.metadata)
            idempotency_key = ensure_idempotency_key_length(self.idempotency_key)

            payload: dict[str, Any] = {
                "customer": customer_id,
                "items": [{"price": price_id, "quantity": quantity}],
            }
            if self.payment_method.strip():
                payload["default_payment_method"] = self.payment_method.strip()
            if trial_period_days is not None:
                payload["trial_period_days"] = trial_period_days
            if metadata:
                payload["metadata"] = metadata

            final_idempotency_key = resolve_idempotency_key(
                idempotency_key,
                "create_subscription",
                payload,
                task_data,
            )
            form_data = to_form_payload(payload)
            data, status, err = request_form(
                "POST",
                "subscriptions",
                api_key,
                form_data=form_data,
                idempotency_key=final_idempotency_key,
            )
            return build_result(data or {}, status, err)
        except ValidationError as exc:
            return error_response(400, "StripeValidationError", str(exc))
        except Exception as exc:
            return error_response(500, "StripeApiError", f"{exc.__class__.__name__}: {exc}")
