"""Issue a Stripe refund (full or partial)."""
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
from connector_stripe.validation import parse_refund_reference
from connector_stripe.validation import require_non_empty
from connector_stripe.validation import to_form_payload
from connector_stripe.validation import validate_refund_reason


class IssueRefund(ConnectorCommand):
    """Issue a Stripe refund using charge or payment intent reference."""

    def __init__(
        self,
        api_key: str,
        charge_id: str = "",
        payment_intent_id: str = "",
        amount: str = "",
        reason: str = "",
        metadata: str = "{}",
        idempotency_key: str = "",
    ):
        self.api_key = api_key
        self.charge_id = charge_id or ""
        self.payment_intent_id = payment_intent_id or ""
        self.amount = amount or ""
        self.reason = reason or ""
        self.metadata = metadata or "{}"
        self.idempotency_key = idempotency_key or ""

    def execute(self, _config: Any, task_data: Any) -> ConnectorProxyResponseDict:
        try:
            api_key = require_non_empty("api_key", self.api_key)
            charge_id, payment_intent_id = parse_refund_reference(self.charge_id, self.payment_intent_id)
            amount = parse_optional_positive_int("amount", self.amount)
            metadata = parse_metadata_json(self.metadata)
            idempotency_key = ensure_idempotency_key_length(self.idempotency_key)

            payload: dict[str, Any] = {}
            if charge_id:
                payload["charge"] = charge_id
            if payment_intent_id:
                payload["payment_intent"] = payment_intent_id
            if amount is not None:
                payload["amount"] = amount
            reason = validate_refund_reason(self.reason)
            if reason:
                payload["reason"] = reason
            if metadata:
                payload["metadata"] = metadata

            final_idempotency_key = resolve_idempotency_key(
                idempotency_key,
                "issue_refund",
                payload,
                task_data,
            )
            form_data = to_form_payload(payload)
            data, status, err = request_form(
                "POST",
                "refunds",
                api_key,
                form_data=form_data,
                idempotency_key=final_idempotency_key,
            )
            return build_result(data or {}, status, err)
        except ValidationError as exc:
            return error_response(400, "StripeValidationError", str(exc))
        except Exception as exc:
            return error_response(500, "StripeApiError", f"{exc.__class__.__name__}: {exc}")
