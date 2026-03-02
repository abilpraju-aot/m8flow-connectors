"""Unit tests for CancelSubscription command."""
from unittest.mock import patch

from connector_stripe.commands.cancel_subscription import CancelSubscription


class TestCancelSubscription:
    def test_immediate_cancel(self) -> None:
        success_data = {
            "id": "sub_123",
            "object": "subscription",
            "status": "canceled",
        }
        with patch("connector_stripe.commands.cancel_subscription.delete") as mock_delete:
            mock_delete.return_value = (success_data, 200, None)
            cmd = CancelSubscription("sk_test_123", "sub_123abc")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_delete.assert_called_once()
            call_args = mock_delete.call_args
            assert call_args[0][0] == "subscriptions/sub_123abc"

    def test_cancel_at_period_end(self) -> None:
        success_data = {
            "id": "sub_123",
            "object": "subscription",
            "status": "active",
            "cancel_at_period_end": True,
        }
        with patch("connector_stripe.commands.cancel_subscription.post") as mock_post:
            mock_post.return_value = (success_data, 200, None)
            cmd = CancelSubscription("sk_test_123", "sub_123abc", cancel_at_period_end="true")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 200
            assert response["error"] is None
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "subscriptions/sub_123abc"
            assert call_args[0][2]["cancel_at_period_end"] == "true"

    def test_invalid_subscription_id(self) -> None:
        cmd = CancelSubscription("sk_test_123", "invalid_sub_id")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"
        assert "sub_" in response["error"]["message"]

    def test_missing_subscription_id(self) -> None:
        cmd = CancelSubscription("sk_test_123", "")
        response = cmd.execute({}, {})
        assert response["command_response"]["http_status"] == 400
        assert response["error"]["error_code"] == "StripeValidationError"

    def test_subscription_not_found(self) -> None:
        with patch("connector_stripe.commands.cancel_subscription.delete") as mock_delete:
            mock_delete.return_value = (
                {},
                404,
                {"error_code": "StripeValidationError", "message": "No such subscription: sub_notfound"},
            )
            cmd = CancelSubscription("sk_test_123", "sub_notfound")
            response = cmd.execute({}, {})
            assert response["command_response"]["http_status"] == 404
            assert response["error"]["error_code"] == "StripeValidationError"

    def test_idempotency_key_used_for_period_end_cancel(self) -> None:
        with patch("connector_stripe.commands.cancel_subscription.post") as mock_post:
            mock_post.return_value = ({"id": "sub_123"}, 200, None)
            cmd = CancelSubscription("sk_test_123", "sub_123abc", cancel_at_period_end="true", idempotency_key="cancel-key-123")
            cmd.execute({}, {})
            call_args = mock_post.call_args
            assert call_args[0][3] == "cancel-key-123"

    def test_boolean_string_parsing(self) -> None:
        with patch("connector_stripe.commands.cancel_subscription.post") as mock_post:
            mock_post.return_value = ({"id": "sub_123"}, 200, None)
            cmd = CancelSubscription("sk_test_123", "sub_123abc", cancel_at_period_end="yes")
            cmd.execute({}, {})
            mock_post.assert_called_once()

        with patch("connector_stripe.commands.cancel_subscription.delete") as mock_delete:
            mock_delete.return_value = ({"id": "sub_123"}, 200, None)
            cmd = CancelSubscription("sk_test_123", "sub_123abc", cancel_at_period_end="no")
            cmd.execute({}, {})
            mock_delete.assert_called_once()
