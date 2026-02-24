# Slack file upload test workflow

This folder contains a **single-purpose BPMN workflow** that tests only the **Slack UploadFile** connector. It mirrors the structure of the [smtp-test](../smtp-test) workflow: init defaults, optional compose form, one service task, and a review form to inspect the result.

## Purpose

- Test **connector_slack/UploadFile** in isolation (no PostMessage or SendDirectMessage).
- Compose upload parameters in a form (channel, token, file content, filename, initial comment) or pass them as process variables.
- Review the connector response (success/error and raw payload) in a second form.

## Flow

1. **Init** – Sets default `slack_upload_compose` (channel, token, content, filename, initial_comment). Process variables override when provided at start.
2. **Compose Slack Upload** – User task with form to edit upload parameters.
3. **Upload file to Slack** – Service task calling `connector_slack/UploadFile`.
4. **Set upload_response** – Script copies the service task result into `upload_response`.
5. **Build review_slack_upload** – Script normalizes the result into status, message, error, and raw fields.
6. **Review Upload Result** – User task with read-only form showing the outcome.
7. **End**

## Prerequisites

1. **Connector proxy** with `connector_slack` registered (e.g. m8flow-connector-proxy). The UploadFile command must be available.
2. **Slack OAuth token** with scope `files:write` (and access to the target channel). Store in platform secrets (e.g. `SLACK_BOT_TOKEN`).
3. **m8flow** (or SpiffArena) configured to use the connector proxy and to load form schemas from this folder (or the process model that includes these files).

## Import and run

1. **Import the process model**  
   Import the `slack-upload-test` folder as a process model (or add `slack-upload-test.bpmn` and the JSON schema/uischema files to an existing model so the user tasks can resolve `formJsonSchemaFilename` / `formUiSchemaFilename`).

2. **Start a process instance**  
   Optionally provide process variables so the Init script uses them instead of defaults:
   - **token** – e.g. `SPIFF_SECRET:SLACK_BOT_TOKEN` or the actual token (required for upload).
   - **channel** – e.g. `#general` or channel ID.
   - **content**, **filename**, **initial_comment** – file content and metadata.

   If you do not set `token` at start, fill it in the **Compose Slack Upload** form before the workflow runs the Upload service task.

3. **Complete the user tasks**  
   Fill in **Compose Slack Upload** (or leave defaults), then run through to **Review Upload Result** and complete it to reach End.

## Files

| File | Description |
|------|-------------|
| `slack-upload-test.bpmn` | BPMN process definition |
| `process_model.json` | Process metadata (primary file, process ID) |
| `slack-upload-compose-schema.json` | JSON schema for the compose form |
| `slack-upload-compose-uischema.json` | UI schema for the compose form |
| `review-slack-upload-schema.json` | JSON schema for the review form |
| `review-slack-upload-uischema.json` | UI schema for the review form (read-only) |
| `slack_upload_workflow_config.yaml` | Optional reference for operator and parameters |

## Operator

- **connector_slack/UploadFile** – Parameters: `token`, `channel`, `content`, `filename`, `initial_comment`.
