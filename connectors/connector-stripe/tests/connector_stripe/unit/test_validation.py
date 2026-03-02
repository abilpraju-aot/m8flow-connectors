"""Unit tests for validation.py functions."""
import pytest

from connector_stripe.validation import (
    VALID_REFUND_REASONS,
    ValidationError,
    ensure_idempotency_key_length,
    parse_bool,
    parse_metadata_json,
    parse_optional_positive_int,
    parse_positive_int,
    parse_refund_reference,
    require_non_empty,
    to_form_payload,
    validate_currency,
    validate_refund_reason,
)


class TestRequireNonEmpty:
    def test_valid_string(self) -> None:
        assert require_non_empty("field", "value") == "value"

    def test_strips_whitespace(self) -> None:
        assert require_non_empty("field", "  value  ") == "value"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValidationError, match="field is required"):
            require_non_empty("field", "")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValidationError, match="field is required"):
            require_non_empty("field", "   ")

    def test_none_raises(self) -> None:
        with pytest.raises(ValidationError, match="field is required"):
            require_non_empty("field", None)  # type: ignore


class TestParsePositiveInt:
    def test_valid_integer_string(self) -> None:
        assert parse_positive_int("amount", "1000") == 1000

    def test_strips_whitespace(self) -> None:
        assert parse_positive_int("amount", "  500  ") == 500

    def test_zero_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be greater than 0"):
            parse_positive_int("amount", "0")

    def test_negative_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be greater than 0"):
            parse_positive_int("amount", "-100")

    def test_non_integer_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            parse_positive_int("amount", "abc")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError, match="is required"):
            parse_positive_int("amount", "")

    def test_float_string_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            parse_positive_int("amount", "10.5")


class TestParseOptionalPositiveInt:
    def test_valid_integer(self) -> None:
        assert parse_optional_positive_int("days", "30") == 30

    def test_empty_returns_none(self) -> None:
        assert parse_optional_positive_int("days", "") is None

    def test_whitespace_returns_none(self) -> None:
        assert parse_optional_positive_int("days", "   ") is None

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            parse_optional_positive_int("days", "abc")


class TestValidateCurrency:
    def test_valid_lowercase(self) -> None:
        assert validate_currency("usd") == "usd"

    def test_valid_uppercase_normalized(self) -> None:
        assert validate_currency("USD") == "usd"

    def test_valid_mixed_case(self) -> None:
        assert validate_currency("Eur") == "eur"

    def test_strips_whitespace(self) -> None:
        assert validate_currency("  gbp  ") == "gbp"

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValidationError, match="3-letter ISO code"):
            validate_currency("us")

    def test_too_long_raises(self) -> None:
        with pytest.raises(ValidationError, match="3-letter ISO code"):
            validate_currency("usdd")

    def test_non_alpha_raises(self) -> None:
        with pytest.raises(ValidationError, match="3-letter ISO code"):
            validate_currency("us1")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError, match="currency is required"):
            validate_currency("")


class TestParseBool:
    def test_true_values(self) -> None:
        for val in ("true", "True", "TRUE", "1", "yes", "Yes", "y", "Y"):
            assert parse_bool(val) is True

    def test_false_values(self) -> None:
        for val in ("false", "False", "FALSE", "0", "no", "No", "n", "N"):
            assert parse_bool(val) is False

    def test_empty_returns_default_false(self) -> None:
        assert parse_bool("") is False

    def test_empty_returns_default_true(self) -> None:
        assert parse_bool("", default=True) is True

    def test_invalid_returns_default(self) -> None:
        assert parse_bool("maybe", default=False) is False
        assert parse_bool("maybe", default=True) is True


