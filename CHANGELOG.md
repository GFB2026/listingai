# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Bridge API provider** — dual-provider MLS support (Trestle RESO + Bridge Interactive) with configurable auth and dataset paths
- **Market data enrichment** — tenant-scoped area market data (JSONB) wired into prompt builder and AI service for context-aware content
- **E2E pipeline test** — integration test covering full flow: manual listing, content generation, email campaign, social post, and DB state verification
- **Bridge API schema wiring** — provider validation, settings/dataset fields on MLS connection schemas, `mls_bridge_base_url` config
- **Least-privilege DB role** — `listingai_app` Postgres role with minimal grants (CRUD only, no CREATE/DROP/TRUNCATE) and default privileges for future tables
- **Playwright E2E tests** — 13 browser tests covering auth, listings, content, and navigation flows with network-level API mocking
- 28 new tests for Bridge provider, backward compatibility, market data cascade, prompt injection prevention, and tenant-to-Claude pipeline flow
- Social publishing page, hook, and tests (Facebook + Instagram)
- Email campaigns page with send form and campaign history
- User/team management page with inline CRUD
- Media upload component with drag-and-drop and preview
- Content library actions: copy, regenerate, delete, status filter
- Brand profile edit/delete with inline editing
- MLS connection edit (`useUpdateMlsConnection` hook + inline form)
- Manual listing create form with collapsible details
- 3 event content types and `event_details` field in content generator
- PPTX and flyer PDF added to export menu
- Sidebar navigation updated with Social, Email, Team items
- 5 missing listing fields added to TypeScript interfaces

### Changed
- Billing Upgrade button wired to `POST /billing/subscribe`
- Docker compose uses `.env` instead of `.env.example`; Docker service names override localhost connection strings

### Fixed
- Docker compose networking for container-to-container communication
- Broken View link in content library

## [1.5.0] - 2026-02-25

Cross-pollination release -- gor-marketing features ported to ListingAI SaaS platform.

### Added
- **Event prompts** — open_house_invite, price_reduction, just_sold content types with stricter anti-cliche rules
- **Email service** — SendGrid integration with BCC personalizations, campaign tracking, and CAN-SPAM footer
- **Social service** — Meta Graph API posting (Facebook + Instagram) with photo URL validation and post tracking
- **Flyer service** — PPTX and PDF flyer builders with parameterized BrandingConfig
- **API endpoints** — `/api/v1/social` (post, status) and `/api/v1/email-campaigns` (send, list, status) with full schemas
- Word scrubbing (`_scrub_avoid_words()`) in AI service for cliche prevention
- Agent contact fields (email, phone) and sale metadata (previous_price, close_price, close_date) on Listing model
- `event_details` parameter wired through API, AIService, and PromptBuilder
- ContentType enum expanded with 3 event types (13 total, was 10)
- Pydantic field validators for URL/email/enum format on Settings
- Flyer export wiring in export endpoint for PPTX/PDF formats
- 80 new service tests: email_service (15), social_service (17), flyer_service (13), email campaigns API (20+), social API (15+)
- Backend README with comprehensive documentation
- Alembic migrations for `email_campaigns` and `social_posts` tables, plus agent contact and sale fields

### Security
- RLS hardening migration for 5 previously unprotected tables (agent_pages, leads, email_campaigns, social_posts, page_visits)
- FORCE ROW LEVEL SECURITY applied on all 11 tenant-scoped tables
- Restricted `listingai_app` DB role created with table-level grants
- 6 new Stripe webhook security tests (signature verification, Redis unavailable, missing signature)

### Fixed
- fpdf2 deprecation: `txt=` parameter renamed to `text=` in flyer_service

### Changed
- Config validation expanded with Pydantic validators for URL/email/enum formats

## [1.4.0] - 2026-02-24

Lead tracking and agent landing pages release.

### Added
- **Agent Pages** -- public landing pages per agent with custom slug, headline, bio, photo, and theme
- **Lead Capture** -- public form submission with UTM attribution, session tracking, and IP/user-agent capture
- **Lead Pipeline** -- full CRUD with pipeline statuses (new, contacted, showing, under_contract, closed, lost)
- **Lead Activities** -- timeline of notes, status changes, and interactions per lead
- **Lead Analytics** -- summary by status/source/agent, pipeline funnel with conversion rates, total closed value
- **Visit Tracking** -- anonymous page visit recording with UTM and referrer attribution
- **Public API** -- unauthenticated endpoints for landing pages, lead submission, visit tracking, and link config
- **Auto-generate content** -- Celery task auto-generates all marketing content types when MLS sync detects new listings
- **Kanban Board UI** -- drag-and-drop lead pipeline board on the dashboard
- **Lead Detail Panel** -- full lead view with contact info, attribution, and activity timeline
- **Analytics Charts** -- source breakdown, funnel visualization, agent leaderboard
- **Agent Hero & Property Hero** -- public-facing agent profile and listing detail components
- **Lead Capture Form** -- public form with validation, UTM/session capture, and success state
- **Frontend test suite** -- 119 tests across 19 files with Vitest, React Testing Library, and MSW
- 81 new backend tests across 5 new test files (test_agent_pages_api, test_leads_api, test_public_api, test_content_auto_gen, test_admin_api)
- 99 new frontend tests across 13 new test files
- New hooks: `useLeads`, `useAgentPages`, `useLeadAnalytics` with full mutation support and toast notifications
- Public Axios instance (`public-api.ts`) for unauthenticated API calls
- UTM parameter capture utility (`utm.ts`) with session storage

