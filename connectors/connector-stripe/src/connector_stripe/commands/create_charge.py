"""Create a Stripe Charge."""
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
from connector_stripe.validation import parse_positive_int
from connector_stripe.validation import require_non_empty
from connector_stripe.validation import to_form_payload
from connector_stripe.validation import validate_currency


class CreateCharge(ConnectorCommand):
    """Create a Charge in Stripe."""

    def __init__(
        self,
        api_key: str,
        amount: str,
        currency: str,
        customer_id: str = "",
        payment_method: str = "",
        description: str = "",
        metadata: str = "{}",
        idempotency_key: str = "",
    ):
        self.api_key = api_key
        self.amount = amount
        self.currency = currency
        self.customer_id = customer_id or ""
        self.payment_method = payment_method or ""
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

            payload: dict[str, Any] = {
                "amount": amount,
                "currency": currency,
            }
            customer_id = self.customer_id.strip()
            payment_method = self.payment_method.strip()
            if customer_id:
                payload["customer"] = customer_id
            if payment_method:
                if payment_method.startswith("pm_"):
                    payload["payment_method"] = payment_method
                else:
                    payload["source"] = payment_method
            if self.description.strip():
                payload["description"] = self.description.strip()
            if metadata:
                payload["metadata"] = metadata

            if not customer_id and not payment_method:
                raise ValidationError("Either customer_id or payment_method is required for CreateCharge.")

            final_idempotency_key = resolve_idempotency_key(
                idempotency_key,
                "create_charge",
                payload,
                task_data,
            )
            form_data = to_form_payload(payload)
            data, status, err = request_form(
                "POST",
                "charges",
                api_key,
                form_data=form_data,
                idempotency_key=final_idempotency_key,
            )
            return build_result(data or {}, status, err)
        except ValidationError as exc:
            return error_response(400, "StripeValidationError", str(exc))
        except Exception as exc:
            return error_response(500, "StripeApiError", f"{exc.__class__.__name__}: {exc}")
