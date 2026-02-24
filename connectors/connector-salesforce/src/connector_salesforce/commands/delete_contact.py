"""Delete a Contact by ID from Salesforce."""
from typing import Any

from connector_salesforce.connector_interface import ConnectorCommand
from connector_salesforce.connector_interface import ConnectorProxyResponseDict
from connector_salesforce.salesforce_client import build_result
from connector_salesforce.salesforce_client import error_response
from connector_salesforce.salesforce_client import request_with_retry


class DeleteContact(ConnectorCommand):
    """Delete a single Contact record by record_id."""

    def __init__(
        self,
        access_token: str,
        instance_url: str,
        record_id: str,
        refresh_token: str = "",
        client_id: str = "",
        client_secret: str = "",
    ):
        self.access_token = access_token
        self.instance_url = instance_url
        self.record_id = record_id
        self.refresh_token = refresh_token or ""
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""

    def execute(self, _config: Any, _task_data: Any) -> ConnectorProxyResponseDict:
        if not (self.record_id and str(self.record_id).strip()):
            return error_response(400, "SalesforceValidationError", "record_id is required.")
        path = f"Contact/{str(self.record_id).strip()}"
        data, status, err, _token, _inst = request_with_retry(
            self.instance_url,
            self.access_token,
            self.refresh_token or None,
            self.client_id or None,
            self.client_secret or None,
            "DELETE",
            path,
        )
        if status == 204 and not err:
            return build_result({}, 204, None)
        return build_result(data or {}, status, err)