### Security
- Removed MinIO default minioadmin credentials; require explicit S3 keys
- Replaced PGPASSWORD env var with .pgpass file in backup container
- Added test build stage to Dockerfile; removed root user from test compose
- Brand profile `is_default` race condition fixed with atomic UPDATE + partial unique index
- Content credit timing gap fixed: re-check + track usage per variant

### Fixed
- asyncpg type inference for `func.coalesce` with string literals in analytics queries
- Production Docker health checks: `localhost` to `127.0.0.1` for frontend wget, `/health/ready` to `/health/live` for backend liveness
- MLS sync watermark only advances when zero errors occur; added flush()
- Test deadlocks under coverage resolved by removing session-scoped engine
- 3 failing CI jobs: backend-lint, backend-security, frontend-build
- TypeScript error in frontend test setup
- Docker test environment: 304/304 tests passing in containers
- Docker-security CI: added .trivyignore for starlette CVEs
- Staging deployment: Docker Compose overlays, frontend build args, type errors

### Changed
- Backend test count: 312 to 393 (37 test files)
- Frontend test count: 0 to 218 (32 test files), 76% coverage
- FastAPI upgraded 0.115.6 to 0.133.0 (resolves CVE-2025-62727 and CVE-2025-54121)
- 17 backend dependencies bumped to latest stable versions
- 13 frontend dependencies bumped to latest stable versions
- CSRF middleware exempts `/api/v1/public/` prefix
- Rate limiter adds public endpoint limits (leads: 10/min, visits: 30/min, general public: 60/min)
- Sidebar updated with Leads, Lead Analytics, and Agent Pages navigation
- Dashboard page includes lead stats and quick actions
- `listing_service.upsert_from_mls` returns `(listing, is_new)` tuple for accurate tracking

### Database
- New tables: `agent_pages`, `leads`, `lead_activities`, `page_visits`
- RLS policies on all new tenant-scoped tables
- Indexes: tenant+agent, tenant+status, tenant+created_at on leads; agent+created_at on page_visits
- Unique constraints: tenant+slug and tenant+user on agent_pages
- New migration: `d4e5f6a7b8c9` brand_profile_unique_default partial unique index

## [1.3.0] - 2026-02-23

Near-complete coverage release -- 97% backend test coverage.

### Added
- 30 new backend tests across 1 new + 6 extended test files (total: 304 tests, 31 files)
- `test_csrf.py` -- CSRF rejection without header, mismatch, valid match, Bearer skip, cookie auto-set
- Extended `test_rate_limiter.py` -- sliding window allow/reject, path-specific limits, prefix limits, fail-open on Redis/Connection/OS errors, 429 with/without oldest entry
- Extended `test_health.py` -- Postgres/Redis/Celery readiness failures, metrics endpoint, CircuitBreakerOpen 503 handler
- Extended `test_auth.py` -- refresh via cookie, refresh inactive user, logout blacklists both cookie tokens
- Extended `test_listings_api.py` -- property_type filter, bathrooms filter, sync queued/throttled/Redis-unavailable
- Extended `test_stripe_webhooks.py` -- invalid payload, signature verification error, duplicate event dedup, unknown price_id
- Extended `test_circuit_breaker.py` -- fixed 3 flaky timing-dependent tests (deterministic time backdating)

### Fixed
- Coverage tracking for ASGI transport: added `concurrency = ["greenlet", "thread"]` to coverage config (jumped from 85% to 94% with zero new tests)
- Flaky circuit breaker tests: replaced `time.sleep()` with deterministic `_last_failure_time` backdating

### Changed
- Backend test coverage increased from 85% to 97% (348 to 65 missed statements)

## [1.2.0] - 2026-02-23

Deep coverage release -- 85% backend test coverage.

### Added
- 53 new backend tests across 3 new + 5 extended test files (total: 274 tests, 30 files)
- `test_listing_service.py` -- ListingService.upsert_from_mls create, update, skip-none paths
- `test_adapters.py` -- PropertyAdapter/MediaAdapter: ViewDescription list/string, Appliances, GarageSpaces, list_date parsing, status/type mapping
- `test_redis.py` -- RedisPool initialize, client error, close
- Extended `test_ai_service.py` -- brand profile lookup, APIConnectionError, APIStatusError 5xx/4xx, hashtag extraction, circuit breaker half-open
- Extended `test_worker_tasks.py` -- Celery wrapper correlation_id, SoftTimeLimitExceeded, retry for all 3 task files; listing-not-found skip; download error resilience
- Extended `test_media_api.py` -- MediaService.upload(), no-filename fallback, content-length rejection, chunk size limit
- Extended `test_export_service.py` -- PDF export, PDF XSS safety
- Extended `test_billing_service.py` -- Stripe InvalidRequestError, general StripeError on subscription create

