# Changelog for m8flow-connectors

## Unreleased

`Added`

* n8n connector (`m8flow-connector-n8n`): trigger workflows via webhook with auth (header/bearer/basic),
  request/response payload mapping, timeout and retry handling, structured logging, plus REST API
  commands to list workflows and retrieve execution status (`TriggerWorkflow`, `ListWorkflows`,
  `GetExecution`, `ListExecutions`).

## 1.0.0 - 2026-03-31

`Added`

* Initial MVP release of connectors for Salesforce, Slack, SMTP, and Stripe.