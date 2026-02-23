# Changelog

All notable changes to this project are documented in this file.

## [1.2.0] - 2026-02-23

Deep coverage release — 85% backend test coverage.

### Added
- 53 new backend tests across 3 new + 5 extended test files (total: 274 tests, 30 files)
- `test_listing_service.py` — ListingService.upsert_from_mls create, update, skip-none paths
- `test_adapters.py` — PropertyAdapter/MediaAdapter: ViewDescription list/string, Appliances, GarageSpaces, list_date parsing, status/type mapping
- `test_redis.py` — RedisPool initialize, client error, close
- Extended `test_ai_service.py` — brand profile lookup, APIConnectionError, APIStatusError 5xx/4xx, hashtag extraction, circuit breaker half-open
- Extended `test_worker_tasks.py` — Celery wrapper correlation_id, SoftTimeLimitExceeded, retry for all 3 task files; listing-not-found skip; download error resilience
- Extended `test_media_api.py` — MediaService.upload(), no-filename fallback, content-length rejection, chunk size limit
- Extended `test_export_service.py` — PDF export, PDF XSS safety
- Extended `test_billing_service.py` — Stripe InvalidRequestError, general StripeError on subscription create

### Changed
- Backend test coverage increased from 81% to 85% (449 -> 348 missed statements)
- 8 source files now at 100% coverage: ai_service, billing_service, export_service, listing_service, media_service, content_batch, media_process, mls_sync
- Version bumped to 1.2.0
- Updated all documentation (README, CLAUDE.md, CHANGELOG, deployment runbook)

## [1.1.0] - 2026-02-23

Test coverage milestone release.

### Added
- 74 new backend tests across 9 new test files (total: 221 tests, 27 files)
- Test coverage for MLS connections API, sync engine, worker tasks, content endpoints, RESO client, media upload/presigned URLs, tenants API, Fernet encryption, and billing service
- Testing section in README.md with coverage stats and commands

### Fixed
- UUID-to-string serialization in `MLSConnectionResponse` and `TenantResponse` Pydantic schemas (added `field_serializer` for `id` field)

### Changed
- Backend test coverage increased from 67% to 81% (785 -> 449 missed statements)
- Version bumped to 1.1.0 (backend `pyproject.toml`, frontend `package.json`)
- Updated CLAUDE.md with current test statistics and version info
- Updated README.md with version badge, test stats, and testing documentation
- Updated CHANGELOG.md with full release history

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
- Frontend client-side password complexity validation matching backend rules
- Production config validation (fails fast if required secrets are missing)
- pip-audit dependency vulnerability scanning in CI
- bandit SAST scanning in CI
- npm audit in frontend CI
- Trivy container image scanning (CRITICAL/HIGH severity)
- Next.js security headers (HSTS, X-Frame-Options, Permissions-Policy)
- Tightened image remote patterns from wildcard to specific S3/MinIO hosts

### Reliability
- Celery exponential backoff with jitter on all task retries (replacing fixed delays)
- Soft and hard time limits on all Celery tasks
- Worker config: `task_acks_late`, `worker_prefetch_multiplier=1`, `task_reject_on_worker_lost`
- Circuit breaker on AI service with configurable failure threshold and recovery timeout
- Page offset cap (`le=1000`) to prevent DoS via large pagination offsets
- Batch listing_ids deduplication at schema level
- Export format validation with allowlist
- Docker init process (tini) for proper signal forwarding and zombie reaping
- Production resource limits (memory/CPU) on all Docker services
- Health checks on all production services (backend, frontend, postgres, redis, nginx)

### Observability
- Structured logging via structlog with request ID context variables
- Request ID middleware (8-char ID per request, returned in `X-Request-ID` header)
- Correlation ID propagation from API endpoints into Celery worker logs
- Frontend Axios interceptor attaching `X-Request-ID: crypto.randomUUID()` to all API calls
- Prometheus metrics endpoint with circuit breaker state gauge
- Prometheus alert rules (9 rules: HighErrorRate, BackendDown, HighP99Latency, etc.)
- Grafana pre-provisioned dashboard (8 panels: request rate, latency percentiles, error rate, heatmap, top endpoints, status distribution)
- Sentry integration (backend + frontend) with configurable DSN and sample rate

### Infrastructure
- Nginx reverse proxy with TLS 1.2/1.3, rate limiting zones, upstream health checks
- Certbot automated Let's Encrypt certificate renewal (every 12h)
- Daily PostgreSQL backup with 7-day daily + 4-week weekly rotation
- Docker Compose overlays: dev, production, staging
- Production compose with logging driver config (50MB max, 5 file rotation)
- Staging compose with reduced resource limits (no TLS/monitoring)

### Database
- Alembic migration chain: initial schema, constraints + RLS, performance indexes, updated_at columns
- Performance indexes: users email lookup, listings by MLS connection, content by tenant+created_at, listings by tenant+city, brand profiles by tenant+default
- `updated_at` timestamps on BrandProfile and MLSConnection models
- CHECK constraints on content status enum, usage event types
- NOT NULL constraints hardened across schema

### API
- DELETE endpoints for content, brand profiles, and users (with self-delete prevention)
- Typed Pydantic response models for batch queue and sync queue operations
- Stripe error handling with user-friendly messages
- Content export to TXT, HTML, DOCX, PDF with format validation

### Frontend
- Zero TypeScript `any` types across entire codebase
- Typed React Query hooks with proper interfaces (Listing, ContentItem, BrandProfile)
- AbortSignal propagation on all queries (request cancellation on unmount)
- Mutation error handlers with toast notifications (generate, MLS connections, export)
- Client-side password validation with real-time feedback on register
- Error boundaries on all dashboard route segments
- Topbar logout error handling with fallback redirect
- Per-endpoint timeout presets (30s default, 120s generate, 60s upload)

### CI/CD
- GitHub Actions pipeline: lint, test, security scan, frontend build, Docker image scan
- pip cache + npm cache for faster CI runs
- 60% coverage gate on backend tests
- Dependabot for pip, npm, and GitHub Actions updates
- Pre-commit hooks (trailing whitespace, ruff, ESLint)

### Developer Experience
- Makefile targets for dev, prod, staging, load testing
- k6 load test scripts with smoke/load/stress profiles
- Deployment runbook covering first deploy, updates, rollback, backup/restore, TLS, monitoring, incident response
- Separated dev requirements (`requirements-dev.txt`) from production
- Node version pinned via `.nvmrc` and `package.json` engines
- CLAUDE.md with full architecture documentation

## [0.1.0] - 2026-02-20

Initial scaffold.

### Added
- FastAPI backend with async SQLAlchemy, JWT auth, multi-tenant data model
- Next.js 15 frontend with App Router, React Query, TailwindCSS
- Claude AI content generation with three-layer prompt system
- MLS integration via RESO Web API (Trestle)
- Celery worker for async MLS sync and batch content generation
- Docker Compose development environment
- Brand voice profiles for customizing AI output
- Stripe billing integration
- MinIO (S3-compatible) media storage
