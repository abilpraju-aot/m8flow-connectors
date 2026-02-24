# connector-salesforce

Salesforce connector for **m8flow**: CRUD for Lead and Contact with OAuth 2.0. Supports create, read, update, and delete with field-mapping validation and clear error reporting.

## Supported objects and operations

| Object  | Create | Read | Update | Delete |
|---------|--------|------|--------|--------|
| Lead    | Yes    | Yes  | Yes    | Yes    |
| Contact | Yes    | Yes  | Yes    | Yes    |

## Commands

- **CreateLead** – Create a Lead. Required fields: `LastName`, `Company`. `fields` is a JSON string.
- **CreateContact** – Create a Contact. Required: `LastName`. `fields` is a JSON string.
- **ReadLead** / **ReadContact** – Read by `record_id` (e.g. `00Q...`, `003...`).
- **UpdateLead** / **UpdateContact** – Update by `record_id`; `fields` is a JSON string of fields to update.
- **DeleteLead** / **DeleteContact** – Delete by `record_id`.

The m8flow connector proxy introspects each command’s `__init__` parameters, so these become the configuration options in the workflow UI.

## Authentication

- **Required**: `access_token`, `instance_url` (e.g. `https://na50.salesforce.com`). Obtain and store via m8flow (or your platform’s secure config). Tokens are never logged or included in error messages.
- **Optional (token refresh)**: `refresh_token`, `client_id`, `client_secret`. When provided and a request returns 401, the connector will attempt to refresh the access token and retry once.

## Field mapping

- **Create**: `fields` must include required fields (Lead: `LastName`, `Company`; Contact: `LastName`). Supported types: string, number, boolean, date (YYYY-MM-DD). Invalid or unknown fields produce a clear `SalesforceValidationError`.
- **Update**: `fields` is a partial map; only provided fields are updated. Same type and allowed-field rules apply.

## Error handling

- **SalesforceAuthError**: Invalid or expired token (401).
- **SalesforcePermissionError**: Insufficient privileges (403).
- **SalesforceValidationError**: Invalid/missing fields or schema (400, 422), including local validation failures.
- **SalesforceApiError**: Other API errors (e.g. 404 record not found, 500). Message includes detail for workflow logs.

## Adding this connector to m8flow-connector-proxy

1. In the m8flow-connector-proxy project, add this package as a dependency in `pyproject.toml`:

   ```toml
   connector-salesforce = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/connector-salesforce", branch = "main" }
   ```

2. Register the Salesforce connector and its commands in the proxy’s connector configuration. The proxy discovers commands from `connector_salesforce.commands`: `CreateLead`, `CreateContact`, `ReadLead`, `ReadContact`, `UpdateLead`, `UpdateContact`, `DeleteLead`, `DeleteContact`.

3. Configure the Salesforce OAuth credentials in m8flow and map them to the command parameters in your workflows.

## Testing

```bash
pytest tests/
```

- Unit tests cover request building, field mapping (valid, missing required, invalid types, invalid field names), and success/error paths for all commands.
- Negative tests cover 401/403 and validation failures.

Manual validation of CRUD operations in a Salesforce org is recommended.
