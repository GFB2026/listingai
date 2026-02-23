.PHONY: help up down build migrate test lint fmt backend frontend frontend-test frontend-test-cov worker shell db-shell prod-up prod-down prod-build prod-logs staging-up staging-down staging-build load-test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Docker (dev)
up: ## Start all services (dev)
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --env-file .env up -d

down: ## Stop all services
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down

build: ## Build all Docker images
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml --env-file .env build

logs: ## Tail logs from all services
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml logs -f

# Docker (production)
prod-up: ## Start production stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env up -d

prod-down: ## Stop production stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down

prod-build: ## Build production images
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env build

prod-logs: ## Tail production logs
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f

prod-migrate: ## Run migrations in production
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml exec backend alembic upgrade head

# Docker (staging)
staging-up: ## Start staging stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml --env-file .env.staging up -d

staging-down: ## Stop staging stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml down

staging-build: ## Build staging images
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.staging.yml --env-file .env.staging build

# Load testing
load-test: ## Run k6 smoke test (use PROFILE=load|stress for heavier tests)
	k6 run -e PROFILE=$(or $(PROFILE),smoke) tests/load/k6-smoke.js

# Database
migrate: ## Run Alembic migrations
	cd backend && alembic upgrade head

migrate-new: ## Create new migration (usage: make migrate-new MSG="add users table")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback last migration
	cd backend && alembic downgrade -1

db-shell: ## Open psql shell
	docker compose -f docker/docker-compose.yml exec postgres psql -U listingai -d listingai

# Backend
backend: ## Run backend dev server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
frontend: ## Run frontend dev server
	cd frontend && npm run dev

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

# Worker
worker: ## Run Celery worker
	cd backend && celery -A app.workers.celery_app worker --loglevel=info

beat: ## Run Celery Beat scheduler
	cd backend && celery -A app.workers.celery_app beat --loglevel=info

# Testing
test: ## Run all tests (backend + frontend)
	cd backend && pytest -v
	cd frontend && npm test

test-cov: ## Run tests with coverage
	cd backend && pytest --cov=app --cov-report=html -v

frontend-test: ## Run frontend tests
	cd frontend && npm test

frontend-test-cov: ## Run frontend tests with coverage
	cd frontend && npm run test:coverage

# Code Quality
lint: ## Run linting
	cd backend && ruff check app/
	cd frontend && npm run lint

fmt: ## Format code
	cd backend && ruff format app/
	cd frontend && npm run format

# Utilities
shell: ## Open backend Python shell
	cd backend && python -c "import asyncio; from app.main import app; print('App loaded')"

redis-cli: ## Open Redis CLI
	docker compose -f docker/docker-compose.yml exec redis redis-cli
