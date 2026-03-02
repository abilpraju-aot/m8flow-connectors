"""Unit tests for validation module."""
import pytest
from connector_stripe.validation import StripeValidationError
from connector_stripe.validation import validate_amount
from connector_stripe.validation import validate_boolean_string
from connector_stripe.validation import validate_currency
from connector_stripe.validation import validate_optional_json
from connector_stripe.validation import validate_optional_stripe_id
from connector_stripe.validation import validate_required
from connector_stripe.validation import validate_stripe_id


class TestValidateAmount:
    def test_valid_amount(self) -> None:
        assert validate_amount("1000") == 1000
        assert validate_amount("  500  ") == 500
        assert validate_amount("1") == 1

    def test_empty_amount(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_amount("")
        assert "required" in exc_info.value.message.lower()

    def test_non_integer_amount(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_amount("10.50")
        assert "valid integer" in exc_info.value.message.lower()

    def test_negative_amount(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_amount("-100")
        assert "positive" in exc_info.value.message.lower()

    def test_zero_amount(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_amount("0")
        assert "positive" in exc_info.value.message.lower()


class TestValidateCurrency:
    def test_valid_currency(self) -> None:
        assert validate_currency("usd") == "usd"
        assert validate_currency("USD") == "usd"
        assert validate_currency("  eur  ") == "eur"
        assert validate_currency("GBP") == "gbp"

    def test_empty_currency(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_currency("")
        assert "required" in exc_info.value.message.lower()

    def test_invalid_currency_length(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_currency("us")
        assert "3-letter" in exc_info.value.message

        with pytest.raises(StripeValidationError) as exc_info:
            validate_currency("usdd")
        assert "3-letter" in exc_info.value.message


class TestValidateRequired:
    def test_valid_value(self) -> None:
        assert validate_required("value", "field") == "value"
        assert validate_required("  trimmed  ", "field") == "trimmed"

    def test_empty_value(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_required("", "my_field")
        assert "my_field" in exc_info.value.message
        assert "required" in exc_info.value.message.lower()


class TestValidateOptionalJson:
    def test_empty_returns_none(self) -> None:
        assert validate_optional_json("", "field") is None
        assert validate_optional_json("  ", "field") is None

    def test_valid_json_object(self) -> None:
        result = validate_optional_json('{"key": "value"}', "field")
        assert result == {"key": "value"}

    def test_invalid_json(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_optional_json("not json", "metadata")
        assert "Invalid JSON" in exc_info.value.message
        assert "metadata" in exc_info.value.message

    def test_json_array_rejected(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_optional_json("[1, 2, 3]", "metadata")
        assert "JSON object" in exc_info.value.message


class TestValidateBooleanString:
    def test_true_values(self) -> None:
        assert validate_boolean_string("true") is True
        assert validate_boolean_string("TRUE") is True
        assert validate_boolean_string("1") is True
        assert validate_boolean_string("yes") is True
        assert validate_boolean_string("YES") is True

    def test_false_values(self) -> None:
        assert validate_boolean_string("false") is False
        assert validate_boolean_string("FALSE") is False
        assert validate_boolean_string("0") is False
        assert validate_boolean_string("no") is False
        assert validate_boolean_string("NO") is False

    def test_empty_returns_default(self) -> None:
        assert validate_boolean_string("") is False
        assert validate_boolean_string("", default=True) is True

    def test_invalid_returns_default(self) -> None:
        assert validate_boolean_string("invalid") is False
        assert validate_boolean_string("invalid", default=True) is True


class TestValidateStripeId:
    def test_valid_id(self) -> None:
        assert validate_stripe_id("cus_abc123", "cus_", "customer_id") == "cus_abc123"
        assert validate_stripe_id("  sub_xyz789  ", "sub_", "subscription_id") == "sub_xyz789"

    def test_empty_id(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_stripe_id("", "cus_", "customer_id")
        assert "required" in exc_info.value.message.lower()

    def test_wrong_prefix(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_stripe_id("sub_123", "cus_", "customer_id")
        assert "cus_" in exc_info.value.message


class TestValidateOptionalStripeId:
    def test_empty_returns_none(self) -> None:
        assert validate_optional_stripe_id("", "cus_", "customer_id") is None
        assert validate_optional_stripe_id("  ", "cus_", "customer_id") is None

    def test_valid_id(self) -> None:
        assert validate_optional_stripe_id("cus_abc123", "cus_", "customer_id") == "cus_abc123"

    def test_wrong_prefix(self) -> None:
        with pytest.raises(StripeValidationError) as exc_info:
            validate_optional_stripe_id("invalid_123", "cus_", "customer_id")
        assert "cus_" in exc_info.value.message
