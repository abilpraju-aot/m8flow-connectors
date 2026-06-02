# n8n Connector — Onboarding & Testing

This walkthrough shows how to configure n8n, invoke a workflow from m8flow, map data in/out,
and track execution status. The same `TriggerWorkflow` command also covers AI/LLM and
file/document workflows.

## 1. Prepare n8n

1. **Create a webhook workflow** in n8n:
   - Add a **Webhook** node (set HTTP Method to `POST`). Note its **Production URL**
     (e.g. `https://n8n.example.com/webhook/abc123`).
   - Optionally set the Webhook node's **Authentication** (Header Auth / Basic Auth) — this must
     match the `auth_type` you use from m8flow.
   - Add downstream nodes (e.g. an HTTP/Set/Code node) and a **Respond to Webhook** node so the
     workflow returns JSON to m8flow.
   - **Activate** the workflow.
2. **Create an API key** (for `ListWorkflows` / `GetExecution` / `ListExecutions`):
   - n8n → **Settings → n8n API → Create an API key**. This key is sent as `X-N8N-API-KEY`.

## 2. Configure the connector in m8flow

Store the n8n base URL, webhook URL, and API key / webhook credentials as m8flow secrets, then map
them to the command parameters in a Service Task. The proxy renders each command's `__init__`
parameters as configurable fields. See [sample-trigger-workflow.bpmn](sample-trigger-workflow.bpmn).

## 3. Invoke a workflow (request mapping)

Use **`TriggerWorkflow`**. Map m8flow workflow variables into `payload` (JSON). Example payload in
[sample-payload.json](sample-payload.json):

```json
{
  "customerId": "CUST-00123",
  "email": "ada@example.com",
  "requestType": "enrichment",
  "metadata": { "source": "m8flow", "priority": "high" }
}
```

Example parameters:

| Parameter   | Value                                            |
|-------------|--------------------------------------------------|
| `webhook_url` | `https://n8n.example.com/webhook/abc123`       |
| `auth_type`   | `header`                                        |
| `api_key`     | *(from m8flow secret)*                          |
| `payload`     | JSON mapped from workflow variables             |
| `timeout`     | `30`                                            |
| `max_retries` | `2`                                             |

## 4. Read the result (response mapping)

The n8n JSON response is returned at `command_response.parsed_body`. Map fields from it back into
m8flow workflow variables in the Service Task output mapping, e.g. `n8n_result.parsed_body.summary`.

## 5. Track execution status

If your workflow returns an `executionId`, pass it to **`GetExecution`** (with `base_url` + `api_key`)
to retrieve `status` (`success` / `error` / `waiting`) and result data. Use **`ListExecutions`** to
review recent runs, optionally filtered by `workflow_id` / `status`.

## 6. Discover workflows

Use **`ListWorkflows`** (with `base_url` + `api_key`) to list available n8n workflows so they can be
selected when configuring the connector.

## AI/LLM workflows

Build an n8n workflow whose nodes call an LLM (OpenAI, Anthropic, etc.). Trigger it with
`TriggerWorkflow`, passing the prompt/inputs in `payload`:

```json
{ "prompt": "Summarize this support ticket", "ticket": "...", "maxTokens": 500 }
```

The model output is returned in the webhook response and surfaced via `parsed_body`.

## File / document workflows

For file/document processing, send file content as **base64** inside `payload` (n8n can convert it
back to binary with a *Move Binary Data* / *Code* node):

```json
{ "filename": "invoice.pdf", "mimeType": "application/pdf", "contentBase64": "JVBERi0xLjQK..." }
```

The processed result (extracted text, classification, etc.) comes back in the webhook response.

## Quick local sanity check (no n8n required)

```bash
cd connectors/m8flow-connector-n8n
pip install -e .            # or: poetry install
pytest tests/               # all unit tests use mocked HTTP
```

To exercise a real instance, set your `webhook_url`/`base_url`/`api_key` and run `TriggerWorkflow`,
then `GetExecution` with the returned execution id.
