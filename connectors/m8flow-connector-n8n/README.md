# M8flow Connector n8n

n8n connector for **m8flow**: invoke n8n workflows via webhooks, list available workflows, and
retrieve workflow execution status/results. Workflows are triggered with a JSON payload mapped
from m8flow workflow variables, and the n8n response is mapped back for downstream tasks.

## Supported actions

| Action                | Command           | Description                                                        |
|-----------------------|-------------------|--------------------------------------------------------------------|
| Trigger workflow      | `TriggerWorkflow` | Invoke an n8n webhook URL with a JSON payload and return the result |
| List workflows        | `ListWorkflows`   | List workflows from an n8n instance (REST API)                     |
| Get execution         | `GetExecution`    | Retrieve a single execution's status/result by id (REST API)       |
| List executions       | `ListExecutions`  | List executions, optionally filtered by workflow/status (REST API) |

The m8flow connector proxy introspects each command's `__init__` parameters, so these become the
configuration options in the workflow UI (Service Task fields). There is no separate connector
configuration UI/API in this repository — configuration is managed through the proxy and m8flow
secrets, exactly like every other connector here.

## Commands

### TriggerWorkflow
Invoke an n8n workflow through its webhook. This is the primary invocation command and works for
**any** n8n workflow, including AI/LLM workflows and file/document-processing workflows (send file
content as base64 inside `payload`).

- **Endpoint**: provide `webhook_url` (full URL), or `base_url` + `webhook_path`.
- **Optional**: `method` (default `POST`), `payload` (JSON object/string, default `{}`),
  `query_params` (JSON object/string), `timeout` (default 30), `max_retries` (default 0).
- **Auth** (see below): `auth_type`, `api_key`, `auth_header_name`, `bearer_token`,
  `basic_username`, `basic_password`.
- **Output**: the workflow's JSON response is returned in `command_response.parsed_body`.

### ListWorkflows
List workflows so they can be discovered/selected. Required: `base_url`, `api_key`.
Optional: `active` (`true`/`false`/`""`), `limit` (default 100), `timeout`.

### GetExecution
Retrieve one execution's status and (optionally) its result data. Required: `base_url`, `api_key`,
`execution_id`. Optional: `include_data` (default `true`), `timeout`.

### ListExecutions
List recent executions to track run history/status. Required: `base_url`, `api_key`.
Optional: `workflow_id`, `status` (`success`/`error`/`waiting`/`""`), `limit` (default 100), `timeout`.

## Authentication

Two authentication contexts apply:

- **Webhook invocation (`TriggerWorkflow`)** — matches whatever the n8n *Webhook* node is configured
  for, selected via `auth_type`:
  | `auth_type` | Required params                       | Sent as                                  |
  |-------------|---------------------------------------|------------------------------------------|
  | `none`      | —                                     | (no auth)                                |
  | `header`    | `api_key` (+ optional `auth_header_name`) | `<auth_header_name>: <api_key>` (default `X-N8N-API-KEY`) |
  | `bearer`    | `bearer_token`                        | `Authorization: Bearer <bearer_token>`   |
  | `basic`     | `basic_username`, `basic_password`    | HTTP Basic auth                          |

- **REST API (`ListWorkflows`, `GetExecution`, `ListExecutions`)** — uses an n8n **API key** sent as
  the `X-N8N-API-KEY` header. Create the key in n8n under *Settings → n8n API*.

All credentials are obtained and stored via m8flow (or your platform's secure config / vault),
passed into the command at runtime, and are **never logged** or included in error messages.

## Endpoint configuration

- **Base URL** — your n8n instance, e.g. `https://n8n.example.com`.
- **Webhook URL** — the full webhook URL from the n8n Webhook node (test vs production URL).
- **Workflow id** — used by `ListExecutions` (filter) and surfaced by `ListWorkflows`.
- **Timeout** — per-request timeout in seconds (default 30).
- **Retry** — `max_retries` on `TriggerWorkflow` retries transient failures (timeout / 429 / 5xx).

## Request & response mapping

- **Request**: map m8flow workflow variables into the `payload` (and `query_params`) JSON. Dynamic
  input mapping is supported — any JSON structure is accepted and forwarded as the webhook body.
- **Response**: the n8n JSON response is available at `command_response.parsed_body`; map fields from
  it back into m8flow workflow variables in the Service Task's output mapping.

## Error handling

| Error code           | When                                                                 |
|----------------------|----------------------------------------------------------------------|
| `N8nConfigError`     | Invalid/missing config: no URL, bad JSON payload, missing credential |
| `N8nAuthError`       | Authentication failed (HTTP 401/403)                                 |
| `N8nNotFoundError`   | Webhook/workflow/execution not found (HTTP 404)                      |
| `N8nTimeoutError`    | Request exceeded the configured timeout                              |
| `N8nExecutionFailed` | Webhook/workflow execution failed (HTTP 5xx)                         |
| `N8nInvalidResponse` | Missing or non-JSON response body                                    |
| `N8nRequestFailed`   | Other n8n API errors (message included for workflow logs)            |

Request, response status, execution id (when present), errors, and retry attempts are logged via
the standard Python logger (`connector_n8n.n8n_client`) without exposing credentials.

## Adding this connector to m8flow-connector-proxy

1. Add the package as a dependency in `pyproject.toml` of the proxy:

   ```toml
   m8flow-connector-n8n = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/m8flow-connector-n8n", branch = "main" }
   ```

2. Register the n8n connector and its commands in the proxy's connector configuration. The proxy
   discovers commands from `connector_n8n.commands`: `TriggerWorkflow`, `ListWorkflows`,
   `GetExecution`, `ListExecutions`.
3. Configure the n8n API key / webhook credentials in m8flow and map them to the relevant command
   parameters in your workflows.

## Examples

See [examples/](examples/) for a sample BPMN Service Task wired to `TriggerWorkflow`, a sample
payload, and an onboarding/testing walkthrough (including AI/LLM and file-processing workflows).

## Testing

```bash
pytest tests/
```

- Unit tests cover success and error paths for all four commands and the shared client.
- Negative tests cover invalid config, auth failure (401/403), not found (404), timeout, execution
  failure (5xx), invalid response, and the retry path.
- Tests assert credentials are never written to logs.

Manual validation against a live n8n instance is recommended — see the examples README.
