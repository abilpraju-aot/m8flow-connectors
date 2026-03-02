# Stripe Connector Setup Guide

This guide explains how to set up and use the Stripe connector for m8flow workflows.

## Prerequisites

1. A Stripe account (test or live)
2. Stripe API keys from your [Stripe Dashboard](https://dashboard.stripe.com/apikeys)

## Getting Your API Key

1. Log in to your [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to **Developers > API keys**
3. Copy your **Secret key**:
   - Use `sk_test_...` for testing
   - Use `sk_live_...` for production

**Important**: Never expose your secret key in client-side code or commit it to version control.

## Installation

```bash
cd connectors/connector-stripe
poetry install
```

## Available Commands

### CreatePaymentIntent

Creates a Payment Intent for card payments (recommended for new integrations).

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `api_key` | Yes | Stripe secret API key |
| `amount` | Yes | Amount in smallest currency unit (e.g., 1000 = $10.00) |
| `currency` | Yes | 3-letter ISO currency code (e.g., `usd`, `eur`) |
| `customer_id` | No | Stripe customer ID (`cus_...`) |
| `payment_method` | No | Payment method ID (`pm_...`) |
| `confirm` | No | Confirm immediately (`true`/`false`) |
| `description` | No | Payment description |
| `metadata` | No | JSON string of key-value pairs |
| `idempotency_key` | No | Unique key for idempotency |

**Example:**
```python
from connector_stripe.commands import CreatePaymentIntent

cmd = CreatePaymentIntent(
    api_key="sk_test_...",
    amount="2000",
    currency="usd",
    description="Order #12345",
    metadata='{"order_id": "12345"}'
)
result = cmd.execute({}, {})
```

### CreateCharge

Creates a charge using the legacy Charges API.

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `api_key` | Yes | Stripe secret API key |
| `amount` | Yes | Amount in smallest currency unit |
| `currency` | Yes | 3-letter ISO currency code |
| `source` | Yes | Payment source token (`tok_...`) |
| `customer_id` | No | Stripe customer ID |
| `description` | No | Charge description |
| `metadata` | No | JSON string of key-value pairs |
| `idempotency_key` | No | Unique key for idempotency |

### CreateSubscription

Creates a recurring subscription for a customer.

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `api_key` | Yes | Stripe secret API key |
| `customer_id` | Yes | Stripe customer ID (`cus_...`) |
| `price_id` | Yes | Stripe price ID (`price_...`) |
| `payment_behavior` | No | One of: `default_incomplete`, `error_if_incomplete`, `allow_incomplete`, `pending_if_incomplete` |
| `default_payment_method` | No | Default payment method ID |
| `metadata` | No | JSON string of key-value pairs |
| `idempotency_key` | No | Unique key for idempotency |

**Example:**
```python
from connector_stripe.commands import CreateSubscription

cmd = CreateSubscription(
    api_key="sk_test_...",
    customer_id="cus_abc123",
    price_id="price_xyz789",
    payment_behavior="default_incomplete"
)
result = cmd.execute({}, {})
```

### CancelSubscription

Cancels an active subscription immediately or at the end of the billing period.

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `api_key` | Yes | Stripe secret API key |
| `subscription_id` | Yes | Subscription ID (`sub_...`) |
| `cancel_at_period_end` | No | If `true`, cancel at period end; if `false`, cancel immediately |
| `idempotency_key` | No | Unique key for idempotency |

### IssueRefund

Issues a full or partial refund for a charge or payment intent.

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| `api_key` | Yes | Stripe secret API key |
| `charge_id` | No* | Charge ID (`ch_...`) |
| `payment_intent_id` | No* | Payment Intent ID (`pi_...`) |
| `amount` | No | Partial refund amount (full refund if omitted) |
| `reason` | No | One of: `duplicate`, `fraudulent`, `requested_by_customer` |
| `metadata` | No | JSON string of key-value pairs |
| `idempotency_key` | No | Unique key for idempotency |

*Either `charge_id` or `payment_intent_id` is required.

**Example:**
```python
from connector_stripe.commands import IssueRefund

# Full refund
cmd = IssueRefund(
    api_key="sk_test_...",
    payment_intent_id="pi_abc123"
)

# Partial refund
cmd = IssueRefund(
    api_key="sk_test_...",
    charge_id="ch_xyz789",
    amount="500",  # Refund $5.00
    reason="requested_by_customer"
)
```

## Idempotency

All write operations support idempotency keys to prevent duplicate operations during retries.

### How It Works

1. Pass an `idempotency_key` parameter to any command
2. If not provided, a UUID is automatically generated
3. Stripe caches responses for 24 hours per idempotency key
4. Retrying with the same key returns the cached response

### Best Practices

- Use meaningful, unique keys (e.g., `order-{order_id}-payment`)
- Store the idempotency key with your order/transaction record
- For workflows, use the workflow instance ID as part of the key

**Example:**
```python
cmd = CreatePaymentIntent(
    api_key="sk_test_...",
    amount="1000",
    currency="usd",
    idempotency_key=f"workflow-{workflow_id}-payment"
)
```

## Error Handling

The connector maps Stripe errors to clear error codes:

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `StripeAuthError` | 401 | Invalid API key |
| `StripeCardError` | 402 | Card was declined |
| `StripeValidationError` | 400 | Invalid parameters |
| `StripeRateLimitError` | 429 | Too many requests |
| `StripeAPIError` | 500 | Stripe server error |
| `StripeTimeout` | 504 | Request timed out |
| `StripeConnectionError` | 503 | Network error |

### Handling Card Declines

Card errors include the decline code when available:

```python
result = cmd.execute({}, {})
if result["error"]:
    error_code = result["error"]["error_code"]
    message = result["error"]["message"]
    
    if error_code == "StripeCardError":
        # Check for specific decline reasons in message
        if "insufficient_funds" in message:
            # Handle insufficient funds
            pass
```

### Common Decline Codes

- `insufficient_funds` - Card has insufficient funds
- `lost_card` - Card reported lost
- `stolen_card` - Card reported stolen
- `expired_card` - Card has expired
- `incorrect_cvc` - CVC verification failed
- `processing_error` - Processing error, retry later

## Testing

### Test API Keys

Always use test API keys (`sk_test_...`) during development. Test mode:
- Does not process real payments
- Uses [test card numbers](https://stripe.com/docs/testing#cards)
- Has separate data from live mode

### Test Card Numbers

| Card Number | Description |
|-------------|-------------|
| `4242424242424242` | Succeeds |
| `4000000000000002` | Declined |
| `4000000000009995` | Insufficient funds |
| `4000000000000069` | Expired card |

### Running Unit Tests

```bash
cd connectors/connector-stripe
poetry run pytest
```

## Security Best Practices

1. **Never log API keys** - The connector is designed to never include API keys in error messages or logs
2. **Use environment variables** - Store API keys in environment variables or a secrets manager
3. **Rotate keys regularly** - Rotate your API keys periodically
4. **Use restricted keys** - Create restricted API keys with only the permissions you need
5. **Monitor usage** - Set up alerts in Stripe Dashboard for unusual activity

## Workflow Integration

### BPMN Service Task

Use the connector in BPMN workflows with a service task:

```xml
<bpmn:serviceTask id="create_payment" name="Create Payment Intent">
  <bpmn:extensionElements>
    <spiffworkflow:serviceTaskOperator id="stripe/CreatePaymentIntent">
      <spiffworkflow:parameters>
        <spiffworkflow:parameter id="api_key" type="str" value="secrets.stripe_api_key" />
        <spiffworkflow:parameter id="amount" type="str" value="order.amount" />
        <spiffworkflow:parameter id="currency" type="str" value="order.currency" />
      </spiffworkflow:parameters>
    </spiffworkflow:serviceTaskOperator>
  </bpmn:extensionElements>
</bpmn:serviceTask>
```

### Storing Secrets

Store your Stripe API key in m8flow platform secrets:
1. Navigate to **Settings > Secrets**
2. Add a new secret named `stripe_api_key`
3. Reference it in workflows as `secrets.stripe_api_key`

## Troubleshooting

### "Invalid API Key provided"

- Verify you're using the correct API key (test vs live)
- Check the key hasn't been revoked in Stripe Dashboard
- Ensure no extra whitespace in the key

### "No such customer"

- Verify the customer ID exists in your Stripe account
- Check you're using the correct mode (test vs live)

### "Amount must be at least 50 cents"

- Stripe has minimum charge amounts per currency
- USD minimum is typically $0.50 (50 cents)

### Duplicate Charges

- Ensure you're using idempotency keys for all payment operations
- Check your retry logic isn't creating new idempotency keys on each retry
