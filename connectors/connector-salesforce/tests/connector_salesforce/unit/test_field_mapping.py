"""Unit tests for field mapping validation and coercion."""
import pytest
from connector_salesforce.field_mapping import FieldMappingError
from connector_salesforce.field_mapping import prepare_contact_fields_for_update
from connector_salesforce.field_mapping import prepare_lead_fields_for_update
from connector_salesforce.field_mapping import validate_and_prepare_contact_fields
from connector_salesforce.field_mapping import validate_and_prepare_lead_fields


class TestValidateLeadFields:
    def test_valid_minimal_lead(self) -> None:
        out = validate_and_prepare_lead_fields({"LastName": "Doe", "Company": "Acme"})
        assert out["LastName"] == "Doe"
        assert out["Company"] == "Acme"

    def test_lead_missing_required_last_name(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            validate_and_prepare_lead_fields({"Company": "Acme"})
        assert "LastName" in exc_info.value.message or "required" in exc_info.value.message.lower()

    def test_lead_missing_required_company(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            validate_and_prepare_lead_fields({"LastName": "Doe"})
        assert "Company" in exc_info.value.message or "required" in exc_info.value.message.lower()

    def test_lead_invalid_field(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            validate_and_prepare_lead_fields({"LastName": "Doe", "Company": "Acme", "InvalidField": "x"})
        assert "Invalid field" in exc_info.value.message and "Lead" in exc_info.value.message

    def test_lead_number_coercion(self) -> None:
        out = validate_and_prepare_lead_fields({"LastName": "Doe", "Company": "Acme", "NumberOfEmployees": "100"})
        assert out["NumberOfEmployees"] == 100

    def test_lead_boolean_coercion(self) -> None:
        out = validate_and_prepare_lead_fields({"LastName": "Doe", "Company": "Acme"})
        out2 = validate_and_prepare_lead_fields({"LastName": "Doe", "Company": "Acme"})
        assert out == out2


class TestValidateContactFields:
    def test_valid_minimal_contact(self) -> None:
        out = validate_and_prepare_contact_fields({"LastName": "Smith"})
        assert out["LastName"] == "Smith"

    def test_contact_missing_required_last_name(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            validate_and_prepare_contact_fields({})
        assert "LastName" in exc_info.value.message or "required" in exc_info.value.message.lower()

    def test_contact_invalid_field(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            validate_and_prepare_contact_fields({"LastName": "Smith", "BadField": "x"})
        assert "Invalid field" in exc_info.value.message and "Contact" in exc_info.value.message


class TestPrepareLeadForUpdate:
    def test_valid_partial_update(self) -> None:
        out = prepare_lead_fields_for_update({"Status": "Open"})
        assert out["Status"] == "Open"

    def test_invalid_field_on_update(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            prepare_lead_fields_for_update({"UnknownField": "x"})
        assert "Invalid field" in exc_info.value.message


class TestPrepareContactForUpdate:
    def test_valid_partial_update(self) -> None:
        out = prepare_contact_fields_for_update({"Email": "a@b.com"})
        assert out["Email"] == "a@b.com"

    def test_invalid_field_on_update(self) -> None:
        with pytest.raises(FieldMappingError) as exc_info:
            prepare_contact_fields_for_update({"UnknownField": "x"})
        assert "Invalid field" in exc_info.value.message