class TestParseMetadataJson:
    def test_valid_json_object(self) -> None:
        result = parse_metadata_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_empty_string_returns_empty_dict(self) -> None:
        assert parse_metadata_json("") == {}

    def test_whitespace_returns_empty_dict(self) -> None:
        assert parse_metadata_json("   ") == {}

    def test_values_converted_to_string(self) -> None:
        result = parse_metadata_json('{"num": 123, "bool": true}')
        assert result == {"num": "123", "bool": "True"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid metadata JSON"):
            parse_metadata_json("{invalid}")

    def test_non_object_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be a JSON object"):
            parse_metadata_json('["array"]')

    def test_max_50_pairs_exceeded_raises(self) -> None:
        data = {f"key{i}": f"value{i}" for i in range(51)}
        import json
        with pytest.raises(ValidationError, match="more than 50 key-value pairs"):
            parse_metadata_json(json.dumps(data))

    def test_key_too_long_raises(self) -> None:
        long_key = "k" * 41
        with pytest.raises(ValidationError, match="exceeds 40 characters"):
            parse_metadata_json(f'{{"{long_key}": "value"}}')

    def test_value_too_long_raises(self) -> None:
        long_value = "v" * 501
        with pytest.raises(ValidationError, match="exceeds 500 characters"):
            parse_metadata_json(f'{{"key": "{long_value}"}}')

    def test_exactly_50_pairs_allowed(self) -> None:
        data = {f"key{i}": f"value{i}" for i in range(50)}
        import json
        result = parse_metadata_json(json.dumps(data))
        assert len(result) == 50

    def test_key_exactly_40_chars_allowed(self) -> None:
        key = "k" * 40
        result = parse_metadata_json(f'{{"{key}": "value"}}')
        assert key in result

    def test_value_exactly_500_chars_allowed(self) -> None:
        value = "v" * 500
        result = parse_metadata_json(f'{{"key": "{value}"}}')
        assert result["key"] == value


class TestValidateRefundReason:
    def test_valid_reasons(self) -> None:
        for reason in VALID_REFUND_REASONS:
            assert validate_refund_reason(reason) == reason

    def test_empty_returns_none(self) -> None:
        assert validate_refund_reason("") is None

    def test_whitespace_returns_none(self) -> None:
        assert validate_refund_reason("   ") is None

    def test_invalid_reason_raises(self) -> None:
        with pytest.raises(ValidationError, match="Invalid refund reason"):
            validate_refund_reason("invalid_reason")

    def test_strips_whitespace(self) -> None:
        assert validate_refund_reason("  duplicate  ") == "duplicate"


class TestParseRefundReference:
    def test_charge_id_only(self) -> None:
        charge, pi = parse_refund_reference("ch_123", "")
        assert charge == "ch_123"
        assert pi is None

    def test_payment_intent_only(self) -> None:
        charge, pi = parse_refund_reference("", "pi_123")
        assert charge is None
        assert pi == "pi_123"

    def test_both_provided_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            parse_refund_reference("ch_123", "pi_123")

    def test_neither_provided_raises(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            parse_refund_reference("", "")

    def test_strips_whitespace(self) -> None:
        charge, pi = parse_refund_reference("  ch_123  ", "")
        assert charge == "ch_123"


class TestEnsureIdempotencyKeyLength:
    def test_valid_key(self) -> None:
        assert ensure_idempotency_key_length("my-key") == "my-key"

    def test_empty_returns_empty(self) -> None:
        assert ensure_idempotency_key_length("") == ""

    def test_strips_whitespace(self) -> None:
        assert ensure_idempotency_key_length("  key  ") == "key"

    def test_exactly_255_chars_allowed(self) -> None:
        key = "k" * 255
        assert ensure_idempotency_key_length(key) == key

    def test_256_chars_raises(self) -> None:
        key = "k" * 256
        with pytest.raises(ValidationError, match="255 characters or fewer"):
            ensure_idempotency_key_length(key)


class TestToFormPayload:
    def test_simple_dict(self) -> None:
        result = to_form_payload({"amount": 1000, "currency": "usd"})
        assert result == {"amount": "1000", "currency": "usd"}

    def test_nested_dict(self) -> None:
        result = to_form_payload({"metadata": {"key": "value"}})
        assert result == {"metadata[key]": "value"}

    def test_list_of_dicts(self) -> None:
        result = to_form_payload({"items": [{"price": "price_123", "quantity": 1}]})
        assert result == {"items[0][price]": "price_123", "items[0][quantity]": "1"}

    def test_boolean_values(self) -> None:
        result = to_form_payload({"confirm": True, "prorate": False})
        assert result == {"confirm": "true", "prorate": "false"}

    def test_none_values_skipped(self) -> None:
        result = to_form_payload({"amount": 1000, "description": None})
        assert result == {"amount": "1000"}

    def test_empty_dict(self) -> None:
        assert to_form_payload({}) == {}
