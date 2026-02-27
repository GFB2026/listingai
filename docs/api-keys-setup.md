# ListingAI Production API Keys Setup

Checklist for obtaining and configuring every external service key required for production deployment.

Reference: all env vars are loaded via `backend/app/config.py` (`Settings` class). The app will refuse to start in production if required keys are missing.

---

## 1. Stripe (Billing)

### Sign up
- [ ] Create an account at [dashboard.stripe.com](https://dashboard.stripe.com)
- [ ] Activate your account (complete identity verification so you can accept live payments)

### Get API keys
- [ ] Go to **Developers > API keys** in the Stripe dashboard
- [ ] Copy the **Secret key** (starts with `sk_live_`) and set it as `STRIPE_SECRET_KEY`
- [ ] Copy the **Publishable key** (starts with `pk_live_`) and set it as `STRIPE_PUBLISHABLE_KEY`

### Create products and prices
The app maps three price IDs to plans (see `billing_service.py` and `webhooks.py`):

| Plan | Monthly limit | Env var |
|------|---------------|---------|
| Starter | 200 credits | `STRIPE_PRICE_ID_STARTER` |
| Professional | 1,000 credits | `STRIPE_PRICE_ID_PROFESSIONAL` |
| Enterprise | 10,000 credits | `STRIPE_PRICE_ID_ENTERPRISE` |

- [ ] Go to **Products** in the Stripe dashboard
- [ ] Create a product for each plan with a recurring monthly price
- [ ] Copy each price ID (starts with `price_`) into the corresponding env var

### Set up the webhook endpoint
- [ ] Go to **Developers > Webhooks > Add endpoint**
- [ ] Set the endpoint URL to `https://your-domain.com/api/v1/webhooks/stripe`
- [ ] Subscribe to these events:
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`
- [ ] After creating the endpoint, copy the **Signing secret** (starts with `whsec_`) and set it as `STRIPE_WEBHOOK_SECRET`

### Verify
- [ ] Use Stripe CLI or the dashboard's "Send test webhook" to confirm the endpoint returns `200`

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_STARTER=price_...
STRIPE_PRICE_ID_PROFESSIONAL=price_...
STRIPE_PRICE_ID_ENTERPRISE=price_...
```

---

## 2. Anthropic (AI Content Generation)

### Sign up
- [ ] Create an account at [console.anthropic.com](https://console.anthropic.com)
- [ ] Add a payment method under **Settings > Billing**

### Get API key
- [ ] Go to **Settings > API Keys > Create Key**
- [ ] Copy the key (starts with `sk-ant-`) and set it as `ANTHROPIC_API_KEY`

### Configure usage limits
- [ ] Go to **Settings > Limits** and set a monthly spend cap appropriate for your traffic
- [ ] The app uses two models (configured in `config.py`):
  - Default: `claude-sonnet-4-5-20250929` (`claude_model_default`)
  - Short-form: `claude-haiku-4-5-20251001` (`claude_model_short`)

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## 3. SendGrid (Email Delivery)

### Sign up
- [ ] Create an account at [sendgrid.com](https://sendgrid.com)
- [ ] Complete sender identity verification

### Get API key
- [ ] Go to **Settings > API Keys > Create API Key**
- [ ] Grant **Full Access** or at minimum **Mail Send** permissions
- [ ] Copy the key (starts with `SG.`) and set it as `SENDGRID_API_KEY`

### Configure sender identity
- [ ] Set `SENDGRID_DEFAULT_FROM_EMAIL` to the address emails will be sent from (e.g., `noreply@yourdomain.com`)
- [ ] Set `SENDGRID_DEFAULT_FROM_NAME` to the display name (e.g., `ListingAI`)
- [ ] These are validated at startup -- `SENDGRID_DEFAULT_FROM_EMAIL` must be a valid email format

### Authenticate your sending domain (DNS records)
- [ ] Go to **Settings > Sender Authentication > Authenticate Your Domain**
- [ ] Select your DNS provider and follow the steps
- [ ] Add the three CNAME records SendGrid provides to your domain's DNS:
  ```
  em1234.yourdomain.com  CNAME  u1234567.wl123.sendgrid.net
  s1._domainkey.yourdomain.com  CNAME  s1.domainkey.u1234567.wl123.sendgrid.net
  s2._domainkey.yourdomain.com  CNAME  s2.domainkey.u1234567.wl123.sendgrid.net
  ```
- [ ] Click **Verify** in the SendGrid dashboard after DNS propagation (up to 48 hours, usually minutes)
- [ ] Optionally set up link branding under **Sender Authentication > Link Branding**

### Verify
- [ ] The `EmailService` in `email_service.py` checks `is_configured` (API key non-empty) before sending
- [ ] Send a test email via the app or directly via the SendGrid API to confirm delivery

```
SENDGRID_API_KEY=SG....
SENDGRID_DEFAULT_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_DEFAULT_FROM_NAME=ListingAI
```

> Note: `SENDGRID_DEFAULT_FROM_EMAIL` and `SENDGRID_DEFAULT_FROM_NAME` map to the `from` field on outgoing emails. Per-tenant overrides can be passed at send time through `EmailService.__init__()`.

---

## 4. Sentry (Error Tracking)

### Sign up
- [ ] Create an account at [sentry.io](https://sentry.io)

### Create a project
- [ ] Click **Create Project**
- [ ] Select **Python** as the platform and **FastAPI** as the framework
- [ ] Name it `listingai-backend` (or similar)

### Get DSN
- [ ] After project creation, Sentry shows the DSN on the setup page
- [ ] Alternatively: go to **Settings > Projects > listingai-backend > Client Keys (DSN)**
- [ ] Copy the DSN (format: `https://<key>@<org>.ingest.sentry.io/<project-id>`) and set it as `SENTRY_DSN`

### Configure
- [ ] `SENTRY_TRACES_SAMPLE_RATE` controls the percentage of requests traced for performance monitoring. Default is `0.1` (10%). Set lower for high-traffic production, higher for staging.
- [ ] The app initializes Sentry in `main.py` with `send_default_pii=False` -- no user data is sent to Sentry
- [ ] Sentry is optional: if `SENTRY_DSN` is empty, `sentry_sdk.init()` is skipped entirely

```
SENTRY_DSN=https://abc123@o456.ingest.sentry.io/789
SENTRY_TRACES_SAMPLE_RATE=0.1
```

---

## 5. S3 / MinIO (Media Storage)

### Option A: AWS S3
- [ ] Create an S3 bucket (e.g., `listingai-media`)
- [ ] Create an IAM user with `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:ListBucket` on the bucket
- [ ] Copy the access key and secret key

### Option B: Self-hosted MinIO (default in Docker stack)
- [ ] The Docker Compose stack includes MinIO by default
- [ ] Generate strong credentials for production (do not use the dev defaults)

```
S3_ENDPOINT_URL=https://s3.amazonaws.com    # or http://minio:9000 for self-hosted
S3_ACCESS_KEY=AKIA...
S3_SECRET_KEY=...
S3_BUCKET_NAME=listingai-media
S3_REGION=us-east-1
```

---

## 6. Meta Graph API (Social Media -- Per-Tenant)

> These are **not** global env vars. Each tenant stores their own Meta credentials in `tenant.settings` JSONB. This section is for tenant onboarding documentation.

### Prerequisites
- [ ] A Facebook Page (the tenant's business page)
- [ ] The Page must be connected to an Instagram Business account (if Instagram posting is desired)

### Get a Page Access Token
- [ ] Go to [developers.facebook.com](https://developers.facebook.com) and create a Meta App (type: Business)
- [ ] Add the **Facebook Login** and **Pages API** products
- [ ] Under **Tools > Graph API Explorer**:
  - Select the app
  - Add permissions: `pages_manage_posts`, `pages_read_engagement`, `instagram_basic`, `instagram_content_publish`
  - Generate a **User Access Token**
  - Exchange it for a **long-lived token**: `GET /oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}`
  - Get the **Page Access Token**: `GET /me/accounts?access_token={long-lived-user-token}`
  - The Page Access Token from this step is permanent (does not expire)

### Get the Page ID and Instagram User ID
- [ ] The `GET /me/accounts` response includes `id` (this is the Facebook Page ID)
- [ ] To get the Instagram Business User ID: `GET /{page-id}?fields=instagram_business_account&access_token={page-token}`
- [ ] The `instagram_business_account.id` value is the Instagram User ID

### Store in tenant settings
These values go into the tenant's `settings` JSONB column, not the `.env` file:

```json
{
  "social": {
    "page_access_token": "EAA...",
    "facebook_page_id": "123456789",
    "instagram_user_id": "987654321"
  }
}
```

The `SocialService.from_tenant_settings()` factory reads these at post time. If `page_access_token` or `facebook_page_id` is missing, social posting is silently disabled for that tenant.

---

## 7. Application Secrets (Not External APIs)

These are generated values, not obtained from third-party services:

- [ ] `APP_SECRET_KEY` -- generate with: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] `JWT_SECRET_KEY` -- generate with: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] `ENCRYPTION_KEY` -- generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- [ ] `POSTGRES_PASSWORD` -- generate a strong random password

```
APP_SECRET_KEY=<random-64-char-urlsafe>
JWT_SECRET_KEY=<random-64-char-urlsafe>
ENCRYPTION_KEY=<fernet-key>
POSTGRES_PASSWORD=<strong-random-password>
```

---

## Production Startup Validation

The `get_settings()` function in `config.py` enforces that these keys are non-empty when `APP_ENV=production` or `APP_ENV=staging`:

| Variable | Required in prod? |
|----------|-------------------|
| `APP_SECRET_KEY` | Yes |
| `JWT_SECRET_KEY` | Yes |
| `ANTHROPIC_API_KEY` | Yes |
| `ENCRYPTION_KEY` | Yes |
| `S3_ACCESS_KEY` | Yes |
| `S3_SECRET_KEY` | Yes |
| `STRIPE_SECRET_KEY` | Yes |
| `STRIPE_PUBLISHABLE_KEY` | Yes |
| `STRIPE_WEBHOOK_SECRET` | Yes |
| `SENDGRID_API_KEY` | Yes |
| `SENDGRID_DEFAULT_FROM_EMAIL` | Yes |
| `SENTRY_DSN` | No (but strongly recommended) |
| `GRAFANA_ADMIN_PASSWORD` | No (defaults to `changeme`) |

If any required key is missing, the app raises a `ValueError` at startup with a list of all missing keys.
