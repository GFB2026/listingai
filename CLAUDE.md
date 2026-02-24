# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ListingAI is a multi-tenant SaaS platform that generates AI-powered real estate marketing content (descriptions, social posts, emails, flyers, video scripts) from MLS listing data. It uses Claude for content generation, with a three-layer prompt system (system prompt + brand voice + listing data).

**Version:** 1.3.0

## Tech Stack

- **Backend:** Python 3.12, FastAPI 0.133, SQLAlchemy 2.0.46 (async), Celery 5.6, Redis 7, PostgreSQL 16
- **Frontend:** Next.js 15 (App Router), React 19, TypeScript 5.9, TailwindCSS 4, React Query 5, Zustand
- **Infrastructure:** Docker Compose, MinIO (S3-compatible), Alembic migrations
- **AI:** Anthropic SDK (Sonnet 4.5 for most content, Haiku 4.5 for short-form like tweets)

## Testing

### Backend
- **306 tests** across 31 test files, all passing
- **97% code coverage** (2302/2367 statements) — CI gate is 60%
- Tests use mocked external services (no real API keys, Stripe, S3, or MLS calls)
- `asyncio_mode = "auto"` with `asyncio_default_fixture_loop_scope = "function"` — async tests auto-detected
- Coverage report: `cd backend && pytest --cov=app --cov-report=term-missing`

### Frontend
- **119 tests** across 19 test files (Vitest + React Testing Library + MSW)
- Tests cover hooks, components, API client, auth context, and utilities

### Docker Tests
- `make docker-test` runs the full backend suite inside Docker (postgres + redis)
- Uses `docker/docker-compose.test.yml` overlay with Docker service hostnames
- Test database auto-created via `docker/scripts/init-test-db.sql`

## Common Commands

### Docker (full stack)
```bash
make up           # Start all services (postgres, redis, minio, backend, worker, beat, frontend)
make down         # Stop all services
make build        # Rebuild Docker images
make logs         # Tail logs for all services
make prod-up      # Start production stack (nginx, TLS, monitoring, backups)
make prod-down    # Stop production stack
make prod-build   # Build production images
make prod-logs    # Tail production logs
make prod-migrate # Run migrations in production container
```

### Staging
```bash
make staging-up     # Start staging stack (reduced resources, no TLS/monitoring)
make staging-down   # Stop staging stack
make staging-build  # Build staging images
```

### Load Testing
```bash
make load-test                # k6 smoke test (5 VUs, 1 min)
make load-test PROFILE=load   # 50 VUs ramp over 9 min
make load-test PROFILE=stress # 100 VUs ramp over 12 min
```

### Backend
```bash
make backend      # Start FastAPI dev server (uvicorn --reload on :8000)
make worker       # Start Celery worker
make beat         # Start Celery Beat scheduler
make test         # Run all tests (backend + frontend)
make test-cov     # Run backend tests with coverage
make docker-test  # Run backend tests inside Docker (postgres + redis)
make lint         # ruff check + npm lint
make fmt          # ruff format + npm format
```

### Running a single test
```bash
cd backend && pytest tests/test_file.py -v                       # one file
cd backend && pytest tests/test_file.py::test_function -v        # one function
cd backend && pytest tests/test_file.py::TestClass::test_method  # one method
cd backend && pytest -k "keyword" -v                             # by name match
cd backend && pytest -m slow -v                                  # by marker (slow, integration)
```

Async tests auto-detected — `asyncio_mode = "auto"` in `pyproject.toml`.

### Frontend
```bash
make frontend          # Start Next.js dev server on :3000
make frontend-install  # npm install
make frontend-test     # Run frontend tests (vitest)
make frontend-test-cov # Run frontend tests with coverage
```

### Database
```bash
make migrate                    # Apply all pending Alembic migrations
make migrate-new MSG="desc"     # Generate new migration
make migrate-down               # Rollback one migration
make db-shell                   # Open psql session
```

Alembic commands run from `backend/`:
```bash
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"
```

Migration chain: `cbe7f3435501` (initial schema) → `a1b2c3d4e5f6` (constraints + RLS) → `b2c3d4e5f6a7` (performance indexes) → `c3d4e5f6a7b8` (updated_at columns)

## Architecture

### Backend Structure (`backend/app/`)

