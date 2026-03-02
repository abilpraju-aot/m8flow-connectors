"""Issue a Stripe Refund for a charge or payment intent."""
import json
from typing import Any

from connector_stripe.connector_interface import ConnectorCommand
from connector_stripe.connector_interface import ConnectorProxyResponseDict
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import generate_idempotency_key
from connector_stripe.stripe_client import post
from connector_stripe.validation import StripeValidationError
from connector_stripe.validation import validate_optional_stripe_id

VALID_REFUND_REASONS = ("duplicate", "fraudulent", "requested_by_customer")


class IssueRefund(ConnectorCommand):
    """Issue a full or partial refund for a Stripe charge or payment intent."""

    def __init__(
        self,
        api_key: str,
        charge_id: str = "",
        payment_intent_id: str = "",
        amount: str = "",
        reason: str = "",
        metadata: str = "",
        idempotency_key: str = "",
    ):
        """
        :param api_key: Stripe secret API key (sk_test_... or sk_live_...).
        :param charge_id: Stripe charge ID (ch_...) to refund. Either charge_id or payment_intent_id required.
        :param payment_intent_id: Stripe payment intent ID (pi_...) to refund.
        :param amount: Optional amount to refund in smallest currency unit. If empty, full refund.
        :param reason: Optional reason (duplicate, fraudulent, requested_by_customer).
        :param metadata: Optional JSON string of metadata key-value pairs.
        :param idempotency_key: Optional unique key to prevent duplicate operations.
        """
        self.api_key = api_key
        self.charge_id = charge_id
        self.payment_intent_id = payment_intent_id
        self.amount = amount
        self.reason = reason
        self.metadata = metadata
        self.idempotency_key = idempotency_key

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            charge_id = validate_optional_stripe_id(self.charge_id, "ch_", "charge_id")
            payment_intent_id = validate_optional_stripe_id(self.payment_intent_id, "pi_", "payment_intent_id")
        except StripeValidationError as exc:
            return error_response(400, "StripeValidationError", exc.message)

        if not charge_id and not payment_intent_id:
            return error_response(
                400,
                "StripeValidationError",
                "Either charge_id or payment_intent_id is required",
            )

        data: dict[str, Any] = {}

        if charge_id:
            data["charge"] = charge_id
        if payment_intent_id:
            data["payment_intent"] = payment_intent_id

        if self.amount.strip():
            try:
                amount_int = int(self.amount.strip())
                if amount_int <= 0:
                    return error_response(400, "StripeValidationError", f"Refund amount must be positive, got: {amount_int}")
                data["amount"] = amount_int
            except ValueError:
                return error_response(400, "StripeValidationError", f"Refund amount must be a valid integer, got: {self.amount}")

        if self.reason.strip():
            reason = self.reason.strip().lower()
            if reason not in VALID_REFUND_REASONS:
                return error_response(
                    400,
                    "StripeValidationError",
                    f"reason must be one of {VALID_REFUND_REASONS}, got: {reason}",
                )
            data["reason"] = reason

        if self.metadata.strip():
            try:
                metadata = json.loads(self.metadata)
                if not isinstance(metadata, dict):
                    return error_response(400, "StripeValidationError", "metadata must be a JSON object")
                data["metadata"] = metadata
            except (json.JSONDecodeError, TypeError) as exc:
                return error_response(400, "StripeValidationError", f"Invalid JSON for metadata: {exc}")

        idempotency_key = self.idempotency_key.strip() or generate_idempotency_key()
        response_json, status, error = post("refunds", self.api_key, data, idempotency_key)
        return build_result(response_json, status, error)
