# connector-stripe

Stripe connector for **m8flow**: create payment intents, create charges, create/cancel subscriptions, and issue refunds with idempotency support for write operations.

## Supported actions

| Action | Command | Description |
|---|---|---|
| Create payment intent | `CreatePaymentIntent` | Creates a Stripe PaymentIntent for payment processing. |
| Create charge | `CreateCharge` | Creates a Stripe Charge (legacy flow) using customer or payment method/source. |
| Create subscription | `CreateSubscription` | Creates a subscription for a customer and price. |
| Cancel subscription | `CancelSubscription` | Cancels a subscription by ID. |
| Issue refund | `IssueRefund` | Issues full or partial refund by charge or payment intent. |

The m8flow connector proxy introspects each command's `__init__` parameters, so these become configuration options in the workflow UI.

## Authentication

- **Required**: `api_key` (Stripe secret key, e.g. `sk_test_...`).
- Store the key in m8flow secrets (or your platform secure config).
- API keys are only sent in `Authorization: Bearer` headers and are never included in connector error messages.

## Idempotency behavior

For write operations (`CreatePaymentIntent`, `CreateCharge`, `CreateSubscription`, `CancelSubscription`, `IssueRefund`):

- Optional input: `idempotency_key`
- If provided, connector sends it as `Idempotency-Key`.
- If omitted, connector auto-generates a key using operation + payload + task context when available.
- This prevents duplicate writes during workflow retries.

## Command parameters (high level)

### CreatePaymentIntent
- Required: `api_key`, `amount`, `currency`
- Optional: `customer_id`, `payment_method`, `confirm`, `description`, `metadata`, `idempotency_key`

### CreateCharge
- Required: `api_key`, `amount`, `currency`
- At least one of: `customer_id` or `payment_method`
- Optional: `description`, `metadata`, `idempotency_key`

### CreateSubscription
- Required: `api_key`, `customer_id`, `price_id`
- Optional: `quantity`, `payment_method`, `trial_period_days`, `metadata`, `idempotency_key`

### CancelSubscription
- Required: `api_key`, `subscription_id`
- Optional: `invoice_now`, `prorate`, `idempotency_key`

### IssueRefund
- Required: `api_key`, and exactly one of `charge_id` or `payment_intent_id`
- Optional: `amount` (for partial refund), `reason`, `metadata`, `idempotency_key`

## Validation

Before calling Stripe, the connector validates:

- `amount` is positive integer (smallest currency unit)
- `currency` is 3-letter ISO code (normalized lowercase)
- required identifiers are present (`customer_id`, `subscription_id`, etc.)
- refund reference rules (exactly one of `charge_id`/`payment_intent_id`)
- metadata JSON format
- idempotency key length (<=255)

## Error handling

Stripe/API errors are normalized to connector codes:

- `StripeAuthError` (401)
- `StripeValidationError` (400/404/422, invalid params)
- `StripeCardError` (402 / card failure such as insufficient funds or declines)
- `StripeRateLimitError` (429)
- `StripeApiError` (other API/network failures)

Errors include Stripe message/type/code context when available, for clear workflow logs.

## Adding this connector to m8flow-connector-proxy

1. In m8flow-connector-proxy `pyproject.toml`, add:

```toml
connector-stripe = { git = "https://github.com/AOT-Technologies/m8flow-connectors.git", subdirectory = "connectors/connector-stripe", branch = "main" }
```

2. Register Stripe commands from `connector_stripe.commands`:
   - `CreatePaymentIntent`
   - `CreateCharge`
   - `CreateSubscription`
   - `CancelSubscription`
   - `IssueRefund`

3. Map workflow secret values to command parameters (especially `api_key`).

## Testing

Run unit tests:

```bash
pytest tests/
```

Coverage includes:
- request construction for each command
- idempotency key usage (provided and auto-generated)
- negative scenarios (invalid payment method, insufficient funds, duplicate retry semantics via idempotency)
- Stripe error mapping

## Manual QA (Stripe test environment)

1. Use a Stripe **test** secret key (`sk_test_...`).
2. Run `CreatePaymentIntent` and confirm object appears in Stripe Dashboard.
3. Run `CreateSubscription`, then `CancelSubscription`, and verify status transitions.
4. Run `IssueRefund` for full and partial amounts; verify refund records.
5. Re-run the same write operation with same `idempotency_key`; verify no duplicate object creation.
