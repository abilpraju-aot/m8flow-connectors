# connector-slack

Slack connector for **m8flow**: post messages to channels, send direct messages, and upload files. Uses OAuth token-based authentication (token provided by m8flow; this connector does not store tokens). Errors from Slack APIs are surfaced in workflow logs with clear, actionable codes.

## Supported actions

- **Post message to a channel** – `PostMessage`: channel by ID or name, message text, optional Block Kit blocks.
- **Send direct message (DM) to a user** – `SendDirectMessage`: user by ID, message text, optional Block Kit blocks.
- **Upload file to a channel or DM** – `UploadFile`: channel or user ID, file content, filename, optional initial comment (plain text).

## Configuration options

- **Channel selector (by ID or name)**: `PostMessage` and `UploadFile` accept `channel` (e.g. `C123` or `#general`).
- **User selector (by ID)**: `SendDirectMessage` accepts `user_id` (e.g. `U12345`).
- **Message text**: All commands support message/comment text where applicable (`message`, `initial_comment`).
- **Block Kit**: Optional `blocks` (JSON string) for `PostMessage` and `SendDirectMessage` for structured messages; `text` is used as fallback.

The m8flow connector proxy introspects each command’s `__init__` parameters, so these become the configuration options in the workflow UI.

## Authentication

- **OAuth token**: The connector expects a Slack OAuth access token. Obtain and store it via m8flow (or your platform’s secure config/vault). This package does not implement OAuth flow or token storage.
- **Secure usage**: The token is sent only in the `Authorization: Bearer` header and is never logged or included in error messages.

## Adding this connector to m8flow-connector-proxy

1. In the m8flow-connector-proxy project (e.g. [m8flow](https://github.com/AOT-Technologies/m8flow) → `m8flow-connector-proxy`), add this package as a dependency in `pyproject.toml`:

   ```toml
   connector-slack = { path = "../connector-slack" }
   # or from git:
   # connector-slack = { git = "https://github.com/your-org/connector-slack.git", branch = "main" }
   ```

2. Register the Slack connector and its commands in the proxy’s connector configuration (same pattern as other connectors, e.g. `m8flow-connector-smtp`). The proxy discovers commands from `connector_slack.commands`: `PostMessage`, `SendDirectMessage`, `UploadFile`.

3. Configure the Slack OAuth token in m8flow (e.g. environment or secrets) and map it to the `token` parameter for each command in your workflows.

## Error handling

- **SlackAuthError**: Invalid or revoked token (e.g. `invalid_auth`, `token_revoked`).
- **SlackPermissionError**: Missing scope (e.g. `missing_scope`).
- **SlackMessageFailed**: Other Slack API errors (e.g. invalid arguments, channel not found); the message field includes Slack’s details for workflow logs.

## File upload note

File upload uses Slack’s `files.upload` API. Slack has deprecated this method (sunset Nov 2025). For MVP, `files.upload` is used; migration to `files.getUploadURLExternal` and `files.completeUploadExternal` is recommended later.

## Testing

```bash
pytest tests/
```

- Unit tests cover request construction, message formatting, success and error paths for all three commands.
- Negative tests cover invalid token (`invalid_auth`, `token_revoked`) and missing permissions (`missing_scope`).
