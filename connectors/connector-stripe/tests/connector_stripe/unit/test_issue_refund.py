"""Unit tests for IssueRefund command."""
from unittest.mock import patch

from connector_stripe.commands.issue_refund import IssueRefund


class TestIssueRefund:
    def test_full_refund_by_charge_id(self) -> None:
        success_data = {
            "id": "re_123",
            "object": "refund",
            "amount": 1000,
            "status": "succeeded",
            "charge": "ch_abc123",
        }
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = IssueRefund("sk_test_123", charge_id="ch_abc123")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "refunds"
            assert call_args[0][2]["charge"] == "ch_abc123"
            assert "amount" not in call_args[0][2]

    def test_full_refund_by_payment_intent(self) -> None:
        success_data = {"id": "re_123", "object": "refund", "status": "succeeded"}
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = IssueRefund("sk_test_123", payment_intent_id="pi_xyz789")
            response = cmd.execute({}, {})
            assert response["error"] is None
            call_args = mock_post.call_args
            assert call_args[0][2]["payment_intent"] == "pi_xyz789"

    def test_partial_refund(self) -> None:
        success_data = {"id": "re_123", "object": "refund", "amount": 500, "status": "succeeded"}
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", amount="500")
            response = cmd.execute({}, {})
            assert response["error"] is None
            call_args = mock_post.call_args
            assert call_args[0][2]["amount"] == 500

    def test_refund_with_reason(self) -> None:
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = ({"id": "re_123"}, 200, None)
            cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", reason="duplicate")
            cmd.execute({}, {})
            call_args = mock_post.call_args
            assert call_args[0][2]["reason"] == "duplicate"

    def test_refund_with_metadata(self) -> None:
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = ({"id": "re_123"}, 200, None)
            cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", metadata='{"refund_reason": "customer request"}')
            cmd.execute({}, {})
            call_args = mock_post.call_args
            assert call_args[0][2]["metadata"] == {"refund_reason": "customer request"}

    def test_missing_charge_and_payment_intent(self) -> None:
        cmd = IssueRefund("sk_test_123")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "charge_id or payment_intent_id" in response["error"]["message"]

    def test_invalid_charge_id_prefix(self) -> None:
        cmd = IssueRefund("sk_test_123", charge_id="invalid_charge")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "ch_" in response["error"]["message"]

    def test_invalid_payment_intent_prefix(self) -> None:
        cmd = IssueRefund("sk_test_123", payment_intent_id="invalid_pi")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "pi_" in response["error"]["message"]

    def test_invalid_refund_amount(self) -> None:
        cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", amount="not_a_number")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "integer" in response["error"]["message"].lower()

    def test_negative_refund_amount(self) -> None:
        cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", amount="-100")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "positive" in response["error"]["message"].lower()

    def test_invalid_reason(self) -> None:
        cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", reason="invalid_reason")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "reason" in response["error"]["message"]

    def test_invalid_metadata_json(self) -> None:
        cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", metadata="not valid json")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "Invalid JSON" in response["error"]["message"]

    def test_refund_already_refunded(self) -> None:
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = (
                {},
                400,
                {"error_code": "StripeValidationError", "message": "Charge ch_abc123 has already been refunded"},
            )
            cmd = IssueRefund("sk_test_123", charge_id="ch_abc123")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 400
            assert response["error"]["error_code"] == "StripeValidationError"

    def test_idempotency_key_passthrough(self) -> None:
        with patch("connector_stripe.commands.issue_refund.post") as mock_post:
            mock_post.return_value = ({"id": "re_123"}, 200, None)
            cmd = IssueRefund("sk_test_123", charge_id="ch_abc123", idempotency_key="refund-key-123")
            cmd.execute({}, {})
            call_args = mock_post.call_args
            assert call_args[0][3] == "refund-key-123"
