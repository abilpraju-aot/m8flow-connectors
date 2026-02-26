# connector-slack

Slack connector for **m8flow**: post messages, send DMs, and upload files with OAuth token auth. Supports channel messaging, direct messaging, and file uploads with clear error reporting.

## Supported actions

| Action              | Command              | Description                                      |
|---------------------|----------------------|--------------------------------------------------|
| Post message        | `PostMessage`        | Send a message to a channel (with optional Block Kit) |
| Send direct message | `SendDirectMessage`  | Send a DM to a user (with optional Block Kit)    |
| Upload file         | `UploadFile`         | Upload a file to a channel or DM                 |

## Commands

- **PostMessage** – Post a message to a channel. Required: `channel` (ID or name, e.g. `C123`, `#general`), `message`. Optional: `blocks` (JSON string of Block Kit blocks; `message` is used as fallback).
- **SendDirectMessage** – Send a direct message to a user. Required: `user_id` (e.g. `U12345`), `message`. Optional: `blocks` (JSON string of Block Kit blocks; `message` is used as fallback).
- **UploadFile** – Upload a file to a channel or DM. Required: `channel`. Optional: `filename`, `initial_comment`, `filepath`, `content_base64`. Either `filepath` or `content_base64` must be provided.

The m8flow connector proxy introspects each command's `__init__` parameters, so these become the configuration options in the workflow UI.

## Authentication

- **Required**: `token` (Slack OAuth access token). Obtain and store via m8flow (or your platform's secure config/vault). Tokens are never logged or included in error messages.

## Error handling

- **SlackAuthError**: Invalid or revoked token (e.g. `invalid_auth`, `token_revoked`).
- **SlackPermissionError**: Missing scope (e.g. `missing_scope`).
- **SlackMessageFailed**: Other Slack API errors (e.g. invalid arguments, channel not found). Message includes Slack's details for workflow logs.
- **SlackUploadFailed**: File upload errors (e.g. pre-signed URL failure).
- **SlackFileNotFound** / **SlackInvalidBase64** / **SlackMissingContent**: Upload input validation errors.

## Adding this connector to m8flow-connector-proxy

1. In the m8flow-connector-proxy project, add this package as a dependency in `pyproject.toml`:

   ```toml
   connector-slack = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/connector-slack", branch = "main" }
   ```

2. Register the Slack connector and its commands in the proxy's connector configuration. The proxy discovers commands from `connector_slack.commands`: `PostMessage`, `SendDirectMessage`, `UploadFile`.

3. Configure the Slack OAuth token in m8flow and map it to the `token` parameter for each command in your workflows.

## Testing

```bash
pytest tests/
```

- Unit tests cover request construction, message formatting, success and error paths for all three commands.
- Negative tests cover invalid token (`invalid_auth`, `token_revoked`) and missing permissions (`missing_scope`).

Manual validation of Slack API operations is recommended.
