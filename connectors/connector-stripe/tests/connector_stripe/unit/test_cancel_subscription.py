"""Unit tests for CancelSubscription command."""
from unittest.mock import patch

from connector_stripe.commands.cancel_subscription import CancelSubscription


class TestCancelSubscription:
    def test_successful_cancel_subscription(self) -> None:
        with patch("connector_stripe.commands.cancel_subscription.request_form") as mock_req:
            mock_req.return_value = ({"id": "sub_123", "status": "canceled"}, 200, None)
            cmd = CancelSubscription("sk_test_123", "sub_123")
            response = cmd.execute({}, {"task_id": "task-can", "execution_id": "exec-1"})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            assert mock_req.call_args[0][0] == "DELETE"
            assert "subscriptions/sub_123" in mock_req.call_args[0][1]
            assert mock_req.call_args[1]["idempotency_key"].startswith("m8stripe_cancel_subscription_")

    def test_missing_subscription_id(self) -> None:
        cmd = CancelSubscription("sk_test_123", "")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