**Request flow:** Client → CORS → SecurityHeaders → RateLimit → RequestLogging → Router → Dependencies (auth, tenant DB) → Endpoint → Service → Database/External API

- **`api/deps.py`** — Dependency injection: `get_db()`, `get_current_user()`, `get_tenant_db()` (sets RLS context), `require_role()` factory
- **`api/v1/`** — Route handlers. All endpoints under `/api/v1/` prefix. Includes DELETE endpoints for content, brand profiles, and users (with self-delete prevention)
- **`core/`** — Security primitives: JWT (HS256 with JTI for blacklisting), bcrypt passwords, Fernet encryption for MLS credentials, Redis-backed token blacklist, login brute-force protection
- **`middleware/`** — Rate limiting (sliding window via Redis sorted sets, per-path limits including 5/min for content generation, 2/5min for batch), security headers (CSP, HSTS), structured request logging with request IDs
- **`models/`** — SQLAlchemy async models. All tenant-scoped models use `TenantMixin` and `TimestampMixin`. Root entity is `Tenant`, everything cascades from it
- **`services/`** — Business logic layer. `PromptBuilder` assembles three-layer prompts. `AIService` calls Claude (with circuit breaker + Prometheus state gauge). `ContentService` handles CRUD + usage tracking. `MediaService` wraps S3/MinIO. `ExportService` exports to TXT/HTML/DOCX/PDF with XSS-safe HTML escaping. `BillingService` wraps Stripe with error handling
- **`integrations/mls/`** — RESO Web API client (OAuth2 client credentials), property/media adapters that normalize RESO fields to internal format, watermark-based incremental sync engine
- **`workers/`** — Celery tasks: MLS sync (periodic every 30 min), batch content generation, photo downloading. Tasks bridge async/sync with `asyncio.run()`

### Multi-Tenancy

Tenant isolation uses both application-level filtering (`tenant_id` FK on all data models) and PostgreSQL Row-Level Security (session variable `app.current_tenant_id` set via `get_tenant_db()` dependency). Tenant deletion cascades to all owned entities.

### Authentication

JWT tokens (access: 30 min, refresh: 7 days) delivered via httpOnly cookies. Backend accepts tokens from cookies or Bearer header. Token blacklisting on logout via Redis with TTL. Auto-refresh handled by Axios interceptor on frontend (401 → refresh → retry).

### Request Tracing

Request middleware generates an 8-char `request_id` per request, bound via `structlog.contextvars.bind_contextvars()` and returned in the `X-Request-ID` response header. Celery tasks accept a `correlation_id` parameter to propagate the originating request ID into worker logs. The frontend Axios instance attaches `X-Request-ID: crypto.randomUUID()` to all outbound API calls.

### Celery Task Resilience

All Celery tasks use exponential backoff with jitter (`retry_backoff=True`, `retry_jitter=True`) and per-task `retry_backoff_max` caps (300–900s). Tasks have both `soft_time_limit` (raises `SoftTimeLimitExceeded`) and `time_limit` (hard kill). Worker config: `task_acks_late=True`, `worker_prefetch_multiplier=1`, `task_reject_on_worker_lost=True`.

### Frontend Structure (`frontend/src/`)

- **`app/(auth)/`** — Login/register pages (unauthenticated routes)
- **`app/(dashboard)/`** — Authenticated routes: listings browser, listing detail, content generation, brand profiles, MLS settings, billing
- **`lib/api.ts`** — Axios instance with `withCredentials: true`, base URL from `NEXT_PUBLIC_API_URL`, request ID interceptor, CSRF token interceptor, 401 auto-refresh interceptor, per-endpoint `TIMEOUTS` presets
- **`lib/auth.tsx`** — React Context for auth state, login/register/logout methods
- **`lib/providers.tsx`** — QueryClient (60s staleTime, 1 retry) + AuthProvider
- **`hooks/`** — React Query hooks: `useListings()`, `useListing()`, `useContent()`, `useGenerate()`, `useMlsConnections()`
- **`components/`** — `content-generator/` (TipTap editor, tone selector, brand voice), `listings/` (card, grid, filters), `layout/` (sidebar, topbar), `ui/` (base components via Radix UI)

### Key Entity Relationships

```
Tenant → Users, Listings, BrandProfiles, MLSConnections, Content → ContentVersions
```

