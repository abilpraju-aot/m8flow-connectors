# Stripe Connector for m8flow

Stripe payment connector supporting payment intents, charges, subscriptions, and refunds with idempotency key support.

## Features

- **Create Payment Intent**: Create payment intents for card payments
- **Create Charge**: Create direct charges (legacy API)
- **Create Subscription**: Set up recurring billing
- **Cancel Subscription**: Cancel active subscriptions
- **Issue Refund**: Full or partial refunds

## Installation

```bash
cd connectors/connector-stripe
poetry install
```

## Usage

Each command is instantiated with required parameters and executed via the `execute()` method:

```python
from connector_stripe.commands import CreatePaymentIntent

cmd = CreatePaymentIntent(
    api_key="sk_test_...",
    amount="1000",  # $10.00 in cents
    currency="usd",
    idempotency_key="unique-key-123"
)
result = cmd.execute({}, {})
```

## Idempotency

All write operations support idempotency keys to prevent duplicate operations during retries:

- Pass `idempotency_key` parameter to any command
- If not provided, a UUID is auto-generated
- Stripe caches responses for 24 hours per idempotency key

## Error Handling

The connector maps Stripe errors to clear error codes:

| Stripe Error | Connector Error Code |
|--------------|---------------------|
| `authentication_error` | `StripeAuthError` |
| `card_error` | `StripeCardError` |
| `invalid_request_error` | `StripeValidationError` |
| `rate_limit_error` | `StripeRateLimitError` |
| `api_error` | `StripeAPIError` |

## Testing

```bash
poetry run pytest
```

## Documentation

See [docs/STRIPE_CONNECTOR_SETUP.md](docs/STRIPE_CONNECTOR_SETUP.md) for detailed setup instructions.
