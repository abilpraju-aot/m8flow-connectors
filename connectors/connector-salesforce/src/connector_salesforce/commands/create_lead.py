"""Create a Lead in Salesforce."""
import json
from typing import Any

from connector_salesforce.connector_interface import ConnectorCommand
from connector_salesforce.connector_interface import ConnectorProxyResponseDict
from connector_salesforce.field_mapping import FieldMappingError
from connector_salesforce.field_mapping import validate_and_prepare_lead_fields
from connector_salesforce.salesforce_client import build_result
from connector_salesforce.salesforce_client import error_response
from connector_salesforce.salesforce_client import request_with_retry


class CreateLead(ConnectorCommand):
    """Create a single Lead record. Requires LastName and Company in fields."""

    def __init__(
        self,
        access_token: str,
        instance_url: str,
        fields: str,
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
    ):
        self.access_token = access_token
        self.instance_url = instance_url
        self.fields = fields
        self.refresh_token = refresh_token or ""
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        try:
            fields_dict = json.loads(self.fields) if isinstance(self.fields, str) else self.fields
        except (json.JSONDecodeError, TypeError) as exc:
            return error_response(400, "SalesforceValidationError", f"Invalid fields JSON: {exc}")
        try:
            payload = validate_and_prepare_lead_fields(fields_dict)
        except FieldMappingError as e:
            return error_response(400, "SalesforceValidationError", e.message)
        data, status, err, _token, _inst = request_with_retry(
            self.instance_url,
            self.access_token,
            self.refresh_token or None,
            self.client_id or None,
            self.client_secret or None,
            "POST",
            "Lead",
            body=payload,
        )
        if err:
            return build_result(data or {}, status, err)
        return build_result(data or {}, status, None)
