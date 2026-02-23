# ListingAI Deployment Runbook

> **Current version:** 1.1.0 | See [CHANGELOG.md](../CHANGELOG.md) for release notes

## Prerequisites

- Docker & Docker Compose v2 installed on the host
- `.env` file configured (copy from `.env.example`)
- TLS certificates in place (or use the certbot auto-provisioning flow)
- DNS A record pointing to the server

---

## 1. First-Time Deploy

```bash
# Clone and configure
git clone <repo-url> /opt/listingai && cd /opt/listingai
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, ENCRYPTION_KEY,
#   POSTGRES_PASSWORD, SECRET_KEY, GRAFANA_ADMIN_PASSWORD, etc.

# Build images
make prod-build

# Start the stack
make prod-up

# Run database migrations
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec backend alembic upgrade head

# Verify
curl -s https://your-domain.com/health/ready | jq .
```

---

## 2. Routine Deployment (code update)

```bash
cd /opt/listingai
git pull origin main

# Rebuild only changed images
make prod-build

# Apply any new migrations BEFORE restarting the backend
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec backend alembic upgrade head

# Rolling restart (backend + worker + frontend)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  up -d --no-deps backend worker beat frontend

# Verify health
curl -s https://your-domain.com/health/ready | jq .
```

---

## 3. Rollback

### Code rollback
```bash
# Identify the previous commit
git log --oneline -5

# Roll back to the previous commit
git checkout <previous-commit-sha>

# Rebuild and restart
make prod-build
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  up -d --no-deps backend worker beat frontend
```

### Database rollback
```bash
# Roll back one Alembic migration
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec backend alembic downgrade -1

# Verify current migration head
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec backend alembic current
```

---

## 4. Database Backup & Restore

### Automatic backups
The `backup` container runs `pg_dump` daily with 7-day rotation (daily) and 4-week rotation (weekly). Backups are stored in the `backups` Docker volume.

### Manual backup
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec postgres pg_dump -U listingai --no-owner --no-acl --clean --if-exists \
  | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore from backup
```bash
# Stop backend and worker to prevent writes
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  stop backend worker beat

# Restore
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec -T postgres psql -U listingai -d listingai

# Re-run migrations in case the backup is from an older schema
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec backend alembic upgrade head

# Restart services
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  up -d backend worker beat
```

---

## 5. TLS Certificate Management

Certbot runs automatically in the `certbot` container, renewing every 12 hours.

### Initial certificate provisioning
```bash
# Ensure DNS points to the server, then:
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec certbot certbot certonly --webroot -w /var/www/certbot \
  -d your-domain.com --agree-tos --email admin@your-domain.com

# Reload nginx to pick up the new cert
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec nginx nginx -s reload
```

### Manual renewal
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec certbot certbot renew --webroot -w /var/www/certbot
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec nginx nginx -s reload
```

---

## 6. Monitoring

### Access Grafana
- URL: `http://<server-ip>:3001` (or via nginx if exposed)
- Default credentials: `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` from `.env`
- Pre-provisioned dashboard: "ListingAI Backend"

### Access Prometheus
- URL: `http://<server-ip>:9090` (internal only, not exposed via nginx by default)

### Key alerts (configured in `docker/monitoring/alerts.yml`)
| Alert | Condition | Severity |
|-------|-----------|----------|
| HighErrorRate | >5% 5xx for 2 min | critical |
| BackendDown | Scrape target unreachable 1 min | critical |
| HighP99Latency | P99 > 5s for 5 min | warning |
| HighAuthFailureRate | >30% auth 401s for 5 min | warning |
| NoTraffic | Zero requests for 10 min | warning |

---

## 7. Incident Response

### Backend not responding
```bash
# Check container status
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps

# Check logs
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  logs --tail=100 backend

# Restart backend
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  restart backend
```

### Worker not processing tasks
```bash
# Check worker logs
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  logs --tail=100 worker

# Check Celery queue depth
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec redis redis-cli LLEN celery

# Restart worker
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  restart worker
```

### Database connection exhaustion
```bash
# Check active connections
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec postgres psql -U listingai -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections if needed
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec postgres psql -U listingai -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE state = 'idle' AND query_start < now() - interval '10 minutes';
  "
```

### Redis memory pressure
```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  exec redis redis-cli INFO memory | grep used_memory_human
```

---

## 8. Scaling

### Horizontal scaling (workers)
```bash
# Run additional worker containers
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml \
  up -d --scale worker=3
```

### Vertical scaling
Edit resource limits in `docker/docker-compose.prod.yml` under `deploy.resources.limits`.

---

## 9. Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Async PostgreSQL URL (asyncpg) |
| `DATABASE_URL_SYNC` | Yes | Sync PostgreSQL URL (psycopg2) |
| `REDIS_URL` | Yes | Redis URL (db 0) |
| `CELERY_BROKER_URL` | Yes | Redis URL (db 1) |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `APP_SECRET_KEY` | Yes | Application secret key |
| `JWT_SECRET_KEY` | Yes | JWT signing key |
| `ENCRYPTION_KEY` | Yes | Fernet key for MLS credential encryption |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret API key |
| `STRIPE_PUBLISHABLE_KEY` | Yes | Stripe publishable API key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `S3_ACCESS_KEY` | Yes | S3/MinIO access key |
| `S3_SECRET_KEY` | Yes | S3/MinIO secret key |
| `SENTRY_DSN` | No | Sentry error tracking DSN |
| `GRAFANA_ADMIN_USER` | No | Grafana admin username (default: admin) |
| `GRAFANA_ADMIN_PASSWORD` | No | Grafana admin password (default: changeme) |
| `NEXT_PUBLIC_API_URL` | No | Frontend API URL (default: http://localhost:8000) |

### Migration chain

```
cbe7f3435501 (initial schema)
  → a1b2c3d4e5f6 (constraints + RLS)
  → b2c3d4e5f6a7 (performance indexes)
  → c3d4e5f6a7b8 (updated_at columns)
```
