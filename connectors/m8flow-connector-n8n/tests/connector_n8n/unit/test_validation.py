"""Unit tests for validation helpers."""
import pytest
from connector_n8n.validation import N8nValidationError
from connector_n8n.validation import normalize_api_base_url
from connector_n8n.validation import normalize_instance_host
from connector_n8n.validation import parse_json_field
from connector_n8n.validation import parse_timeout
from connector_n8n.validation import validate_http_method


class TestValidation:
    def test_normalize_api_base_url(self) -> None:
        assert normalize_api_base_url("https://n8n.example.com") == "https://n8n.example.com/api/v1"
        assert normalize_api_base_url("https://n8n.example.com/api/v1/") == "https://n8n.example.com/api/v1"

    def test_normalize_instance_host(self) -> None:
        assert normalize_instance_host("https://n8n.example.com/") == "https://n8n.example.com"
        assert normalize_instance_host("https://n8n.example.com/api/v1") == "https://n8n.example.com"

    def test_parse_json_field_empty(self) -> None:
        assert parse_json_field("payload", "") == {}

    def test_parse_json_field_invalid(self) -> None:
        with pytest.raises(N8nValidationError):
            parse_json_field("payload", "not-json")

    def test_validate_http_method(self) -> None:
        assert validate_http_method("post") == "POST"

    def test_validate_http_method_invalid(self) -> None:
        with pytest.raises(N8nValidationError):
            validate_http_method("TRACE")

    def test_parse_timeout_default(self) -> None:
        assert parse_timeout("") == 120

    def test_parse_timeout_out_of_range(self) -> None:
        with pytest.raises(N8nValidationError):
            parse_timeout("0")
