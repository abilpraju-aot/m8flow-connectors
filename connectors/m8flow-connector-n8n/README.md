# M8flow Connector n8n

n8n connector for **m8flow**: invoke webhooks, list workflows, execute workflows via API, and retrieve execution status/results.

## Supported actions

| Action | Command | Description |
|--------|---------|-------------|
| Invoke webhook | `InvokeWebhook` | Call an n8n production or test webhook URL with JSON payload |
| List workflows | `ListWorkflows` | List workflows with optional active/name filters |
| Get workflow | `GetWorkflow` | Fetch workflow metadata by ID |
| Get workflow webhooks | `GetWorkflowWebhooks` | Derive production/test webhook URLs from workflow nodes |
| Execute workflow | `ExecuteWorkflow` | Trigger workflow execution via n8n REST API |
| Get execution | `GetExecution` | Retrieve execution status and optional node I/O |
| List executions | `ListExecutions` | List executions with optional workflow/status filters |

## Authentication

### REST API commands (`ListWorkflows`, `GetWorkflow`, `GetWorkflowWebhooks`, `ExecuteWorkflow`, `GetExecution`, `ListExecutions`)

- **Required**: `base_url` — n8n API root, e.g. `https://my-n8n.example.com/api/v1`
- **Required**: `api_key` — n8n API key sent as `X-N8N-API-KEY`

Create an API key in n8n under **Settings > n8n API**. Store credentials in m8flow secrets; they are never logged or included in error messages.

**Recommended API key scopes (enterprise):**

| Scope | Used by |
|-------|---------|
| `workflow:list` | `ListWorkflows` |
| `workflow:read` | `GetWorkflow`, `GetWorkflowWebhooks` |
| `workflow:execute` | `ExecuteWorkflow` |
| `execution:read` | `GetExecution` |
| `execution:list` | `ListExecutions` |

Non-enterprise API keys typically have full instance access.

### Webhook commands (`InvokeWebhook`)

- **Required**: `webhook_url` — full URL from the n8n Webhook node (production: `/webhook/...`, test: `/webhook-test/...`)
- **Optional**: `basic_auth_user` / `basic_auth_password` for basic-auth webhooks
- **Optional**: `headers` JSON for header-auth webhooks

**n8n prerequisites for webhooks:**

1. Workflow must be **Active** for production URLs.
2. Use the **production** URL (`/webhook/`), not the test URL (`/webhook-test/`), for unattended runs.
3. For synchronous responses, set the Webhook node to **Respond: When Last Node Finishes** (required for AI/LLM workflows returning results).

## Error handling

| Error code | Meaning |
|------------|---------|
| `N8nAuthError` | Invalid API key or webhook credentials (HTTP 401/403) |
| `N8nNotFoundError` | Workflow or execution not found (HTTP 404) |
| `N8nWebhookNotFound` | Webhook not registered; workflow may be inactive |
| `N8nWebhookFailed` | Webhook returned an error |
| `N8nValidationError` | Invalid command input (JSON, URL, method, timeout) |
| `N8nConnectionError` | Network failure reaching n8n |
| `N8nTimeout` | Request timed out |
| `N8nApiError` | Other n8n REST API errors |

## Sample Service Task patterns

### Invoke an AI/LLM workflow via webhook

```text
Command: n8n/InvokeWebhook
webhook_url: M8FLOW_SECRET:N8N_WEBHOOK_URL
method: POST
payload: {"prompt": "{{llm_prompt}}", "context": "{{context}}"}
timeout: 120
```

### List workflows then execute by ID

1. `n8n/ListWorkflows` with `active=true`
2. `n8n/ExecuteWorkflow` with selected `workflow_id` and `input_data`

### Poll execution status

1. `n8n/ExecuteWorkflow` or `n8n/InvokeWebhook`
2. `n8n/GetExecution` with `execution_id` from the response
3. Optionally `n8n/ListExecutions` filtered by `workflow_id` and `status`

## Adding this connector to m8flow-connector-proxy

1. Add the package as a dependency in `pyproject.toml` of the proxy:

   ```toml
   m8flow-connector-n8n = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/m8flow-connector-n8n", branch = "main" }
   ```

2. Register the n8n connector and its commands from `connector_n8n.commands`.
3. Configure n8n secrets in m8flow and map them to Service Task parameters.

## Testing

```bash
pytest tests/
```

Unit tests cover success and error paths for all commands. Manual validation against a live n8n instance is recommended.
