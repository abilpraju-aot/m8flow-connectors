# Stripe Connector – Setup and Usage

This document walks you through creating a Stripe account, generating API keys, configuring the connector in m8flow, and using it in workflows to create payment intents, charges, subscriptions, and refunds. It is written for users who have not used the Stripe API before.

---

## Prerequisites

- **Stripe account** (free to create at [stripe.com](https://stripe.com)).
- **m8flow** (or m8flow-connector-proxy) environment where the Stripe connector is or will be registered.

For technical reference (commands, parameters, error codes), see the [connector-stripe README](../README.md).

---

## 1. Create a Stripe Account

1. Go to [dashboard.stripe.com/register](https://dashboard.stripe.com/register).
2. Enter your email, name, and create a password.
3. Verify your email address.
4. You now have access to Stripe's **test mode** dashboard.

---

## 2. Get Your API Keys

Stripe uses API keys for authentication. There are two types:

| Key Type | Prefix | Purpose |
|----------|--------|---------|
| **Secret key** | `sk_test_` or `sk_live_` | Server-side API calls (used by the connector) |
| **Publishable key** | `pk_test_` or `pk_live_` | Client-side (not used by this connector) |

**To get your secret key:**

1. In the Stripe Dashboard, click **Developers** in the left sidebar.
2. Click **API keys**.
3. Under **Standard keys**, you will see your **Secret key**. Click **Reveal test key** to view it.
4. Copy the secret key (starts with `sk_test_`).

**Security:** Treat this key as a secret. Store it only in m8flow secrets/vault (or your platform's secure config). Do not put it in code, logs, or documentation.

---

## 3. Test Mode vs Live Mode

- **Test mode** (`sk_test_`): Use for development and testing. No real money is charged.
- **Live mode** (`sk_live_`): Use for production. Real payments are processed.

Toggle between modes using the **Test mode** switch in the Stripe Dashboard. The connector works with both; just use the appropriate API key.

---

## 4. Store the API Key in m8flow

1. Copy your **Secret key** from the Stripe Dashboard.
2. In m8flow, add this key to your **secrets/vault** (or environment config).
3. In your workflows, map that secret to the **api_key** parameter for each Stripe connector command.

The connector sends the API key only in the `Authorization: Bearer` header to Stripe; it does not log or expose it.

---

## 5. Add the Stripe Connector to m8flow-connector-proxy (if applicable)

If you are deploying the connector via m8flow-connector-proxy:

1. In the m8flow-connector-proxy project, add the Stripe connector as a dependency in `pyproject.toml`:

```toml
[tool.poetry.dependencies]
connector-stripe = { git = "https://github.com/your-org/m8flow-connectors.git", subdirectory = "connectors/connector-stripe" }
```

2. Register the Stripe connector and its commands in the proxy's connector configuration.

See the [connector-stripe README – Adding this connector to m8flow-connector-proxy](../README.md#adding-this-connector-to-m8flow-connector-proxy) for exact steps.

---

## 6. Using the Connector in Workflows

### Available Commands

| Command | Description |
|---------|-------------|
| **CreatePaymentIntent** | Create a payment intent (recommended for most payment flows) |
| **CreateCharge** | Create a charge (legacy, use PaymentIntent for new integrations) |
| **CreateSubscription** | Create a recurring subscription for a customer |
| **CancelSubscription** | Cancel an existing subscription |
| **IssueRefund** | Refund a charge or payment intent (full or partial) |

### Common Parameters

| Parameter | Description |
|-----------|-------------|
| `api_key` | Stripe secret key (from m8flow secrets) |
| `amount` | Amount in smallest currency unit (e.g., 1000 = $10.00 for USD) |
| `currency` | 3-letter ISO currency code (e.g., `usd`, `eur`, `gbp`) |
| `customer_id` | Stripe customer ID (e.g., `cus_...`) |
| `payment_method` | Payment method ID (e.g., `pm_...`) |
| `idempotency_key` | Optional key to prevent duplicate operations on retries |

### CreatePaymentIntent Example

| Parameter | Value |
|-----------|-------|
| `api_key` | `{{ secrets.stripe_api_key }}` |
| `amount` | `2500` (= $25.00) |
| `currency` | `usd` |
| `description` | `Order #12345` |
| `metadata` | `{"order_id": "12345"}` |

### CreateSubscription Example

| Parameter | Value |
|-----------|-------|
| `api_key` | `{{ secrets.stripe_api_key }}` |
| `customer_id` | `cus_ABC123` |
| `price_id` | `price_XYZ789` |
| `quantity` | `1` |

### IssueRefund Example

| Parameter | Value |
|-----------|-------|
| `api_key` | `{{ secrets.stripe_api_key }}` |
| `payment_intent_id` | `pi_ABC123` |
| `amount` | `500` (partial refund of $5.00) |
| `reason` | `requested_by_customer` |

---

## 7. Idempotency

All write operations support idempotency keys to prevent duplicate operations during retries:

- If you provide an `idempotency_key`, it will be used.
- If you leave it empty, the connector auto-generates a deterministic key from the task context.
- Stripe remembers idempotency keys for 24 hours.

---

## 8. Testing with Stripe Test Cards

In test mode, use these card numbers:

| Card Number | Behavior |
|-------------|----------|
| `4242424242424242` | Succeeds |
| `4000000000000002` | Declines (card_declined) |
| `4000000000009995` | Declines (insufficient_funds) |
| `4000000000000069` | Declines (expired_card) |

Use any future expiration date, any 3-digit CVC, and any postal code.

See [Stripe Testing Documentation](https://stripe.com/docs/testing) for more test cards.

---

## 9. Troubleshooting

| Error | What to do |
|-------|------------|
| **StripeAuthError** (invalid API key) | Check that the API key is correct and not revoked. Ensure you're using the secret key (not publishable). |
| **StripeValidationError** | Check required parameters (amount, currency, etc.). Ensure amount is a positive integer. |
| **StripeCardError** (card declined) | The card was declined by the issuer. In test mode, use a test card that succeeds. |
| **StripeRateLimitError** | Too many requests. Wait and retry, or implement backoff. |
| **StripeApiError** | General Stripe API error. Check the error message for details. |

---

## 10. Summary / Quick Reference

1. Create a Stripe account at [stripe.com](https://stripe.com).
2. Get your **Secret key** from **Developers** → **API keys** in the Dashboard.
3. Store the secret key in m8flow secrets.
4. Map the secret to the **api_key** parameter for Stripe connector commands.
5. Use **CreatePaymentIntent**, **CreateCharge**, **CreateSubscription**, **CancelSubscription**, or **IssueRefund** in your workflows.

---

## 11. Links and References

- [Stripe Dashboard](https://dashboard.stripe.com)
- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Testing](https://stripe.com/docs/testing)
- [connector-stripe README](../README.md) (technical reference)
