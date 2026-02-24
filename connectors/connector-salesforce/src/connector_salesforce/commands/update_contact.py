"""Update a Contact by ID in Salesforce."""
import json
from typing import Any

from connector_salesforce.connector_interface import ConnectorCommand
from connector_salesforce.connector_interface import ConnectorProxyResponseDict
from connector_salesforce.field_mapping import FieldMappingError
from connector_salesforce.field_mapping import prepare_contact_fields_for_update
from connector_salesforce.salesforce_client import build_result
from connector_salesforce.salesforce_client import error_response
from connector_salesforce.salesforce_client import request_with_retry


class UpdateContact(ConnectorCommand):
    """Update a single Contact record by record_id. fields is a JSON object of field names to values."""

    def __init__(
        self,
        access_token: str,
        instance_url: str,
        record_id: str,
        fields: str,
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
    ):
        self.access_token = access_token
        self.instance_url = instance_url
        self.record_id = record_id
        self.fields = fields
        self.refresh_token = refresh_token or ""
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not (self.record_id and str(self.record_id).strip()):
            return error_response(400, "SalesforceValidationError", "record_id is required.")
        try:
            fields_dict = json.loads(self.fields) if isinstance(self.fields, str) else self.fields
        except (json.JSONDecodeError, TypeError) as exc:
            return error_response(400, "SalesforceValidationError", f"Invalid fields JSON: {exc}")
        try:
            payload = prepare_contact_fields_for_update(fields_dict)
        except FieldMappingError as e:
            return error_response(400, "SalesforceValidationError", e.message)
        if not payload:
            return error_response(400, "SalesforceValidationError", "At least one field is required for update.")
        path = f"Contact/{str(self.record_id).strip()}"
        data, status, err, _token, _inst = request_with_retry(
            self.instance_url,
            self.access_token,
            self.refresh_token or None,
            self.client_id or None,
            self.client_secret or None,
            "PATCH",
            path,
            body=payload,
        )
        return build_result(data or {}, status, err)
