# M8flow Connectors

This repository contains connector packages used by [M8flow](https://github.com/AOT-Technologies/m8flow) to integrate workflows with external systems. Each connector packages a set of workflow-safe commands for a specific service so those actions can be used in BPMN Service Tasks without adding service-specific code to the core platform.

## Purpose Of This Repo

The goal of this repository is to keep M8flow integrations modular, testable, and easy to install.

- Each connector wraps a third-party system such as Slack, Salesforce, Stripe, or SMTP.
- Each package owns its authentication, input validation, API calls, and error handling.
- New integrations can be added to an M8flow deployment by installing a connector package into the connector runtime instead of changing the main M8flow codebase.

If you are looking for the full platform, deployment, and runtime services, start with the main repository: [AOT-Technologies/m8flow](https://github.com/AOT-Technologies/m8flow).

## Available Connectors

| Connector | Purpose |
|-----------|---------|
| `m8flow-connector-github` | Connect to repositories, list pull requests, and list branches |
| `m8flow-connector-salesforce` | Create, read, update, and delete Salesforce Leads and Contacts |
| `m8flow-connector-slack` | Post messages, send direct messages, and upload files to Slack |
| `m8flow-connector-smtp` | Send email through an SMTP server, including attachments |
| `m8flow-connector-stripe` | Create payment intents, charges, subscriptions, cancellations, and refunds |

Each connector has its own `README.md` with command-specific details, required parameters, and service-specific behavior.

## How Connectors Work With M8flow

M8flow does not call these packages directly from a BPMN model. Instead, the normal flow is:

1. A connector package from this repository is installed in the M8flow connector runtime, typically `m8flow-connector-proxy`.
2. The proxy discovers or registers the command classes exposed by that connector.
3. M8flow presents those commands as options for workflow Service Tasks.
4. The proxy inspects each command class constructor (`__init__`) and exposes those parameters as configurable fields in the workflow UI.
5. When the workflow runs, the selected command executes and returns a standard response payload for M8flow to consume.

In practice, each connector follows the same pattern:

- A Python package lives under `connectors/<connector-name>/src/<python_package>`.
- Command implementations live under `<python_package>.commands`.
- Each command defines the inputs it needs in `__init__`.
- Each command implements `execute(config, task_data)` and returns a response envelope containing `command_response`, `error`, and `command_response_version`.

This design keeps workflow authors focused on mapping inputs and outputs, while the connector package handles authentication details, request formatting, retries, and service-specific error translation.

## How To Install A Connector In M8flow

Installation is typically done in the M8flow connector runtime, not in the BPMN model itself.

1. Choose the connector package you want to use from this repository.
2. Add that package as a dependency in the `m8flow-connector-proxy` service used by your M8flow deployment.
3. Register or expose the connector's command classes in the proxy configuration.
4. Rebuild and redeploy the connector runtime so the new package is available.
5. Configure any required credentials or secrets in your M8flow environment and map them into workflows.

Example dependency entry in the proxy's `pyproject.toml`:

```toml
m8flow-connector-slack = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/m8flow-connector-slack", branch = "main" }
```

The same pattern applies to the other connectors in this repository by changing the package name and `subdirectory`.

After installation, the proxy should be configured to load the command classes exposed by the connector package. For most connectors in this repository, that means loading the package's `commands` module. The exact registration path should follow the connector-specific README for the package you install.

For the surrounding platform setup and deployment context, refer to the main [M8flow repository](https://github.com/AOT-Technologies/m8flow).

## How To Use A Connector In A Service Task

Once a connector is installed and available in the connector proxy, the general workflow authoring pattern is:

1. Add a Service Task to your BPMN workflow.
2. Select the connector command you want the task to execute.
3. Fill in the command inputs required by that connector.
4. Map workflow data into those inputs using process variables or expressions.
5. Store credentials in M8flow-managed configuration or secrets, not directly in the BPMN model.
6. Use the task result and any returned error details in downstream workflow logic.

The important rule is that the Service Task fields usually map directly to the command class constructor parameters. For example:

- Slack message tasks map values such as `token`, `channel`, and `message`.
- Salesforce tasks map values such as `access_token`, `instance_url`, and `fields`.
- SMTP tasks map values such as `smtp_host`, `email_to`, `email_subject`, and `attachments`.
- Stripe tasks map values such as `api_key`, `amount`, `currency`, or `subscription_id`.

At runtime, the connector command executes the external API call and returns a normalized result to M8flow. That lets workflows handle external integrations using a consistent Service Task pattern even though each third-party system has different request and authentication rules.

## Repository Layout

```text
connectors/
  m8flow-connector-salesforce/
  m8flow-connector-slack/
  m8flow-connector-smtp/
  m8flow-connector-stripe/
```

Each connector directory is an independently installable Python package with its own source code, tests, lockfile, and connector-specific README.
