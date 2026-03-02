"""Cancel a Stripe subscription."""
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import request_form
from connector_stripe.stripe_client import resolve_idempotency_key
from connector_stripe.validation import ValidationError
from connector_stripe.validation import ensure_idempotency_key_length
from connector_stripe.validation import parse_bool
from connector_stripe.validation import require_non_empty
from connector_stripe.validation import to_form_payload


class CancelSubscription(ConnectorCommand):
    """Cancel a Stripe subscription by ID."""

    def __init__(
        self,
        api_key: str,
        subscription_id: str,
        invoice_now: str = "false",
        prorate: str = "true",
        idempotency_key: str = "",
    ):
        self.api_key = api_key
        self.subscription_id = subscription_id
        self.invoice_now = invoice_now or "false"
        self.prorate = prorate or "true"
        self.idempotency_key = idempotency_key or ""

    def execute(self, _config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_key = require_non_empty("api_key", self.api_key)
            subscription_id = require_non_empty("subscription_id", self.subscription_id)
            idempotency_key = ensure_idempotency_key_length(self.idempotency_key)

            payload: dict[str, Any] = {
                "invoice_now": parse_bool(self.invoice_now, default=False),
                "prorate": parse_bool(self.prorate, default=True),
            }
            final_idempotency_key = resolve_idempotency_key(
                idempotency_key,
                "cancel_subscription",
                {"subscription_id": subscription_id, **payload},
                task_data,
            )
            form_data = to_form_payload(payload)
            data, status, err = request_form(
                "DELETE",
                f"subscriptions/{subscription_id}",
                api_key,
                form_data=form_data,
                idempotency_key=final_idempotency_key,
            )
            return build_result(data or {}, status, err)
        except ValidationError as exc:
            return error_response(400, "StripeValidationError", str(exc))
        except Exception as exc:
            return error_response(500, "StripeApiError", f"{exc.__class__.__name__}: {exc}")