### Changed
- Backend test coverage increased from 81% to 85% (449 to 348 missed statements)
- 8 source files now at 100% coverage: ai_service, billing_service, export_service, listing_service, media_service, content_batch, media_process, mls_sync

## [1.1.0] - 2026-02-23

Test coverage milestone release.

### Added
- 74 new backend tests across 9 new test files (total: 221 tests, 27 files)
- Test coverage for MLS connections API, sync engine, worker tasks, content endpoints, RESO client, media upload/presigned URLs, tenants API, Fernet encryption, and billing service
- Testing section in README.md with coverage stats and commands

### Fixed
- UUID-to-string serialization in `MLSConnectionResponse` and `TenantResponse` Pydantic schemas (added `field_serializer` for `id` field)

### Changed
- Backend test coverage increased from 67% to 81% (785 to 449 missed statements)

## [1.0.0] - 2026-02-23

Production-ready release with comprehensive hardening across security, reliability, observability, and CI/CD.

### Security
- JWT token blacklisting on logout via Redis with automatic TTL expiry
- CSRF double-submit cookie pattern on all state-changing endpoints
- Login brute-force protection (5 attempts per 15 min, Redis-backed)
- Fernet encryption for MLS credentials stored at rest
- Row-Level Security (RLS) on all tenant-scoped PostgreSQL tables
- Security headers middleware (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- XSS prevention in content export (HTML-escaping before embedding in HTML/PDF)
- Rate limiting on expensive AI endpoints (5/min generate, 2/5min batch)
- Production config validation (fails fast if required secrets are missing)
- pip-audit, bandit, npm audit, and Trivy container scanning in CI
- Next.js security headers and tightened image remote patterns

### Added
- Backend auth: JWT + refresh tokens, RBAC (broker/admin/agent roles), token blacklist
- RESO/Trestle MLS integration with encrypted credentials and incremental sync
- Circuit breaker on AI service with configurable failure threshold and recovery timeout
- Content export to TXT, HTML, DOCX, PDF with format validation
- Stripe billing with subscription plans, usage metering, and webhook handlers
- Nginx reverse proxy with TLS 1.2/1.3, rate limiting zones, upstream health checks
- Certbot automated Let's Encrypt certificate renewal (every 12h)
- Daily PostgreSQL backup with 7-day daily + 4-week weekly rotation
- Docker Compose overlays: dev, production, staging
- Structured logging via structlog with request ID correlation
- Prometheus metrics endpoint, alert rules, and Grafana pre-provisioned dashboard
- Sentry integration (backend + frontend) with configurable DSN
- k6 load test scripts with smoke/load/stress profiles
- Deployment runbook covering first deploy, updates, rollback, backup/restore, TLS, monitoring, incident response
- GitHub Actions CI/CD pipeline: lint, test (60% coverage gate), security scan, frontend build, Docker image scan
- Dependabot for pip, npm, and GitHub Actions updates
- Pre-commit hooks (trailing whitespace, ruff, ESLint)
- 147 backend tests across 16 test files, all passing

### Changed
- Celery tasks use exponential backoff with jitter (replacing fixed delays)
- Soft and hard time limits on all Celery tasks
- Docker init process (tini) for proper signal forwarding and zombie reaping
- Production resource limits (memory/CPU) on all Docker services
- Health checks on all production services

### Database
- Alembic migration chain: initial schema, constraints + RLS, performance indexes, updated_at columns
- Performance indexes on users, listings, content, and brand profiles
- CHECK constraints on content status enum, usage event types
- NOT NULL constraints hardened across schema

### Frontend
- Zero TypeScript `any` types across entire codebase
- Typed React Query hooks with AbortSignal propagation
- Mutation error handlers with toast notifications
- Client-side password validation with real-time feedback
- Error boundaries on all dashboard route segments
- Per-endpoint timeout presets (30s default, 120s generate, 60s upload)

## [0.1.0] - 2026-02-19

Initial scaffold.

### Added
- FastAPI backend with async SQLAlchemy, JWT auth, multi-tenant data model
- Next.js 15 frontend with App Router, React Query, TailwindCSS 4
- Claude AI content generation with three-layer prompt system (system + brand voice + listing data)
- MLS integration via RESO Web API (Trestle)
- Celery worker for async MLS sync and batch content generation
- Docker Compose development environment
- Brand voice profiles for customizing AI output
- Stripe billing integration
- MinIO (S3-compatible) media storage
- 10 content types: listing description, social media (Facebook, Instagram, LinkedIn), email campaign, flyer copy, video script
