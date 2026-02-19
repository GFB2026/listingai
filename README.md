# ListingAI - AI-Powered Real Estate Content Engine

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

## Architecture

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: Next.js 15 + React 19 + TailwindCSS 4
- **AI**: Claude API (Anthropic)
- **Database**: PostgreSQL 16 with Row-Level Security
- **Cache/Broker**: Redis 7
- **Task Queue**: Celery
- **Storage**: S3 (MinIO in dev)
- **Billing**: Stripe

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
listingai/
├── backend/          # FastAPI application
├── frontend/         # Next.js application
├── docker/           # Docker configuration
├── Makefile          # Dev commands
└── .env.example      # Environment template
```

## License

Proprietary - Galt Ocean Realty
