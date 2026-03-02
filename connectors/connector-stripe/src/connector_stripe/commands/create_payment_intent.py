"""Create a Stripe PaymentIntent."""
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
from connector_stripe.validation import parse_metadata_json
from connector_stripe.validation import parse_positive_int
from connector_stripe.validation import require_non_empty
from connector_stripe.validation import to_form_payload
from connector_stripe.validation import validate_currency


class CreatePaymentIntent(ConnectorCommand):
    """Create a PaymentIntent in Stripe."""

    def __init__(
        self,
        api_key: str,
        amount: str,
        currency: str,
        customer_id: str = "",
        payment_method: str = "",
        confirm: str = "false",
        description: str = "",
        metadata: str = "{}",
        idempotency_key: str = "",
    ):
        self.api_key = api_key
        self.amount = amount
        self.currency = currency
        self.customer_id = customer_id or ""
        self.payment_method = payment_method or ""
        self.confirm = confirm or "false"
        self.description = description or ""
        self.metadata = metadata or "{}"
        self.idempotency_key = idempotency_key or ""

    def execute(self, _config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_key = require_non_empty("api_key", self.api_key)
            amount = parse_positive_int("amount", self.amount)
            currency = validate_currency(self.currency)
            metadata = parse_metadata_json(self.metadata)
            idempotency_key = ensure_idempotency_key_length(self.idempotency_key)
            confirm = parse_bool(self.confirm, default=False)

            payload: dict[str, Any] = {
                "amount": amount,
                "currency": currency,
                "confirm": confirm,
            }
            if self.customer_id.strip():
                payload["customer"] = self.customer_id.strip()
            if self.payment_method.strip():
                payload["payment_method"] = self.payment_method.strip()
            if self.description.strip():
                payload["description"] = self.description.strip()
            if metadata:
                payload["metadata"] = metadata

            final_idempotency_key = resolve_idempotency_key(
                idempotency_key,
                "create_payment_intent",
                payload,
                task_data,
            )
            form_data = to_form_payload(payload)
            data, status, err = request_form(
                "POST",
                "payment_intents",
                api_key,
                form_data=form_data,
                idempotency_key=final_idempotency_key,
            )
            return build_result(data or {}, status, err)
        except ValidationError as exc:
            return error_response(400, "StripeValidationError", str(exc))
        except Exception as exc:
            return error_response(500, "StripeApiError", f"{exc.__class__.__name__}: {exc}")
