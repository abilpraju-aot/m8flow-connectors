# M8flow Connector GitHub

GitHub connector for **m8flow**: connect to a repository, list pull requests, and list branches using GitHub Personal Access Token (PAT) authentication.

## Supported actions

| Action               | Command               | Description                                              |
|----------------------|-----------------------|----------------------------------------------------------|
| Connect to repository | `ConnectRepository`  | Verify access and fetch repository metadata              |
| List pull requests   | `ListPullRequests`    | List PRs with optional state filter and pagination       |
| List branches        | `ListBranches`        | List branches with optional protected filter and pagination |

## Commands

- **ConnectRepository** — Verify access to a repository and return its metadata. Required: `owner`, `repo`.
- **ListPullRequests** — List pull requests. Required: `owner`, `repo`. Optional: `state` (`open` / `closed` / `all`, default `open`), `per_page` (default 30), `page` (default 1).
- **ListBranches** — List branches. Required: `owner`, `repo`. Optional: `protected` (`true` / `false` / `""` for all, default `""`), `per_page` (default 30), `page` (default 1).

The m8flow connector proxy introspects each command's `__init__` parameters, so these become the configuration options in the workflow UI.

## Authentication

- **Required**: `token` — A GitHub **Personal Access Token (PAT)** (classic or fine-grained) or an OAuth token.
  - The token is passed as `Authorization: Bearer <token>` to the GitHub REST API v2022-11-28.
  - Tokens are **never logged** or included in error messages.
  - Obtain and store the token via m8flow (or your platform's secure config / vault).

### Minimum required scopes (classic PAT)

| Operation            | Scope          |
|----------------------|----------------|
| Public repositories  | *(none)*       |
| Private repositories | `repo`         |
| List pull requests   | `repo`         |
| List branches        | `repo`         |

For fine-grained PATs, grant **Contents: Read** and **Pull requests: Read** for the target repository.

## Error handling

- **GitHubAuthError**: Invalid or expired token (HTTP 401/403).
- **GitHubNotFoundError**: Repository not found or token lacks access (HTTP 404).
- **GitHubRequestFailed**: Other GitHub API errors. Message includes GitHub's details for workflow logs.

## Adding this connector to m8flow-connector-proxy

1. Add the package as a dependency in `pyproject.toml` of the proxy:

   ```toml
   m8flow-connector-github = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/m8flow-connector-github", branch = "main" }
   ```

2. Register the GitHub connector and its commands in the proxy's connector configuration. The proxy discovers commands from `connector_github.commands`: `ConnectRepository`, `ListPullRequests`, `ListBranches`.
3. Configure the GitHub PAT in m8flow and map it to the `token` parameter for each command in your workflows.

## Testing

```bash
pytest tests/
```

- Unit tests cover success and error paths for all three commands.
- Negative tests cover invalid tokens (401) and missing repositories (404).

Manual validation against the GitHub API is recommended.
