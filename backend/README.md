# ListingPulse Backend

Multi-tenant SaaS platform for AI-powered real estate marketing. FastAPI + PostgreSQL backend with Claude integration for automated content generation, social media publishing, email campaigns, and branded flyer export.

## Features

- **Multi-tenant** — Per-tenant data isolation via row-level security, JSONB settings, and configurable brand profiles
- **AI Content Generation** — Listing descriptions, social posts, emails, flyers, and event-specific content (open house, price reduction, just sold) via Claude API
- **Brand Profiles** — Customizable voice, vocabulary, avoid-words, and tone per tenant
- **MLS Integration** — Trestle RESO API sync with automatic listing import and change detection
- **Social Media Publishing** — Facebook Pages and Instagram Business posting via Meta Graph API with photo URL validation
- **Email Campaigns** — SendGrid integration with CAN-SPAM compliant footer, batch sending, and campaign tracking
- **Flyer Export** — Branded PPTX and PDF flyer generation with configurable branding (colors, logo, QR codes)
- **Content Export** — Export content as TXT, HTML, DOCX, PPTX, or PDF
- **Lead Management** — Lead capture, activity tracking, and page visit analytics
- **Agent Pages** — Public-facing agent landing pages with SEO metadata
- **Billing** — Stripe integration with usage-based metering and plan management
- **Media Storage** — S3/R2 file upload with presigned URLs

## Tech Stack

- **Framework:** FastAPI with async/await
- **Database:** PostgreSQL with SQLAlchemy async ORM + Alembic migrations
- **Auth:** JWT tokens with CSRF protection
- **AI:** Anthropic Claude API (Sonnet for long-form, Haiku for short-form)
- **Email:** SendGrid API v3
- **Social:** Meta Graph API v21.0
- **Storage:** S3-compatible (Cloudflare R2)
- **Billing:** Stripe with webhooks

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (or .env file)
cp .env.example .env
# Edit .env with your database URL, API keys, etc.

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

| Prefix | Module | Purpose |
|--------|--------|---------|
| `/api/v1/auth` | auth | Login, register, JWT tokens |
| `/api/v1/tenants` | tenants | Tenant CRUD and settings |
| `/api/v1/users` | users | User management |
| `/api/v1/listings` | listings | Listing CRUD and MLS sync |
| `/api/v1/content` | content | AI content generation and export |
| `/api/v1/brand-profiles` | brand_profiles | Brand voice configuration |
| `/api/v1/social` | social | Facebook/Instagram publishing |
| `/api/v1/email-campaigns` | email_campaigns | Email sending and campaign history |
| `/api/v1/leads` | leads | Lead management and activity |
| `/api/v1/agent-pages` | agent_pages | Public agent landing pages |
| `/api/v1/media` | media | File upload and presigned URLs |
| `/api/v1/mls-connections` | mls_connections | MLS API connection management |
| `/api/v1/billing` | billing | Stripe subscriptions and usage |
| `/api/v1/admin` | admin | Platform admin operations |
| `/api/v1/webhooks` | webhooks | Stripe webhook handler |
| `/api/v1/public` | public | Public-facing pages (no auth) |

## Content Types

| Type | Description |
|------|-------------|
| `listing_description` | Full property description |
| `social_instagram` | Instagram post with hashtags |
| `social_facebook` | Facebook post |
| `social_x` | X/Twitter post (short-form) |
| `social_linkedin` | LinkedIn post |
| `email_just_listed` | Just-listed email campaign |
| `email_open_house` | Open house invitation |
| `flyer` | Marketing flyer copy |
| `open_house_invite` | Open house event content |
| `price_reduction` | Price reduction announcement |
| `just_sold` | Just-sold celebration |

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app factory
    config.py            # Pydantic Settings with validators
    api/
      v1/               # All API route modules
      deps.py           # Dependency injection (auth, DB, tenant)
      router.py         # Route registration
    core/
      database.py       # Async SQLAlchemy engine/session
      security.py       # JWT, password hashing, CSRF
    models/             # SQLAlchemy ORM models
    schemas/            # Pydantic request/response schemas
    services/
      ai_service.py     # Claude API integration
      prompt_builder.py # Content-type system prompts
      email_service.py  # SendGrid with CAN-SPAM footer
      social_service.py # Meta Graph API with photo validation
      flyer_service.py  # PPTX + PDF flyer generation
      export_service.py # Multi-format content export
      billing_service.py # Stripe integration
      lead_service.py   # Lead capture and tracking
      media_service.py  # S3/R2 file storage
    integrations/
      mls/              # Trestle RESO API client
  migrations/           # Alembic database migrations
  tests/                # pytest test suite
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific service tests
python -m pytest tests/test_email_service.py -v
python -m pytest tests/test_social_service.py -v
python -m pytest tests/test_flyer_service.py -v
```

## Environment Variables

Key configuration (see `app/config.py` for full list):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis for caching (optional) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `SENDGRID_API_KEY` | SendGrid for email delivery |
| `STRIPE_SECRET_KEY` | Stripe billing |
| `S3_BUCKET` | Media storage bucket |
| `JWT_SECRET` | JWT token signing key |
