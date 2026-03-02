"""Unit tests for Stripe error handling and client module."""
from unittest.mock import MagicMock
from unittest.mock import patch

from connector_stripe.stripe_client import _flatten_dict
from connector_stripe.stripe_client import _parse_stripe_response
from connector_stripe.stripe_client import _stripe_error_to_connector_error
from connector_stripe.stripe_client import build_result
from connector_stripe.stripe_client import delete
from connector_stripe.stripe_client import error_response
from connector_stripe.stripe_client import generate_idempotency_key
from connector_stripe.stripe_client import post


class TestStripeErrorMapping:
    def test_authentication_error(self) -> None:
        response_json = {
            "error": {
                "type": "authentication_error",
                "message": "Invalid API Key provided",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 401)
        assert status == 401
        assert error["error_code"] == "StripeAuthError"
        assert "authentication" in error["message"].lower()

    def test_card_error_with_decline_code(self) -> None:
        response_json = {
            "error": {
                "type": "card_error",
                "message": "Your card was declined",
                "decline_code": "insufficient_funds",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 402)
        assert status == 402
        assert error["error_code"] == "StripeCardError"
        assert "insufficient_funds" in error["message"]

    def test_card_error_without_decline_code(self) -> None:
        response_json = {
            "error": {
                "type": "card_error",
                "message": "Your card was declined",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 402)
        assert status == 402
        assert error["error_code"] == "StripeCardError"

    def test_invalid_request_error(self) -> None:
        response_json = {
            "error": {
                "type": "invalid_request_error",
                "message": "No such customer: cus_invalid",
                "code": "resource_missing",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 400)
        assert status == 400
        assert error["error_code"] == "StripeValidationError"
        assert "resource_missing" in error["message"]

    def test_rate_limit_error(self) -> None:
        response_json = {
            "error": {
                "type": "rate_limit_error",
                "message": "Too many requests",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 429)
        assert status == 429
        assert error["error_code"] == "StripeRateLimitError"

    def test_api_error(self) -> None:
        response_json = {
            "error": {
                "type": "api_error",
                "message": "Internal server error",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 500)
        assert status == 500
        assert error["error_code"] == "StripeAPIError"

    def test_unknown_error_type(self) -> None:
        response_json = {
            "error": {
                "type": "unknown_type",
                "message": "Something went wrong",
            }
        }
        status, error = _stripe_error_to_connector_error(response_json, 400)
        assert error["error_code"] == "StripeAPIError"


class TestParseStripeResponse:
    def test_success_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"id": "pi_123", "status": "succeeded"}

        data, status, error = _parse_stripe_response(mock_response)
        assert data == {"id": "pi_123", "status": "succeeded"}
        assert status == 200
        assert error is None

    def test_error_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {
            "error": {"type": "invalid_request_error", "message": "Invalid param"}
        }

        data, status, error = _parse_stripe_response(mock_response)
        assert data == {}
        assert status == 400
        assert error is not None
        assert error["error_code"] == "StripeValidationError"

    def test_non_json_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}

        data, status, error = _parse_stripe_response(mock_response)
        assert data == {}
        assert error is not None
        assert error["error_code"] == "StripeAPIError"
        assert "Non-JSON" in error["message"]

    def test_invalid_json_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.side_effect = ValueError("Invalid JSON")

        data, status, error = _parse_stripe_response(mock_response)
        assert data == {}
        assert error is not None
        assert "Invalid JSON" in error["message"]


class TestPost:
    def test_successful_post(self) -> None:
        with patch("connector_stripe.stripe_client.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = {"id": "pi_123"}
            mock_post.return_value = mock_response

            data, status, error = post("payment_intents", "sk_test_123", {"amount": 1000})
            assert data == {"id": "pi_123"}
            assert status == 200
            assert error is None

            call_args = mock_post.call_args
            assert "Bearer sk_test_123" in call_args[1]["headers"]["Authorization"]

    def test_post_with_idempotency_key(self) -> None:
        with patch("connector_stripe.stripe_client.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = {"id": "pi_123"}
            mock_post.return_value = mock_response

            post("payment_intents", "sk_test_123", {"amount": 1000}, idempotency_key="idem-123")

            call_args = mock_post.call_args
            assert call_args[1]["headers"]["Idempotency-Key"] == "idem-123"

    def test_timeout_error(self) -> None:
        with patch("connector_stripe.stripe_client.requests.post") as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.Timeout()

            data, status, error = post("payment_intents", "sk_test_123", {"amount": 1000})
            assert data == {}
            assert status == 504
            assert error["error_code"] == "StripeTimeout"

    def test_connection_error(self) -> None:
        with patch("connector_stripe.stripe_client.requests.post") as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.ConnectionError()

            data, status, error = post("payment_intents", "sk_test_123", {"amount": 1000})
            assert data == {}
            assert status == 503
            assert error["error_code"] == "StripeConnectionError"


class TestDelete:
    def test_successful_delete(self) -> None:
        with patch("connector_stripe.stripe_client.requests.delete") as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "application/json"}
            mock_response.json.return_value = {"id": "sub_123", "status": "canceled"}
            mock_delete.return_value = mock_response

            data, status, error = delete("subscriptions/sub_123", "sk_test_123")
            assert data == {"id": "sub_123", "status": "canceled"}
            assert status == 200
            assert error is None


class TestFlattenDict:
    def test_simple_dict(self) -> None:
        result = _flatten_dict({"amount": 1000, "currency": "usd"})
        assert result == {"amount": 1000, "currency": "usd"}

    def test_nested_dict(self) -> None:
        result = _flatten_dict({"metadata": {"order_id": "123", "user": "abc"}})
        assert result == {"metadata[order_id]": "123", "metadata[user]": "abc"}

    def test_nested_list(self) -> None:
        result = _flatten_dict({"items": [{"price": "price_123"}]})
        assert result == {"items[0][price]": "price_123"}


class TestHelperFunctions:
    def test_generate_idempotency_key(self) -> None:
        key1 = generate_idempotency_key()
        key2 = generate_idempotency_key()
        assert len(key1) == 36
        assert key1 != key2

    def test_error_response(self) -> None:
        result = error_response(400, "TestError", "Test message")
        assert result["command_response"]["http_status"] == 400
        assert result["error"]["error_code"] == "TestError"
        assert result["error"]["message"] == "Test message"
        assert result["command_response_version"] == 2

    def test_build_result_success(self) -> None:
        result = build_result({"id": "pi_123"}, 200, None)
        assert result["command_response"]["http_status"] == 200
        assert '"id": "pi_123"' in result["command_response"]["body"]
        assert result["error"] is None
        assert result["command_response_version"] == 2

    def test_build_result_error(self) -> None:
        error = {"error_code": "StripeCardError", "message": "Card declined"}
        result = build_result({}, 402, error)
        assert result["command_response"]["http_status"] == 402
        assert result["error"] == error
