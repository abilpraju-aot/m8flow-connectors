"""Field validation and type coercion for Lead and Contact. Supports string, number, boolean, date (ISO)."""
from datetime import datetime
from typing import Any

# Required and allowed optional fields per object. Unknown fields raise with clear message.
LEAD_REQUIRED = frozenset({"LastName", "Company"})
LEAD_OPTIONAL = frozenset({
    "FirstName", "Title", "Email", "Phone", "MobilePhone", "Street", "City", "State", "PostalCode", "Country",
    "Description", "LeadSource", "Status", "Rating", "Website", "NumberOfEmployees", "Industry", "AnnualRevenue",
})
CONTACT_REQUIRED = frozenset({"LastName"})
CONTACT_OPTIONAL = frozenset({
    "AccountId", "FirstName", "Title", "Email", "Phone", "MobilePhone", "MailingStreet", "MailingCity",
    "MailingState", "MailingPostalCode", "MailingCountry", "Description", "LeadSource", "Department",
})


class FieldMappingError(Exception):
    """Raised when field validation or coercion fails. message is safe for workflow logs."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _coerce_value(field_name: str, value: Any, expected: str) -> Any:
    """Coerce value to string, number, boolean, or date (ISO). Raises FieldMappingError on failure."""
    if value is None:
        return None
    if expected == "string":
        return str(value).strip() if isinstance(value, str) else str(value)
    if expected == "number":
        if isinstance(value, int | float):
            return value
        try:
            s = str(value).strip()
            if "." in s or "e" in s.lower():
                return float(s)
            return int(s)
        except (ValueError, TypeError) as e:
            raise FieldMappingError(f"Field '{field_name}' must be a number.") from e
    if expected == "boolean":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("true", "1", "yes"):
            return True
        if s in ("false", "0", "no", ""):
            return False
        raise FieldMappingError(f"Field '{field_name}' must be a boolean (true/false).") from None
    if expected == "date":
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        s = str(value).strip()
        if not s:
            return None
        try:
            datetime.fromisoformat(s.replace("Z", "+00:00")[:10])
            return s[:10]
        except (ValueError, TypeError):
            pass
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
        raise FieldMappingError(f"Field '{field_name}' must be a date (YYYY-MM-DD).") from None
    return value


# Simple type hints for common fields: field_name -> "string" | "number" | "boolean" | "date"
LEAD_FIELD_TYPES: dict[str, str] = {
    "LastName": "string", "Company": "string", "FirstName": "string", "Title": "string", "Email": "string",
    "Phone": "string", "MobilePhone": "string", "Street": "string", "City": "string", "State": "string",
    "PostalCode": "string", "Country": "string", "Description": "string", "LeadSource": "string", "Status": "string",
    "Rating": "string", "Website": "string", "NumberOfEmployees": "number", "Industry": "string",
    "AnnualRevenue": "number",
}
CONTACT_FIELD_TYPES: dict[str, str] = {
    "LastName": "string", "AccountId": "string", "FirstName": "string", "Title": "string", "Email": "string",
    "Phone": "string", "MobilePhone": "string", "MailingStreet": "string", "MailingCity": "string",
    "MailingState": "string", "MailingPostalCode": "string", "MailingCountry": "string", "Description": "string",
    "LeadSource": "string", "Department": "string",
}


def _prepare_fields(
    fields_dict: dict[str, Any],
    required: frozenset[str],
    optional: frozenset[str],
    field_types: dict[str, str],
    object_name: str,
) -> dict[str, Any]:
    """Validate and coerce fields. Raises FieldMappingError for missing required, unknown field, or type error."""
    allowed = required | optional
    for key in fields_dict:
        if key not in allowed:
            raise FieldMappingError(f"Invalid field for {object_name}: '{key}'.")
    for req in required:
        val = fields_dict.get(req)
        if val is None or (isinstance(val, str) and not val.strip()):
            raise FieldMappingError(f"Required field for {object_name} is missing or empty: '{req}'.")
    out: dict[str, Any] = {}
    for k, v in fields_dict.items():
        if v is None or (isinstance(v, str) and not v.strip()):
            if k in required:
                raise FieldMappingError(f"Required field for {object_name} is missing or empty: '{k}'.")
            continue
        expected = field_types.get(k, "string")
        out[k] = _coerce_value(k, v, expected)
    return out


def validate_and_prepare_lead_fields(fields_dict: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce Lead fields. Raises FieldMappingError on failure."""
    return _prepare_fields(
        fields_dict, LEAD_REQUIRED, LEAD_OPTIONAL, LEAD_FIELD_TYPES, "Lead"
    )


def validate_and_prepare_contact_fields(fields_dict: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce Contact fields. Raises FieldMappingError on failure."""
    return _prepare_fields(
        fields_dict, CONTACT_REQUIRED, CONTACT_OPTIONAL, CONTACT_FIELD_TYPES, "Contact"
    )


def prepare_lead_fields_for_update(fields_dict: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce Lead fields for Update (partial). Raises FieldMappingError on failure."""
    allowed = LEAD_REQUIRED | LEAD_OPTIONAL
    for key in fields_dict:
        if key not in allowed:
            raise FieldMappingError(f"Invalid field for Lead: '{key}'.")
    out: dict[str, Any] = {}
    for k, v in fields_dict.items():
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        expected = LEAD_FIELD_TYPES.get(k, "string")
        out[k] = _coerce_value(k, v, expected)
    return out


def prepare_contact_fields_for_update(fields_dict: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce Contact fields for Update (partial). Raises FieldMappingError on failure."""
    allowed = CONTACT_REQUIRED | CONTACT_OPTIONAL
    for key in fields_dict:
        if key not in allowed:
            raise FieldMappingError(f"Invalid field for Contact: '{key}'.")
    out: dict[str, Any] = {}
    for k, v in fields_dict.items():
        if v is None or (isinstance(v, str) and not v.strip()):
            continue
        expected = CONTACT_FIELD_TYPES.get(k, "string")
        out[k] = _coerce_value(k, v, expected)
    return out