`UsageEvent` tracks content generation, MLS sync, and export events for billing (monthly credit limits per tenant plan).

### Production Infrastructure (`docker/`)

**Compose overlays:** Base `docker-compose.yml` + `docker-compose.prod.yml` (production), `docker-compose.staging.yml` (staging), or `docker-compose.test.yml` (testing).

Production stack adds:
- **Nginx** — Reverse proxy with TLS 1.2/1.3, rate limiting (auth:5r/s, api:30r/s, general:60r/s), upstream health checks
- **Certbot** — Automated Let's Encrypt certificate renewal (every 12h)
- **Backup** — Daily `pg_dump` with 7-day daily + 4-week weekly rotation (see `docker/scripts/backup.sh`)
- **Prometheus** — Metrics scraping from `/metrics` endpoint, 30-day retention, alert rules in `docker/monitoring/alerts.yml`
- **Grafana** — Pre-provisioned dashboard ("ListingAI Backend") with request rate, latency percentiles, error rate, heatmap, status distribution

Deployment runbook: `docs/deployment-runbook.md`

### CI/CD (`.github/workflows/ci.yml`)

5 jobs run on push to main/master and PRs to main:
- **backend-lint** — Ruff linting (pinned to ruff==0.8.4) with pip cache
- **backend-test** — pytest with PostgreSQL + Redis services, 60% coverage gate, coverage XML artifact upload
- **backend-security** — pip-audit (dependency vulnerabilities, with `--ignore-vuln` for unfixable transitive CVEs) + bandit (SAST)
- **frontend-build** — ESLint + Vitest + TypeScript strict check + npm audit + Next.js build, npm cache
- **docker-security** — Trivy container image scanning for CRITICAL/HIGH vulnerabilities with `.trivyignore` (runs after backend-test + frontend-build)

Dependabot configured for pip (weekly), npm (weekly), and GitHub Actions (monthly).

## Environment

Copy `.env.example` to `.env`. Key variables:
- `DATABASE_URL` / `DATABASE_URL_SYNC` — Async (asyncpg) and sync (psycopg2) PostgreSQL URLs
- `REDIS_URL` / `CELERY_BROKER_URL` — Redis for cache (db 0) and Celery broker (db 1)
- `ANTHROPIC_API_KEY` — Claude API access
- `ENCRYPTION_KEY` — Fernet key for encrypting MLS credentials at rest
- `NEXT_PUBLIC_API_URL` — Frontend's backend URL (default `http://localhost:8000`)

## Deferred Frontend Major Bumps

These major-version upgrades were intentionally deferred (Dependabot PRs closed 2026-02-24). Each requires migration work:

- **tailwind-merge 2→3** — changes theme scale keys, removes validators, new config format
- **@tiptap/react + @tiptap/starter-kit 2→3** — renames API, needs `immediatelyRender: false` for SSR
- **eslint-config-next 15→16** — requires flat config migration (`.eslintrc.json` → `eslint.config.mjs`)
- **@sentry/nextjs 8→10** — two major jumps, API changes

## Conventions

- Backend uses async/await throughout (asyncpg, httpx, async SQLAlchemy sessions)
- Pydantic v2 schemas with `validation_alias` for ORM field mapping
- Structured logging via structlog with context variables (request_id, tenant_id)
- Rate limiter and login protection fail open if Redis is unavailable
- Celery tasks use `asyncio.run()` to bridge sync Celery with async application code
- Frontend path alias: `@/*` maps to `./src/*`
- Dependencies split: `requirements.txt` (prod only), `requirements-dev.txt` (adds pytest, ruff). CI uses dev; Docker uses prod
- Ruff config in `backend/pyproject.toml`: line-length 100, rules E/W/F/I/N/UP/B/S/T20/SIM
- Pre-commit hooks enforce trailing whitespace, ruff lint+format (backend), ESLint (frontend)
- Node version pinned to 20 via `frontend/.nvmrc` and `package.json` engines
- Docker images use tini as init process for proper signal forwarding
- Production config validates all required secrets on startup (Stripe keys, JWT, Anthropic, encryption, S3)
- Frontend is fully typed — zero `any` types across all TypeScript files
- All React Query hooks propagate AbortSignal for request cancellation on unmount
- All mutations include `onError` toast notifications for user feedback
