# ListingAI - AI-Powered Real Estate Content Engine

> **Version 1.1.0** | 221 tests | 81% coverage | Production-ready

Generate listing descriptions, social media posts, email campaigns, flyer copy, and video scripts from MLS data using Claude AI.

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start infrastructure (Postgres, Redis, MinIO)
make up

# 3. Run database migrations
make migrate

# 4. Install frontend dependencies
make frontend-install

# 5. Start backend (terminal 1)
make backend

# 6. Start frontend (terminal 2)
make frontend

# 7. Start worker (terminal 3)
make worker
```

Visit http://localhost:3000 to register your brokerage and start generating content.

## Architecture

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, FastAPI 0.115, SQLAlchemy 2 (async), Celery 5 |
| **Frontend** | Next.js 15 (App Router), React 19, TypeScript 5.7, TailwindCSS 4 |
| **AI** | Anthropic Claude (Sonnet 4.5 for long-form, Haiku 4.5 for short-form) |
| **Database** | PostgreSQL 16 with Row-Level Security |
| **Cache/Broker** | Redis 7 |
| **Storage** | S3-compatible (MinIO in dev) |
| **Billing** | Stripe |
| **Monitoring** | Prometheus + Grafana |
| **Reverse Proxy** | Nginx with TLS 1.2/1.3 |

## Project Structure

```
listingai/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/v1/       # Route handlers (listings, content, auth, billing, MLS, admin)
│   │   ├── core/         # Security (JWT, encryption, token blacklist, login protection)
│   │   ├── middleware/    # Rate limiter, security headers, request logging
│   │   ├── models/       # SQLAlchemy models with tenant isolation
│   │   ├── services/     # Business logic (AI, content, media, billing, export)
│   │   ├── integrations/ # MLS/RESO client + sync engine
│   │   └── workers/      # Celery tasks (MLS sync, batch generation, photo processing)
│   ├── migrations/       # Alembic migrations
│   └── tests/
├── frontend/             # Next.js application
│   └── src/
│       ├── app/          # App Router pages (auth, dashboard, listings, content, brand)
│       ├── components/   # Content generator, listings, layout, UI primitives
│       ├── hooks/        # React Query hooks (listings, content, MLS, generate)
│       └── lib/          # API client, auth context, providers, utilities
├── docker/               # Docker configuration
│   ├── monitoring/       # Prometheus alerts, Grafana dashboards
│   ├── nginx/            # Reverse proxy config with TLS
│   ├── scripts/          # Backup scripts
│   ├── docker-compose.prod.yml     # Production overlay
│   └── docker-compose.staging.yml  # Staging overlay
├── tests/load/           # k6 load test scripts
├── docs/                 # Deployment runbook
├── .github/              # CI/CD (lint, test, security scanning, Trivy)
├── Makefile              # Dev/prod/staging commands
└── .env.example          # Environment template
```

## Key Features

- **Multi-tenant SaaS** with PostgreSQL Row-Level Security for data isolation
- **AI content generation** with three-layer prompt system (system + brand voice + listing data)
- **Brand voice profiles** for consistent tone across all generated content
- **MLS integration** via RESO Web API with incremental sync (30-min intervals)
- **Content versioning** with full history tracking
- **Export** to TXT, HTML, DOCX, PDF
- **Billing** with Stripe-backed subscription plans and usage metering
- **CSRF protection** via double-submit cookie pattern
- **Rate limiting** with sliding window (Redis sorted sets), per-path limits
- **Circuit breaker** on AI service with automatic recovery
- **Structured logging** with request ID correlation from frontend through Celery workers

## Development Commands

```bash
make help              # Show all available commands
make up / make down    # Start/stop dev infrastructure
make backend           # FastAPI dev server (port 8000)
make frontend          # Next.js dev server (port 3000)
make worker            # Celery worker
make beat              # Celery Beat scheduler
make test              # Run pytest
make test-cov          # Run pytest with coverage
make lint              # Ruff + ESLint
make fmt               # Auto-format
make migrate           # Apply Alembic migrations
make db-shell          # Open psql session
```

## Production Deployment

```bash
make prod-build        # Build production images
make prod-up           # Start production stack (nginx, TLS, monitoring, backups)
make prod-migrate      # Run migrations in production
make prod-logs         # Tail production logs
```

See [docs/deployment-runbook.md](docs/deployment-runbook.md) for the full deployment guide including rollback, backup/restore, TLS, monitoring, and incident response.

## Staging

```bash
make staging-build     # Build staging images
make staging-up        # Start staging stack (reduced resources, no TLS/monitoring)
make staging-down      # Stop staging
```

## Load Testing

```bash
make load-test                 # Smoke test (5 VUs, 1 min)
make load-test PROFILE=load    # Load test (50 VUs ramp)
make load-test PROFILE=stress  # Stress test (100 VUs ramp)
```

## CI/CD Pipeline

GitHub Actions pipeline runs on push to `main`/`master` and PRs:

| Job | Description |
|-----|-------------|
| `backend-lint` | Ruff linting |
| `backend-test` | pytest with PostgreSQL + Redis services, 60% coverage gate |
| `backend-security` | pip-audit (dependency vulnerabilities) + bandit (SAST) |
| `frontend-build` | ESLint + TypeScript check + Next.js build + npm audit |
| `docker-security` | Trivy container image scanning (CRITICAL/HIGH) |

## Testing

```bash
make test              # Run all 221 tests
make test-cov          # Tests with HTML coverage report
cd backend && pytest tests/test_auth.py -v         # Single file
cd backend && pytest -k "billing" -v               # By keyword
```

- **221 tests** across 27 test files, all passing
- **81% code coverage** (1918/2367 statements) -- CI gate: 60%
- All external services fully mocked -- zero real API calls to Anthropic, Stripe, S3, or MLS during testing
- No client credentials or secrets used in test execution

## API Documentation

Once the backend is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Monitoring (Production)

- **Grafana**: http://server:3001 (pre-provisioned dashboard with request rate, latency percentiles, error rates)
- **Prometheus**: http://server:9090 (internal metrics)
- Alert rules for high error rates, latency, downtime, auth failures (see `docker/monitoring/alerts.yml`)

## License

Proprietary - Galt Ocean Realty
