# M8flow Connector n8n

n8n connector for **m8flow**: trigger n8n workflows via their webhooks and exchange JSON payloads,
plus list/inspect workflows and retrieve execution status and results through the n8n Public API.

## Supported actions

| Action                | Command           | Description                                                        |
|-----------------------|-------------------|--------------------------------------------------------------------|
| Trigger workflow      | `TriggerWorkflow` | Invoke a workflow via its webhook URL, passing an optional payload |
| List workflows        | `ListWorkflows`   | List workflows with optional active filter and pagination          |
| Get workflow          | `GetWorkflow`     | Fetch a single workflow's details by id                            |
| List executions       | `ListExecutions`  | List executions, optionally filtered by workflow and status        |
| Get execution         | `GetExecution`    | Fetch a single execution's status and (optionally) result data     |

The m8flow connector proxy introspects each command's `__init__` parameters, so these become the
configuration options in the workflow UI.

## Commands

- **TriggerWorkflow** — Invoke a workflow through its Webhook node. Required: `webhook_url`. Optional:
  `method` (default `POST`), `payload` (JSON sent as body for non-GET, or query params for GET),
  `auth_type` (`none` / `header` / `basic`, default `none`), `auth_header_name`, `auth_header_value`
  (for `header`), `username`, `password` (for `basic`).
- **ListWorkflows** — List workflows. Required: `base_url`, `api_key`. Optional: `active`
  (`true` / `false` / `""` for all, default `""`), `limit` (default 100), `cursor`.
- **GetWorkflow** — Get one workflow. Required: `base_url`, `api_key`, `workflow_id`.
- **ListExecutions** — List executions. Required: `base_url`, `api_key`. Optional: `workflow_id`,
  `status` (`success` / `error` / `waiting`), `limit` (default 100), `cursor`.
- **GetExecution** — Get one execution. Required: `base_url`, `api_key`, `execution_id`. Optional:
  `include_data` (default `False`).

## Authentication

- **Webhook invocation (`TriggerWorkflow`)** — uses the auth configured on the n8n Webhook node:
  - `none` — no authentication.
  - `header` — a custom header (`auth_header_name` / `auth_header_value`), matching n8n "Header Auth".
  - `basic` — HTTP basic auth (`username` / `password`).
- **Public API (all other commands)** — `api_key` is an **n8n Public API key** (n8n *Settings > n8n API*),
  sent as the `X-N8N-API-KEY` header against `{base_url}/api/v1/...`.
- API keys and webhook credentials are **never logged** or included in error messages. Obtain and store
  them via m8flow (or your platform's secure config / vault).

## Sample workflow configuration

Configure an m8flow **service task** with the n8n connector. Example — trigger a workflow and read its
response:

| Parameter     | Value                                              |
|---------------|----------------------------------------------------|
| Command       | `n8n/TriggerWorkflow`                              |
| `webhook_url` | `https://n8n.example.com/webhook/abc-123`         |
| `method`      | `POST`                                             |
| `payload`     | `{ "customerId": 42, "action": "onboard" }`       |
| `auth_type`   | `header`                                           |
| `auth_header_name`  | `Authorization`                              |
| `auth_header_value` | `M8FLOW_SECRET:N8N_WEBHOOK_TOKEN` (resolved secret) |

The webhook's JSON response is returned in `command_response.parsed_body`; a non-JSON response (from an
n8n "Respond to Webhook" node returning text/binary) is returned as raw text.

For Public-API commands, set `base_url` and `api_key` from stored secrets, e.g.
`base_url = M8FLOW_SECRET:N8N_BASE_URL`, `api_key = M8FLOW_SECRET:N8N_API_KEY`.

### AI/LLM and file/document workflows

These are invoked exactly like any other workflow via `TriggerWorkflow` — build the workflow in n8n
(e.g. an LLM chain or a document-processing pipeline) behind a Webhook node, then pass the prompt/inputs
or file content (e.g. base64-encoded) in `payload`. The workflow's output comes back in the response.

## Error handling

- **N8nAuthError**: Invalid or missing API key / webhook credentials (HTTP 401/403).
- **N8nNotFoundError**: Workflow, execution, or webhook not found (HTTP 404).
- **N8nRequestFailed**: Other n8n API/webhook errors. Message includes n8n's details for workflow logs.
- **N8nInvalidInput**: A required parameter (e.g. `webhook_url`, `base_url`, `api_key`, an id) was missing.

## Adding this connector to m8flow-connector-proxy

1. Add the package as a dependency in `pyproject.toml` of the proxy:

   ```toml
   m8flow-connector-n8n = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/m8flow-connector-n8n", branch = "main" }
   ```

2. The proxy discovers commands from `connector_n8n.commands`: `TriggerWorkflow`, `ListWorkflows`,
   `GetWorkflow`, `ListExecutions`, `GetExecution`.
3. Configure the n8n base URL and API key in m8flow and map them to the `base_url` / `api_key`
   parameters; map webhook auth values to `TriggerWorkflow` parameters in your workflows.

## Testing

```bash
pytest tests/
```

- Unit tests cover success and error paths for all five commands.
- Negative tests cover invalid credentials (401), missing resources (404), and missing required input.

Manual validation against a real or local n8n instance is recommended.
