# connector-stripe

Stripe connector for **m8flow**: create payment intents, charges, subscriptions, and refunds with API key auth. Supports idempotency keys for all write operations to prevent duplicate charges during retries.

## Supported actions


| Action                | Command               | Description                                 |
| --------------------- | --------------------- | ------------------------------------------- |
| Create payment intent | `CreatePaymentIntent` | Create a payment intent for card payments   |
| Create charge         | `CreateCharge`        | Create a charge (legacy Charges API)        |
| Create subscription   | `CreateSubscription`  | Set up recurring billing for a customer     |
| Cancel subscription   | `CancelSubscription`  | Cancel immediately or at period end         |
| Issue refund          | `IssueRefund`         | Full or partial refund for a charge/payment |


## Commands

- **CreatePaymentIntent** – Create a payment intent. Required: `api_key`, `amount`, `currency`. Optional: `customer_id`, `payment_method`, `confirm`, `description`, `metadata`, `idempotency_key`.
- **CreateCharge** – Create a charge. Required: `api_key`, `amount`, `currency`, `source`. Optional: `customer_id`, `description`, `metadata`, `idempotency_key`.
- **CreateSubscription** – Create a subscription. Required: `api_key`, `customer_id`, `price_id`. Optional: `payment_behavior`, `default_payment_method`, `metadata`, `idempotency_key`.
- **CancelSubscription** – Cancel a subscription. Required: `api_key`, `subscription_id`. Optional: `cancel_at_period_end`, `idempotency_key`.
- **IssueRefund** – Issue a refund. Required: `api_key`, plus `charge_id` or `payment_intent_id`. Optional: `amount` (partial), `reason`, `metadata`, `idempotency_key`.

The m8flow connector proxy introspects each command's `__init__` parameters, so these become the configuration options in the workflow UI.

## Authentication

- **Required**: `api_key` (Stripe secret API key, e.g. `sk_test_...` or `sk_live_...`). Obtain from your Stripe Dashboard and store via m8flow (or your platform's secure config/vault). API keys are never logged or included in error messages.

## Idempotency

All write operations support idempotency keys to prevent duplicate operations during retries:

- Pass `idempotency_key` parameter to any command
- If not provided, a UUID is automatically generated
- Stripe caches responses for 24 hours per idempotency key

## Error handling

- **StripeAuthError**: Invalid API key (HTTP 401).
- **StripeCardError**: Card was declined, includes decline code (HTTP 402).
- **StripeValidationError**: Invalid parameters (HTTP 400).
- **StripeRateLimitError**: Too many requests (HTTP 429).
- **StripeAPIError**: Stripe server error (HTTP 500).
- **StripeTimeout**: Request timed out (HTTP 504).
- **StripeConnectionError**: Network error (HTTP 503).

## Adding this connector to m8flow-connector-proxy

1. In the m8flow-connector-proxy project, add this package as a dependency in `pyproject.toml`:
  ```toml
   connector-stripe = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/connector-stripe", branch = "main" }
  ```
2. Register the Stripe connector and its commands in the proxy's connector configuration. The proxy discovers commands from `connector_stripe.commands`: `CreatePaymentIntent`, `CreateCharge`, `CreateSubscription`, `CancelSubscription`, `IssueRefund`.
3. Configure the Stripe API key in m8flow and map it to the `api_key` parameter for each command in your workflows.



## Testing

```bash
pytest tests/
```

- Unit tests cover request construction, idempotency handling, success and error paths for all five commands.
- Negative tests cover invalid API key, card declined, insufficient funds, and duplicate request retries.

For step-by-step testing (including account creation and manual API checks), see [docs/STRIPE_TESTING_GUIDE.md](docs/STRIPE_TESTING_GUIDE.md). Manual validation in Stripe Dashboard (test environment) is recommended.